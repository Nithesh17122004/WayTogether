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
    Recalculate provisional equal expense shares after an approval/cancellation.
    No money is charged in Phase 6. Phase 7 must define the final charge point.
    """
    confirmed = list(
        Booking.objects.filter(
            journey=journey,
            status=Booking.Status.CONFIRMED,
        ).order_by("requested_at", "id")
    )
    occupied_seats = sum(item.seats_requested for item in confirmed)
    if not confirmed:
        return

    total_people = occupied_seats + 1  # driver plus confirmed passengers
    per_person = (journey.estimated_total_expenses / total_people).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )

    for booking in confirmed:
        booking.estimated_contribution_per_passenger = per_person
        booking.estimated_contribution_total = (
            per_person * booking.seats_requested
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        booking.save(update_fields=[
            "estimated_contribution_per_passenger",
            "estimated_contribution_total",
            "updated_at",
        ])
