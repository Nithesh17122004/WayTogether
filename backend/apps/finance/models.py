import uuid
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q


class ExpenseSettlement(models.Model):
    """
    Driver-declared final eligible expenses for a completed journey.
    This is a cost allocation record, not a fare or driver earning.
    """
    journey = models.OneToOneField(
        "journeys.Journey",
        on_delete=models.PROTECT,
        related_name="expense_settlement",
    )
    driver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="submitted_expense_settlements",
    )
    actual_fuel_expense = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"), validators=[MinValueValidator(0)])
    actual_toll_expense = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    actual_parking_expense = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    actual_other_expense = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    actual_expense_note = models.CharField(max_length=1000, blank=True)
    eligible_total = models.DecimalField(max_digits=11, decimal_places=2, default=0)
    driver_share = models.DecimalField(max_digits=11, decimal_places=2, default=0)
    passenger_seat_count = models.PositiveSmallIntegerField(default=0)
    currency = models.CharField(max_length=3, default="INR")
    is_finalized = models.BooleanField(default=False)
    submitted_at = models.DateTimeField(auto_now_add=True)
    finalized_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-submitted_at",)

    @property
    def total_people(self):
        return self.passenger_seat_count + 1

    def __str__(self):
        return f"Expense settlement for journey #{self.journey_id}"


class PassengerContribution(models.Model):
    """Immutable passenger share calculated when the driver finalizes expenses."""
    booking = models.OneToOneField(
        "bookings.Booking",
        on_delete=models.PROTECT,
        related_name="final_contribution",
    )
    settlement = models.ForeignKey(
        ExpenseSettlement,
        on_delete=models.PROTECT,
        related_name="contributions",
    )
    passenger = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="final_journey_contributions",
    )
    seat_count = models.PositiveSmallIntegerField()
    per_seat_amount = models.DecimalField(max_digits=11, decimal_places=2)
    total_amount = models.DecimalField(max_digits=11, decimal_places=2)
    currency = models.CharField(max_length=3, default="INR")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("created_at", "id")
        indexes = [
            models.Index(fields=("passenger", "created_at"), name="finance_passenger_date_idx"),
            models.Index(fields=("settlement", "created_at"), name="finance_settlement_date_idx"),
        ]

    def __str__(self):
        return f"Contribution for booking #{self.booking_id}: {self.total_amount} {self.currency}"


class SandboxPayment(models.Model):
    """
    A fake payment record for workflow testing only. It never calls a payment
    provider, moves money, or creates a real payment order.
    """
    class Status(models.TextChoices):
        CREATED = "created", "Sandbox initiated"
        SUCCEEDED = "succeeded", "Sandbox successful"
        FAILED = "failed", "Sandbox failed"
        REFUNDED = "refunded", "Sandbox refunded"

    contribution = models.ForeignKey(
        PassengerContribution,
        on_delete=models.PROTECT,
        related_name="sandbox_payments",
    )
    reference = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    provider = models.CharField(max_length=24, default="sandbox", editable=False)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.CREATED)
    amount = models.DecimalField(max_digits=11, decimal_places=2)
    currency = models.CharField(max_length=3, default="INR")
    failure_note = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(
                fields=("contribution",),
                condition=Q(status__in=("created", "succeeded")),
                name="one_active_sandbox_payment_per_share",
            ),
        ]
        indexes = [
            models.Index(fields=("status", "created_at"), name="finance_payment_status_idx"),
        ]

    def __str__(self):
        return f"Sandbox payment {self.reference} · {self.status}"


class SandboxRefund(models.Model):
    """Administrative, simulated refund record; no money is sent."""
    payment = models.OneToOneField(
        SandboxPayment,
        on_delete=models.PROTECT,
        related_name="sandbox_refund",
    )
    reference = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    amount = models.DecimalField(max_digits=11, decimal_places=2)
    currency = models.CharField(max_length=3, default="INR")
    reason = models.CharField(max_length=500)
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="processed_sandbox_refunds",
    )
    processed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Sandbox refund {self.reference}"
