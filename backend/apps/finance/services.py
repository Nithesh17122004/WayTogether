from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import APIException, PermissionDenied, ValidationError

from apps.bookings.models import Booking
from apps.journeys.models import Journey
from apps.trust.models import Notification
from apps.trust.services import notify

from .models import ExpenseSettlement, PassengerContribution, SandboxPayment, SandboxRefund


class SandboxDisabled(APIException):
    status_code = 403
    default_detail = "Sandbox payment simulation is disabled."
    default_code = "sandbox_disabled"


def sandbox_enabled():
    return bool(getattr(settings, "FINANCE_SANDBOX_ENABLED", False))


def ensure_sandbox_enabled():
    if not sandbox_enabled():
        raise SandboxDisabled()


def _departure_datetime(journey):
    from datetime import datetime
    return timezone.make_aware(
        datetime.combine(journey.travel_date, journey.departure_time),
        timezone.get_current_timezone(),
    )


@transaction.atomic
def finalize_expense_settlement(*, journey_id, driver, data):
    journey = (
        Journey.objects.select_for_update()
        .select_related("driver")
        .get(pk=journey_id, driver=driver)
    )
    if journey.status != Journey.Status.PUBLISHED:
        raise ValidationError({"journey": "Only a published journey can be financially finalized."})
    if timezone.now() < _departure_datetime(journey):
        raise ValidationError({"journey": "Actual expenses can be finalized only after the departure time."})
    if hasattr(journey, "expense_settlement"):
        raise ValidationError({"journey": "Final expenses have already been submitted and locked."})

    # Requests that were still pending at departure can no longer be approved.
    now = timezone.now()
    Booking.objects.filter(
        journey=journey,
        status=Booking.Status.PENDING,
    ).update(
        status=Booking.Status.CANCELLED,
        cancelled_at=now,
        cancelled_by=driver,
        updated_at=now,
    )

    bookings = list(
        Booking.objects.select_for_update()
        .filter(journey=journey, status=Booking.Status.CONFIRMED)
        .select_related("passenger")
        .order_by("requested_at", "id")
    )
    passenger_seats = sum(booking.seats_requested for booking in bookings)
    actual_fields = (
        "actual_fuel_expense", "actual_toll_expense",
        "actual_parking_expense", "actual_other_expense",
    )
    total = sum((data.get(field, Decimal("0.00")) for field in actual_fields), Decimal("0.00"))
    total = total.quantize(Decimal("0.01"))
    if total <= Decimal("0.00"):
        raise ValidationError({"actual_expenses": "Enter a positive total of eligible actual journey expenses."})

    # Use integer paise so the allocation reconciles exactly.
    total_paise = int((total * 100).to_integral_exact())
    people = passenger_seats + 1  # driver is a cost-sharing participant
    per_person_paise, remainder_paise = divmod(total_paise, people)
    driver_share = (Decimal(per_person_paise + remainder_paise) / 100).quantize(Decimal("0.01"))
    # Passenger checkout is based on the fixed amount accepted when the journey
    # was published, plus the disclosed platform fee. The actual expense split
    # remains in ExpenseSettlement as a separate post-trip cost record.
    per_seat = journey.passenger_total_per_passenger.quantize(Decimal("0.01"))
    if per_seat <= Decimal("0.00"):
        raise ValidationError({"journey": "This journey has no valid published passenger amount."})

    settlement = ExpenseSettlement.objects.create(
        journey=journey,
        driver=driver,
        actual_fuel_expense=data.get("actual_fuel_expense", Decimal("0.00")),
        actual_toll_expense=data.get("actual_toll_expense", Decimal("0.00")),
        actual_parking_expense=data.get("actual_parking_expense", Decimal("0.00")),
        actual_other_expense=data.get("actual_other_expense", Decimal("0.00")),
        actual_expense_note=data.get("actual_expense_note", ""),
        eligible_total=total,
        driver_share=driver_share,
        passenger_seat_count=passenger_seats,
        is_finalized=True,
        finalized_at=timezone.now(),
    )
    for booking in bookings:
        amount = (per_seat * booking.seats_requested).quantize(Decimal("0.01"))
        PassengerContribution.objects.create(
            booking=booking,
            settlement=settlement,
            passenger=booking.passenger,
            seat_count=booking.seats_requested,
            per_seat_amount=per_seat,
            total_amount=Decimal(amount).quantize(Decimal("0.01")),
        )
        notify(
            recipient=booking.passenger,
            actor=driver,
            event_type=Notification.EventType.EXPENSE_FINALIZED,
            title="Final expense contribution available",
            body="The driver finalized this journey's eligible expenses. Your contribution is ready to review.",
            booking=booking,
            journey=journey,
        )

    journey.status = Journey.Status.COMPLETED
    journey.save(update_fields=["status", "updated_at"])
    return settlement


@transaction.atomic
def create_sandbox_payment(*, contribution, passenger):
    ensure_sandbox_enabled()
    contribution = (
        PassengerContribution.objects.select_for_update()
        .select_related("passenger", "settlement", "booking")
        .get(pk=contribution.pk)
    )
    if contribution.passenger_id != passenger.id:
        raise PermissionDenied("You can only simulate payment for your own contribution.")
    existing = contribution.sandbox_payments.filter(
        status__in=(SandboxPayment.Status.CREATED, SandboxPayment.Status.SUCCEEDED)
    ).first()
    if existing:
        return existing
    return SandboxPayment.objects.create(
        contribution=contribution,
        amount=contribution.total_amount,
        currency=contribution.currency,
    )


@transaction.atomic
def complete_sandbox_payment(*, payment_id, passenger, outcome, failure_note=""):
    ensure_sandbox_enabled()
    payment = (
        SandboxPayment.objects.select_for_update()
        .select_related("contribution", "contribution__passenger")
        .get(pk=payment_id, contribution__passenger=passenger)
    )
    if payment.status != SandboxPayment.Status.CREATED:
        raise ValidationError({"payment": "Only a newly initiated sandbox payment can be completed."})
    if outcome not in (SandboxPayment.Status.SUCCEEDED, SandboxPayment.Status.FAILED):
        raise ValidationError({"outcome": "Choose succeeded or failed for the sandbox simulation."})
    payment.status = outcome
    payment.failure_note = failure_note[:300] if outcome == SandboxPayment.Status.FAILED else ""
    payment.completed_at = timezone.now()
    payment.save(update_fields=["status", "failure_note", "completed_at"])
    return payment


@transaction.atomic
def refund_sandbox_payment(*, payment_id, admin_user, reason):
    ensure_sandbox_enabled()
    payment = (
        SandboxPayment.objects.select_for_update()
        .select_related("contribution")
        .get(pk=payment_id)
    )
    if payment.status != SandboxPayment.Status.SUCCEEDED:
        raise ValidationError({"payment": "Only successful sandbox payments can be refunded."})
    if hasattr(payment, "sandbox_refund"):
        raise ValidationError({"payment": "A sandbox refund has already been recorded."})
    refund = SandboxRefund.objects.create(
        payment=payment,
        amount=payment.amount,
        currency=payment.currency,
        reason=reason[:500],
        processed_by=admin_user,
    )
    payment.status = SandboxPayment.Status.REFUNDED
    payment.save(update_fields=["status"])
    return refund
