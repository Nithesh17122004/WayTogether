from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db import models
from django.db.models import Q


PHONE_VALIDATOR = RegexValidator(
    regex=r"^\+[1-9]\d{7,14}$",
    message="Enter an international-format phone number, such as +919876543210.",
)


class Notification(models.Model):
    class EventType(models.TextChoices):
        BOOKING_REQUEST = "booking_request", "Booking request"
        BOOKING_CONFIRMED = "booking_confirmed", "Booking confirmed"
        BOOKING_DECLINED = "booking_declined", "Booking declined"
        BOOKING_CANCELLED = "booking_cancelled", "Booking cancelled"
        JOURNEY_CANCELLED = "journey_cancelled", "Journey cancelled"
        NEW_MESSAGE = "new_message", "New message"
        EXPENSE_FINALIZED = "expense_finalized", "Expenses finalized"
        SAFETY_UPDATE = "safety_update", "Safety report update"

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="activity_notifications",
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="sent_activity_notifications",
        null=True,
        blank=True,
    )
    event_type = models.CharField(max_length=32, choices=EventType.choices)
    title = models.CharField(max_length=160)
    body = models.CharField(max_length=500)
    booking = models.ForeignKey(
        "bookings.Booking",
        on_delete=models.SET_NULL,
        related_name="notifications",
        null=True,
        blank=True,
    )
    journey = models.ForeignKey(
        "journeys.Journey",
        on_delete=models.SET_NULL,
        related_name="notifications",
        null=True,
        blank=True,
    )
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=("recipient", "read_at", "-created_at"), name="trust_notify_inbox_idx"),
        ]

    def __str__(self):
        return f"{self.recipient_id}: {self.title}"


class BookingMessage(models.Model):
    booking = models.ForeignKey(
        "bookings.Booking",
        on_delete=models.PROTECT,
        related_name="messages",
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="booking_messages",
    )
    content = models.CharField(max_length=1500)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("created_at", "id")
        indexes = [
            models.Index(fields=("booking", "created_at"), name="trust_message_thread_idx"),
        ]

    def __str__(self):
        return f"Message #{self.pk} · booking #{self.booking_id}"


class EmergencyContact(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="emergency_contacts",
    )
    contact_name = models.CharField(max_length=120)
    phone = models.CharField(max_length=16, validators=[PHONE_VALIDATOR])
    relationship = models.CharField(max_length=80, blank=True)
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-is_primary", "contact_name")
        constraints = [
            models.UniqueConstraint(fields=("user", "phone"), name="trust_unique_emergency_phone"),
        ]

    def __str__(self):
        return f"{self.contact_name} ({self.user_id})"


class SafetyReport(models.Model):
    class Category(models.TextChoices):
        UNSAFE_DRIVING = "unsafe_driving", "Unsafe driving"
        HARASSMENT = "harassment", "Harassment or inappropriate behaviour"
        MISREPRESENTATION = "misrepresentation", "Profile or journey misrepresentation"
        PAYMENT_DISPUTE = "payment_dispute", "Expense contribution dispute"
        ACCIDENT = "accident", "Accident or injury"
        OTHER = "other", "Other safety concern"

    class Priority(models.TextChoices):
        NORMAL = "normal", "Normal"
        HIGH = "high", "High"
        URGENT = "urgent", "Urgent"

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        REVIEWING = "reviewing", "Under review"
        RESOLVED = "resolved", "Resolved"
        CLOSED = "closed", "Closed"

    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="submitted_safety_reports",
    )
    reported_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="safety_reports_about_user",
        null=True,
        blank=True,
    )
    journey = models.ForeignKey(
        "journeys.Journey",
        on_delete=models.SET_NULL,
        related_name="safety_reports",
        null=True,
        blank=True,
    )
    booking = models.ForeignKey(
        "bookings.Booking",
        on_delete=models.SET_NULL,
        related_name="safety_reports",
        null=True,
        blank=True,
    )
    category = models.CharField(max_length=24, choices=Category.choices)
    priority = models.CharField(max_length=8, choices=Priority.choices, default=Priority.NORMAL)
    description = models.TextField(max_length=5000)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.OPEN)
    admin_note = models.CharField(max_length=1000, blank=True)
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="assigned_safety_reports",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=("status", "priority", "-created_at"), name="trust_report_queue_idx"),
            models.Index(fields=("reporter", "-created_at"), name="trust_report_owner_idx"),
        ]

    def __str__(self):
        return f"Safety report #{self.pk} · {self.category} · {self.status}"


class JourneyReview(models.Model):
    booking = models.ForeignKey(
        "bookings.Booking",
        on_delete=models.PROTECT,
        related_name="reviews",
    )
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="journey_reviews_written",
    )
    reviewee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="journey_reviews_received",
    )
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    comment = models.CharField(max_length=1000, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(fields=("booking", "reviewer"), name="trust_one_review_per_reviewer_booking"),
        ]
        indexes = [
            models.Index(fields=("reviewee", "-created_at"), name="trust_reviewee_rating_idx"),
        ]

    def __str__(self):
        return f"Review {self.rating}/5 for user #{self.reviewee_id}"
