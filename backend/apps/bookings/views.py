from datetime import datetime
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.db.models import Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.drivers.models import DriverProfile, Vehicle
from apps.drivers.services import recompute_driver_status, recompute_vehicle_status
from apps.journeys.models import Journey
from apps.trust.models import Notification
from apps.trust.services import notify_booking_participants
from .models import Booking
from .permissions import IsVerifiedDriver, IsVerifiedPassenger
from .serializers import BookingRequestSerializer, BookingSerializer
from .services import refresh_contribution_estimates


def journey_has_departed(journey):
    departure = timezone.make_aware(
        datetime.combine(journey.travel_date, journey.departure_time),
        timezone.get_current_timezone(),
    )
    return timezone.now() >= departure


def _read_booking(booking, request):
    return BookingSerializer(booking, context={"request": request}).data


class PassengerBookingCreateView(APIView):
    permission_classes = [IsAuthenticated, IsVerifiedPassenger]
    throttle_scope = "booking_request"

    def post(self, request):
        serializer = BookingRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        journey_id = serializer.validated_data["journey"]
        seats_requested = serializer.validated_data["seats_requested"]
        request_message = serializer.validated_data["request_message"]

        try:
            with transaction.atomic():
                journey = get_object_or_404(
                    Journey.objects.select_for_update().select_related(
                        "driver", "vehicle", "driver__driver_profile"
                    ),
                    pk=journey_id,
                    status=Journey.Status.PUBLISHED,
                )
                if journey.driver_id == request.user.id:
                    return Response(
                        {"detail": "You cannot request seats on your own journey."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                if journey_has_departed(journey):
                    return Response(
                        {"detail": "Booking requests are closed because this journey has departed."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                profile = getattr(journey.driver, "driver_profile", None)
                if (
                    not journey.driver.is_active
                    or not journey.driver.is_email_verified
                    or not profile
                    or profile.verification_status != DriverProfile.VerificationStatus.APPROVED
                    or journey.vehicle.verification_status != Vehicle.VerificationStatus.APPROVED
                ):
                    return Response(
                        {"detail": "This journey is no longer eligible for booking."},
                        status=status.HTTP_409_CONFLICT,
                    )

                active = Booking.objects.filter(
                    journey=journey,
                    passenger=request.user,
                    status__in=(Booking.Status.PENDING, Booking.Status.CONFIRMED),
                ).exists()
                if active:
                    return Response(
                        {"detail": "You already have an active request or confirmed booking for this journey."},
                        status=status.HTTP_409_CONFLICT,
                    )

                confirmed = Booking.objects.filter(
                    journey=journey,
                    status=Booking.Status.CONFIRMED,
                ).aggregate(total=Sum("seats_requested"))["total"] or 0
                available = max(0, journey.seats_offered - confirmed)
                if seats_requested > available:
                    return Response(
                        {"detail": f"Only {available} seat(s) are currently available."},
                        status=status.HTTP_409_CONFLICT,
                    )

                booking = Booking.objects.create(
                    journey=journey,
                    passenger=request.user,
                    seats_requested=seats_requested,
                    request_message=request_message,
                )
                from apps.trust.services import notify
                notify(
                    recipient=journey.driver,
                    actor=request.user,
                    event_type=Notification.EventType.BOOKING_REQUEST,
                    title="New passenger booking request",
                    body=f"{request.user.display_name} requested {seats_requested} seat(s) on your journey.",
                    booking=booking,
                    journey=journey,
                )
        except IntegrityError:
            return Response(
                {"detail": "You already have an active booking for this journey."},
                status=status.HTTP_409_CONFLICT,
            )

        return Response(
            {
                "detail": "Your booking request has been sent to the driver. Seats are not reserved until the driver confirms.",
                "booking": _read_booking(booking, request),
            },
            status=status.HTTP_201_CREATED,
        )


class PassengerBookingListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated, IsVerifiedPassenger]
    serializer_class = BookingSerializer

    def get_queryset(self):
        return (
            Booking.objects.filter(passenger=self.request.user)
            .select_related("journey", "journey__driver", "journey__vehicle", "passenger")
            .order_by("-requested_at")
        )


class DriverBookingRequestListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated, IsVerifiedDriver]
    serializer_class = BookingSerializer

    def get_queryset(self):
        queryset = (
            Booking.objects.filter(journey__driver=self.request.user)
            .select_related("journey", "journey__driver", "journey__vehicle", "passenger")
            .order_by("-requested_at")
        )
        status_filter = self.request.query_params.get("status")
        allowed = {choice[0] for choice in Booking.Status.choices}
        if status_filter in allowed:
            queryset = queryset.filter(status=status_filter)
        return queryset


class BookingApproveView(APIView):
    permission_classes = [IsAuthenticated, IsVerifiedDriver]
    throttle_scope = "booking_action"

    def post(self, request, pk):
        response_note = str(request.data.get("driver_response", "")).strip()[:500]
        try:
            with transaction.atomic():
                initial = get_object_or_404(Booking.objects.only("id", "journey_id"), pk=pk)
                journey = get_object_or_404(
                    Journey.objects.select_for_update().select_related("driver", "vehicle"),
                    pk=initial.journey_id,
                    driver=request.user,
                    status=Journey.Status.PUBLISHED,
                )
                booking = get_object_or_404(
                    Booking.objects.select_for_update().select_related("passenger"),
                    pk=pk,
                    journey=journey,
                )
                if booking.status != Booking.Status.PENDING:
                    return Response(
                        {"detail": "Only pending booking requests can be approved."},
                        status=status.HTTP_409_CONFLICT,
                    )
                if (
                    not booking.passenger.is_active
                    or not booking.passenger.is_email_verified
                    or getattr(getattr(booking.passenger, "passenger_verification", None), "status", None) != "approved"
                ):
                    return Response(
                        {"detail": "The passenger account is no longer eligible for booking approval."},
                        status=status.HTTP_409_CONFLICT,
                    )
                if journey_has_departed(journey):
                    return Response(
                        {"detail": "This journey has departed; the booking request cannot be approved."},
                        status=status.HTTP_409_CONFLICT,
                    )

                profile = DriverProfile.objects.filter(user=request.user).first()
                if not profile:
                    return Response({"detail": "Driver verification is no longer valid."}, status=403)
                recompute_vehicle_status(journey.vehicle)
                recompute_driver_status(request.user)
                profile.refresh_from_db()
                journey.vehicle.refresh_from_db()
                if (
                    profile.verification_status != DriverProfile.VerificationStatus.APPROVED
                    or journey.vehicle.verification_status != Vehicle.VerificationStatus.APPROVED
                ):
                    return Response(
                        {"detail": "Driver and vehicle verification must remain approved to confirm bookings."},
                        status=status.HTTP_403_FORBIDDEN,
                    )

                confirmed = Booking.objects.filter(
                    journey=journey,
                    status=Booking.Status.CONFIRMED,
                ).aggregate(total=Sum("seats_requested"))["total"] or 0
                available = max(0, journey.seats_offered - confirmed)
                if booking.seats_requested > available:
                    return Response(
                        {"detail": f"Not enough seats remain. Only {available} seat(s) are available."},
                        status=status.HTTP_409_CONFLICT,
                    )

                booking.status = Booking.Status.CONFIRMED
                booking.driver_response = response_note
                booking.responded_at = timezone.now()
                booking.save(update_fields=["status", "driver_response", "responded_at", "updated_at"])
                refresh_contribution_estimates(journey)
                booking.refresh_from_db()
                notify_booking_participants(
                    booking=booking,
                    event_type=Notification.EventType.BOOKING_CONFIRMED,
                    title="Booking confirmed",
                    body="The driver approved your seat request. Your seats are now reserved.",
                    actor=request.user,
                )
        except IntegrityError:
            return Response(
                {"detail": "The booking could not be confirmed because seat availability changed. Refresh and try again."},
                status=status.HTTP_409_CONFLICT,
            )

        return Response({"detail": "Booking confirmed. The requested seats are now reserved.", "booking": _read_booking(booking, request)})


class BookingDeclineView(APIView):
    permission_classes = [IsAuthenticated, IsVerifiedDriver]
    throttle_scope = "booking_action"

    def post(self, request, pk):
        response_note = str(request.data.get("driver_response", "")).strip()[:500]
        with transaction.atomic():
            initial = get_object_or_404(Booking.objects.only("id", "journey_id"), pk=pk)
            journey = get_object_or_404(
                Journey.objects.select_for_update(),
                pk=initial.journey_id,
                driver=request.user,
            )
            booking = get_object_or_404(
                Booking.objects.select_for_update().select_related("journey", "journey__driver", "journey__vehicle", "passenger"),
                pk=pk,
                journey=journey,
                status=Booking.Status.PENDING,
            )
            booking.status = Booking.Status.DECLINED
            booking.driver_response = response_note
            booking.responded_at = timezone.now()
            booking.save(update_fields=["status", "driver_response", "responded_at", "updated_at"])
            notify_booking_participants(
                booking=booking,
                event_type=Notification.EventType.BOOKING_DECLINED,
                title="Booking request declined",
                body="The driver declined your booking request.",
                actor=request.user,
            )

        return Response({"detail": "Booking request declined.", "booking": _read_booking(booking, request)})


class BookingCancelView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_scope = "booking_action"

    def post(self, request, pk):
        with transaction.atomic():
            initial = get_object_or_404(Booking.objects.only("id", "journey_id"), pk=pk)
            journey = get_object_or_404(
                Journey.objects.select_for_update().select_related("driver"),
                pk=initial.journey_id,
            )
            booking = get_object_or_404(
                Booking.objects.select_for_update().select_related(
                    "journey", "journey__driver", "journey__vehicle", "passenger"
                ),
                pk=pk,
                journey=journey,
            )
            is_passenger = booking.passenger_id == request.user.id
            is_driver = journey.driver_id == request.user.id and request.user.role == "driver"
            if not (is_passenger or is_driver):
                return Response({"detail": "You do not have permission to cancel this booking."}, status=403)
            if booking.status not in (Booking.Status.PENDING, Booking.Status.CONFIRMED):
                return Response({"detail": "This booking is no longer active."}, status=409)
            if journey_has_departed(journey):
                return Response({"detail": "Bookings cannot be cancelled after the journey has departed."}, status=409)

            was_confirmed = booking.status == Booking.Status.CONFIRMED
            booking.status = Booking.Status.CANCELLED
            booking.cancelled_at = timezone.now()
            booking.cancelled_by = request.user
            booking.save(update_fields=["status", "cancelled_at", "cancelled_by", "updated_at"])
            notify_booking_participants(
                booking=booking,
                event_type=Notification.EventType.BOOKING_CANCELLED,
                title="Booking cancelled",
                body="A participant cancelled this booking. Any reserved seats have been released.",
                actor=request.user,
            )
            if was_confirmed:
                refresh_contribution_estimates(journey)

        return Response({"detail": "Booking cancelled. Confirmed seats have been released.", "booking": _read_booking(booking, request)})


class BookingDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        booking = get_object_or_404(
            Booking.objects.select_related(
                "journey", "journey__driver", "journey__vehicle", "passenger"
            ),
            pk=pk,
        )
        if booking.passenger_id != request.user.id and booking.journey.driver_id != request.user.id:
            return Response({"detail": "Booking not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(_read_booking(booking, request))
