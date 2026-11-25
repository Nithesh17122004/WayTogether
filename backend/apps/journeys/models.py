from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone


class Journey(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"
        CANCELLED = "cancelled", "Cancelled"
        COMPLETED = "completed", "Completed"

    driver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="journeys",
    )
    vehicle = models.ForeignKey(
        "drivers.Vehicle",
        on_delete=models.PROTECT,
        related_name="journeys",
    )
    origin_name = models.CharField(max_length=200)
    origin_latitude = models.DecimalField(max_digits=10, decimal_places=7)
    origin_longitude = models.DecimalField(max_digits=10, decimal_places=7)
    destination_name = models.CharField(max_length=200)
    destination_latitude = models.DecimalField(max_digits=10, decimal_places=7)
    destination_longitude = models.DecimalField(max_digits=10, decimal_places=7)
    travel_date = models.DateField(db_index=True)
    departure_time = models.TimeField()
    seats_offered = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(8)]
    )
    fuel_expense = models.DecimalField(max_digits=9, decimal_places=2, default=0)
    toll_expense = models.DecimalField(max_digits=9, decimal_places=2, default=0)
    parking_expense = models.DecimalField(max_digits=9, decimal_places=2, default=0)
    other_expense = models.DecimalField(max_digits=9, decimal_places=2, default=0)
    expense_note = models.CharField(max_length=500, blank=True)
    description = models.CharField(max_length=1000, blank=True)
    route_distance_km = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    route_duration_minutes = models.PositiveIntegerField(null=True, blank=True)
    route_geometry = models.JSONField(default=list, blank=True)
    independently_planned = models.BooleanField(default=False)
    expenses_only = models.BooleanField(default=False)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.DRAFT)
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("travel_date", "departure_time")
        indexes = [
            models.Index(fields=("status", "travel_date"), name="journey_status_date_idx"),
            models.Index(fields=("driver", "status"), name="journey_driver_status_idx"),
            models.Index(fields=("origin_latitude", "origin_longitude"), name="journey_origin_coords_idx"),
            models.Index(fields=("destination_latitude", "destination_longitude"), name="journey_dest_coords_idx"),
        ]

    @property
    def estimated_total_expenses(self):
        return (
            self.fuel_expense
            + self.toll_expense
            + self.parking_expense
            + self.other_expense
        )

    @property
    def estimated_contribution_per_passenger(self):
        # Early estimate assumes every offered passenger seat is occupied.
        # Final expense allocation is recalculated at booking time in Phase 6.
        people_count = self.seats_offered + 1  # includes the driver
        return (self.estimated_total_expenses / people_count).quantize(
            self.fuel_expense.as_tuple().exponent and self.fuel_expense.__class__("0.01")
        )

    def __str__(self):
        return f"{self.origin_name} → {self.destination_name} on {self.travel_date}"


class JourneyStop(models.Model):
    journey = models.ForeignKey(Journey, on_delete=models.CASCADE, related_name="stops")
    sequence = models.PositiveSmallIntegerField()
    location_name = models.CharField(max_length=200)
    latitude = models.DecimalField(max_digits=10, decimal_places=7)
    longitude = models.DecimalField(max_digits=10, decimal_places=7)

    class Meta:
        ordering = ("sequence",)
        constraints = [
            models.UniqueConstraint(fields=("journey", "sequence"), name="unique_journey_stop_sequence"),
        ]

    def __str__(self):
        return f"{self.sequence}. {self.location_name}"
