from datetime import date
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.drivers.models import DriverProfile, Vehicle
from apps.drivers.services import recompute_driver_status, recompute_vehicle_status
from .geo import haversine_km
from .models import Journey
from .permissions import IsVerifiedDriver
from .serializers import JourneySerializer
from .services import MapsProviderError, MapsRateLimitError, get_route_preview, search_locations


def _published_queryset():
    return (
        Journey.objects.filter(
            status=Journey.Status.PUBLISHED,
            travel_date__gte=timezone.localdate(),
            driver__is_active=True,
            driver__is_email_verified=True,
            driver__is_phone_verified=True,
            driver__driver_profile__verification_status=DriverProfile.VerificationStatus.APPROVED,
            vehicle__verification_status=Vehicle.VerificationStatus.APPROVED,
        )
        .select_related("driver", "vehicle", "driver__driver_profile")
        .prefetch_related("stops")
    )


class LocationSearchView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = "map_search"

    def get(self, request):
        query = str(request.query_params.get("q", "")).strip()
        if len(query) < 3:
            return Response({"results": []})
        try:
            results = search_locations(query)
        except MapsRateLimitError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_429_TOO_MANY_REQUESTS)
        except MapsProviderError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        return Response({"results": results})


class RoutePreviewView(APIView):
    permission_classes = [IsAuthenticated, IsVerifiedDriver]
    throttle_scope = "route_preview"

    def get(self, request):
        try:
            values = [
                float(request.query_params[name])
                for name in ("origin_lat", "origin_lon", "destination_lat", "destination_lon")
            ]
        except (KeyError, TypeError, ValueError):
            return Response(
                {"detail": "Provide origin_lat, origin_lon, destination_lat and destination_lon."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        origin_lat, origin_lon, destination_lat, destination_lon = values
        if not -90 <= origin_lat <= 90 or not -90 <= destination_lat <= 90:
            return Response({"detail": "Latitude must be between -90 and 90."}, status=400)
        if not -180 <= origin_lon <= 180 or not -180 <= destination_lon <= 180:
            return Response({"detail": "Longitude must be between -180 and 180."}, status=400)
        try:
            route = get_route_preview(origin_lat, origin_lon, destination_lat, destination_lon)
        except MapsProviderError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        return Response(route)


class JourneyListCreateView(APIView):
    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated(), IsVerifiedDriver()]
        return [AllowAny()]

    def get(self, request):
        if request.query_params.get("mine") == "true":
            if not request.user.is_authenticated:
                return Response({"detail": "Authentication is required."}, status=401)
            queryset = Journey.objects.filter(driver=request.user).select_related("vehicle").prefetch_related("stops")
            return Response(JourneySerializer(queryset, many=True, context={"request": request}).data)

        try:
            origin_lat = float(request.query_params["origin_lat"])
            origin_lon = float(request.query_params["origin_lon"])
            destination_lat = float(request.query_params["destination_lat"])
            destination_lon = float(request.query_params["destination_lon"])
            travel_date = date.fromisoformat(request.query_params["date"])
            seats = int(request.query_params.get("seats", "1"))
            radius = float(request.query_params.get("radius_km", "25"))
        except (KeyError, ValueError, TypeError):
            return Response(
                {"detail": "Provide origin/destination coordinates and an ISO date (YYYY-MM-DD)."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not -90 <= origin_lat <= 90 or not -90 <= destination_lat <= 90:
            return Response({"detail": "Latitude must be between -90 and 90."}, status=400)
        if not -180 <= origin_lon <= 180 or not -180 <= destination_lon <= 180:
            return Response({"detail": "Longitude must be between -180 and 180."}, status=400)
        if travel_date < timezone.localdate():
            return Response({"detail": "Search date cannot be in the past."}, status=400)
        if not 1 <= seats <= 8 or not 1 <= radius <= 100:
            return Response({"detail": "Seats must be 1–8 and search radius 1–100 km."}, status=400)

        queryset = _published_queryset().filter(travel_date=travel_date, seats_offered__gte=seats)
        matches = []
        for journey in queryset[:1000]:
            origin_distance = haversine_km(
                origin_lat, origin_lon, journey.origin_latitude, journey.origin_longitude
            )
            destination_distance = haversine_km(
                destination_lat, destination_lon,
                journey.destination_latitude, journey.destination_longitude,
            )
            if origin_distance <= radius and destination_distance <= radius:
                journey._origin_match_distance_km = round(origin_distance, 1)
                journey._destination_match_distance_km = round(destination_distance, 1)
                journey._route_match_score = origin_distance + destination_distance
                matches.append(journey)

        matches.sort(key=lambda item: (
            item._route_match_score,
            item.departure_time,
            item.id,
        ))
        return Response(JourneySerializer(matches, many=True, context={"request": request}).data)

    def post(self, request):
        serializer = JourneySerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        journey = serializer.save()
        return Response(JourneySerializer(journey, context={"request": request}).data, status=201)


class MyJourneyListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated, IsVerifiedDriver]
    serializer_class = JourneySerializer

    def get_queryset(self):
        return (
            Journey.objects.filter(driver=self.request.user)
            .select_related("vehicle")
            .prefetch_related("stops")
        )


class JourneyDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, pk):
        journey = get_object_or_404(
            Journey.objects.select_related("driver", "vehicle", "driver__driver_profile")
            .prefetch_related("stops"),
            pk=pk,
        )
        if journey.status != Journey.Status.PUBLISHED and (
            not request.user.is_authenticated or journey.driver_id != request.user.id
        ):
            return Response({"detail": "Journey not found."}, status=404)
        return Response(JourneySerializer(journey, context={"request": request}).data)


class JourneyUpdateView(generics.UpdateAPIView):
    permission_classes = [IsAuthenticated, IsVerifiedDriver]
    serializer_class = JourneySerializer
    http_method_names = ["patch", "put", "head", "options"]

    def get_queryset(self):
        return Journey.objects.filter(driver=self.request.user, status=Journey.Status.DRAFT).select_related("vehicle")

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context


class JourneyPublishView(APIView):
    permission_classes = [IsAuthenticated, IsVerifiedDriver]

    def post(self, request, pk):
        with transaction.atomic():
            journey = get_object_or_404(
                Journey.objects.select_for_update().select_related("vehicle", "driver"),
                pk=pk,
                driver=request.user,
                status=Journey.Status.DRAFT,
            )
            profile = DriverProfile.objects.select_for_update().filter(user=request.user).first()
            if not profile:
                return Response({"detail": "Complete driver verification before publishing."}, status=400)

            recompute_vehicle_status(journey.vehicle)
            recompute_driver_status(request.user)
            profile.refresh_from_db()
            journey.vehicle.refresh_from_db()

            if profile.verification_status != DriverProfile.VerificationStatus.APPROVED:
                return Response({"detail": "Your driver verification must be approved before publishing."}, status=403)
            if journey.vehicle.verification_status != Vehicle.VerificationStatus.APPROVED:
                return Response({"detail": "The selected vehicle must be approved before publishing."}, status=403)
            if not journey.independently_planned or not journey.expenses_only:
                return Response({"detail": "The journey must meet WayTogether's independent journey and expense-sharing rules."}, status=400)
            if journey.estimated_total_expenses <= Decimal("0.00"):
                return Response({"detail": "Enter the estimated eligible journey expenses before publishing."}, status=400)

            journey.status = Journey.Status.PUBLISHED
            journey.published_at = timezone.now()
            journey.save(update_fields=["status", "published_at", "updated_at"])

        return Response({
            "detail": "Your independently planned journey has been published.",
            "journey": JourneySerializer(journey, context={"request": request}).data,
        })


class JourneyCancelView(APIView):
    permission_classes = [IsAuthenticated, IsVerifiedDriver]

    def post(self, request, pk):
        journey = get_object_or_404(Journey, pk=pk, driver=request.user)
        if journey.status not in (Journey.Status.DRAFT, Journey.Status.PUBLISHED):
            return Response({"detail": "This journey can no longer be cancelled."}, status=409)
        journey.status = Journey.Status.CANCELLED
        journey.save(update_fields=["status", "updated_at"])
        return Response({"detail": "Journey cancelled.", "status": journey.status})
