from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone


class Booking(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending driver response"
        CONFIRMED = "confirmed", "Confirmed"
        DECLINED = "declined", "Declined"
        CANCELLED = "cancelled", "Cancelled"

    journey = models.ForeignKey(
        "journeys.Journey",
        on_delete=models.PROTECT,
        related_name="bookings",
    )
    passenger = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="journey_bookings",
    )
    seats_requested = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(8)]
    )
    request_message = models.CharField(max_length=500, blank=True)
    driver_response = models.CharField(max_length=500, blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    estimated_contribution_per_passenger = models.DecimalField(
        max_digits=9, decimal_places=2, default=Decimal("0.00")
    )
    estimated_contribution_total = models.DecimalField(
        max_digits=9, decimal_places=2, default=Decimal("0.00")
    )
    requested_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    responded_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancelled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="cancelled_journey_bookings",
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ("-requested_at",)
        constraints = [
            models.UniqueConstraint(
                fields=("journey", "passenger"),
                condition=Q(status__in=("pending", "confirmed")),
                name="one_active_booking_per_passenger_journey",
            ),
        ]
        indexes = [
            models.Index(fields=("journey", "status"), name="booking_journey_status_idx"),
            models.Index(fields=("passenger", "status"), name="booking_passenger_status_idx"),
            models.Index(fields=("status", "requested_at"), name="booking_status_requested_idx"),
        ]

    def __str__(self):
        return f"Booking #{self.pk} · journey #{self.journey_id} · {self.passenger.email}"

    @property
    def is_active(self):
        return self.status in (self.Status.PENDING, self.Status.CONFIRMED)

    @property
    def has_departed(self):
        now = timezone.localtime()
        departure = timezone.make_aware(
            timezone.datetime.combine(self.journey.travel_date, self.journey.departure_time),
            timezone.get_current_timezone(),
        )
        return now >= departure
