from datetime import date
from decimal import Decimal

from django.db import transaction
from django.db.models import Prefetch, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.drivers.models import DriverProfile, Vehicle, VerificationDocument
from apps.bookings.models import Booking
from apps.trust.models import Notification
from apps.trust.services import notify
from apps.drivers.services import recompute_driver_status, recompute_vehicle_status
from .geo import haversine_km
from .models import Journey
from .permissions import IsDriverAccount, IsVerifiedDriver
from .serializers import JourneySerializer
from .services import MapsProviderError, MapsRateLimitError, get_route_preview, search_locations


def _best_matching_segment(journey, origin_lat, origin_lon, destination_lat, destination_lon, radius_km):
    """Find an ordered pickup/drop-off pair along the journey, including intermediate stops."""
    points = [
        (journey.origin_name, journey.origin_latitude, journey.origin_longitude),
        *[
            (stop.location_name, stop.latitude, stop.longitude)
            for stop in journey.stops.all()
        ],
        (journey.destination_name, journey.destination_latitude, journey.destination_longitude),
    ]
    best = None
    for origin_index, origin_point in enumerate(points[:-1]):
        origin_distance = haversine_km(
            origin_lat, origin_lon, origin_point[1], origin_point[2]
        )
        if origin_distance > radius_km:
            continue
        for destination_point in points[origin_index + 1:]:
            destination_distance = haversine_km(
                destination_lat, destination_lon,
                destination_point[1], destination_point[2],
            )
            if destination_distance > radius_km:
                continue
            score = origin_distance + destination_distance
            if best is None or score < best[0]:
                best = (
                    score,
                    origin_distance,
                    destination_distance,
                    origin_point[0],
                    destination_point[0],
                )
    return best


def _published_queryset():
    """
    One shared eligibility rule for public marketplace lists and journey details.
    Keep time-of-departure checks out of this base queryset so a user who opened
    a journey just before departure can still read its details afterwards.
    New booking requests remain protected by the booking service's departure check.
    """
    return (
        Journey.objects.filter(
            status=Journey.Status.PUBLISHED,
            travel_date__gte=timezone.localdate(),
            driver__is_active=True,
            driver__is_email_verified=True,
            driver__driver_profile__verification_status=DriverProfile.VerificationStatus.APPROVED,
            driver__driver_documents__document_type=VerificationDocument.DocumentType.DRIVER_PHOTO,
            driver__driver_documents__review_status=VerificationDocument.ReviewStatus.APPROVED,
            driver__driver_documents__is_current=True,
            vehicle__verification_status=Vehicle.VerificationStatus.APPROVED,
        )
        .select_related("driver", "vehicle", "driver__driver_profile")
        .prefetch_related(
            "stops",
            Prefetch("bookings", queryset=Booking.objects.filter(status=Booking.Status.CONFIRMED), to_attr="_confirmed_bookings"),
        )
        .distinct()
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
    # A route preview is public, read-only map data; publishing remains restricted
    # to authenticated verified drivers in JourneyPublishView.
    permission_classes = [AllowAny]
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
        except MapsRateLimitError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_429_TOO_MANY_REQUESTS)
        except MapsProviderError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        return Response(route)


class JourneyListCreateView(APIView):
    def get_permissions(self):
        if self.request.method == "POST":
            # Drivers can prepare drafts while KYC is pending; publishing is
            # separately protected by IsVerifiedDriver.
            return [IsAuthenticated(), IsDriverAccount()]
        return [AllowAny()]

    def get(self, request):
        if request.query_params.get("mine") == "true":
            if not request.user.is_authenticated:
                return Response({"detail": "Authentication is required."}, status=401)
            queryset = Journey.objects.filter(driver=request.user).select_related("vehicle").prefetch_related(
                "stops",
                Prefetch("bookings", queryset=Booking.objects.filter(status=Booking.Status.CONFIRMED), to_attr="_confirmed_bookings"),
            )
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

        queryset = _published_queryset().filter(travel_date=travel_date)
        if travel_date == timezone.localdate():
            queryset = queryset.filter(departure_time__gt=timezone.localtime().time().replace(tzinfo=None))
        matches = []
        for journey in queryset[:1000]:
            confirmed_seats = sum(item.seats_requested for item in journey._confirmed_bookings)
            journey._confirmed_seats = confirmed_seats
            if journey.seats_offered - confirmed_seats < seats:
                continue
            match = _best_matching_segment(
                journey, origin_lat, origin_lon, destination_lat, destination_lon, radius
            )
            if match:
                (
                    journey._route_match_score,
                    origin_distance,
                    destination_distance,
                    journey._matched_origin_name,
                    journey._matched_destination_name,
                ) = match
                journey._origin_match_distance_km = round(origin_distance, 1)
                journey._destination_match_distance_km = round(destination_distance, 1)
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
    # A pending driver must still be able to manage and see their saved drafts.
    permission_classes = [IsAuthenticated, IsDriverAccount]
    serializer_class = JourneySerializer

    def get_queryset(self):
        return (
            Journey.objects.filter(driver=self.request.user)
            .select_related("vehicle")
            .prefetch_related(
                "stops",
                Prefetch("bookings", queryset=Booking.objects.filter(status=Booking.Status.CONFIRMED), to_attr="_confirmed_bookings"),
            )
        )


class JourneyDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, pk):
        # Fetch the record first so its owner can still view their own draft,
        # cancelled or completed journey. Public access then uses exactly the
        # same approved-driver/vehicle/document eligibility filter as the
        # upcoming dashboard and marketplace search.
        journey = get_object_or_404(
            Journey.objects.select_related("driver", "vehicle", "driver__driver_profile")
            .prefetch_related(
                "stops",
                Prefetch("bookings", queryset=Booking.objects.filter(status=Booking.Status.CONFIRMED), to_attr="_confirmed_bookings"),
            ),
            pk=pk,
        )
        is_owner = request.user.is_authenticated and journey.driver_id == request.user.id
        if journey.status == Journey.Status.PUBLISHED:
            public_journey = _published_queryset().filter(pk=pk).first()
            if public_journey is None and not is_owner:
                return Response({"detail": "This journey is not currently available to the public."}, status=404)
            if public_journey is not None:
                journey = public_journey
        elif not is_owner:
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
            approved_driver_photo = VerificationDocument.objects.filter(
                owner=request.user,
                document_type=VerificationDocument.DocumentType.DRIVER_PHOTO,
                review_status=VerificationDocument.ReviewStatus.APPROVED,
                is_current=True,
            ).exists()
            if not approved_driver_photo:
                return Response({"detail": "Upload your driver face photo and wait for administrator approval before publishing."}, status=403)
            if not request.user.phone:
                return Response(
                    {"detail": "Add a driver contact phone number before publishing. Phone OTP verification is not required."},
                    status=400,
                )
            if journey.vehicle.verification_status != Vehicle.VerificationStatus.APPROVED:
                return Response({"detail": "The selected vehicle must be approved before publishing."}, status=403)
            if journey.travel_date < timezone.localdate() or (
                journey.travel_date == timezone.localdate()
                and journey.departure_time <= timezone.localtime().time().replace(tzinfo=None)
            ):
                return Response({"detail": "This departure time has already passed. Update the draft to a future departure time."}, status=400)
            if not journey.independently_planned or not journey.expenses_only:
                return Response({"detail": "The journey must meet WayTogether's independent journey and expense-sharing rules."}, status=400)
            if journey.driver_amount_per_passenger <= Decimal("0.00"):
                return Response({"detail": "Enter the driver amount per passenger before publishing."}, status=400)

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
        with transaction.atomic():
            journey = get_object_or_404(
                Journey.objects.select_for_update(),
                pk=pk,
                driver=request.user,
            )
            if journey.status not in (Journey.Status.DRAFT, Journey.Status.PUBLISHED):
                return Response({"detail": "This journey can no longer be cancelled."}, status=409)

            now = timezone.now()
            affected_bookings = list(
                Booking.objects.select_for_update()
                .filter(
                    journey=journey,
                    status__in=(Booking.Status.PENDING, Booking.Status.CONFIRMED),
                )
                .select_related("passenger")
            )
            Booking.objects.filter(
                pk__in=[item.pk for item in affected_bookings],
            ).update(
                status=Booking.Status.CANCELLED,
                cancelled_at=now,
                cancelled_by=request.user,
                updated_at=now,
            )
            for booking in affected_bookings:
                notify(
                    recipient=booking.passenger,
                    actor=request.user,
                    event_type=Notification.EventType.JOURNEY_CANCELLED,
                    title="Journey cancelled",
                    body="The driver cancelled this journey. Your booking is now closed.",
                    booking=booking,
                    journey=journey,
                )
            journey.status = Journey.Status.CANCELLED
            journey.save(update_fields=["status", "updated_at"])

        return Response({
            "detail": "Journey cancelled. All pending requests and confirmed bookings have been cancelled.",
            "status": journey.status,
        })


class UpcomingJourneyListView(generics.ListAPIView):
    """Real published future routes for the signed-in marketplace dashboard."""
    permission_classes = [IsAuthenticated]
    serializer_class = JourneySerializer

    def get_queryset(self):
        now = timezone.localtime().time().replace(tzinfo=None)
        return _published_queryset().filter(
            Q(travel_date__gt=timezone.localdate())
            | Q(travel_date=timezone.localdate(), departure_time__gte=now)
        ).order_by("travel_date", "departure_time")[:30]
