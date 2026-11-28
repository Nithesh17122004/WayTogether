from decimal import Decimal, ROUND_HALF_UP

from django.db.models import Sum

from .models import Booking


def confirmed_seat_count(journey):
    result = Booking.objects.filter(
        journey=journey,
        status=Booking.Status.CONFIRMED,
    ).aggregate(total=Sum("seats_requested"))
    return result["total"] or 0


def available_seat_count(journey):
    return max(0, journey.seats_offered - confirmed_seat_count(journey))


def refresh_contribution_estimates(journey):
    """
    Keep each active booking aligned with the driver's published per-seat amount.
    The passenger price is fixed per seat: driver amount + disclosed 30% fee.
    This only records an estimate; it does not initiate a payment or payout.
    """
    active_bookings = Booking.objects.filter(
        journey=journey,
        status__in=(Booking.Status.PENDING, Booking.Status.CONFIRMED),
    ).order_by("requested_at", "id")
    per_person = journey.passenger_total_per_passenger.quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )

    for booking in active_bookings:
        booking.estimated_contribution_per_passenger = per_person
        booking.estimated_contribution_total = (
            per_person * booking.seats_requested
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        booking.save(update_fields=[
            "estimated_contribution_per_passenger",
            "estimated_contribution_total",
            "updated_at",
        ])
