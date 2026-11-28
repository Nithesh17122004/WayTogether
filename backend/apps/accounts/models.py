from pathlib import Path
import uuid

from django.conf import settings
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone

from .storage import get_private_passenger_storage
from .validators import validate_masked_aadhaar_file, validate_passenger_photo


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("An email address is required.")
        email = self.normalize_email(email).strip().lower()
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("is_email_verified", True)
        extra_fields.setdefault("role", "admin")
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    class Role(models.TextChoices):
        PASSENGER = "passenger", "Passenger"
        DRIVER = "driver", "Driver"
        ADMIN = "admin", "Administrator"

    username = None
    email = models.EmailField(unique=True)
    phone = models.CharField(
        max_length=16,
        unique=True,
        null=True,
        blank=True,
        default=None,
        validators=[
            RegexValidator(
                regex=r"^\+[1-9]\d{7,14}$",
                message="Enter a mobile number in international format, such as +919876543210.",
            )
        ],
    )
    role = models.CharField(max_length=12, choices=Role.choices, default=Role.PASSENGER)
    is_email_verified = models.BooleanField(default=False)
    is_phone_verified = models.BooleanField(default=False)
    terms_accepted_at = models.DateTimeField(null=True, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.email.strip().lower()
        super().save(*args, **kwargs)

    @property
    def display_name(self):
        return self.get_full_name().strip() or self.email

    def __str__(self):
        return self.email


class VerificationCode(models.Model):
    class Channel(models.TextChoices):
        EMAIL = "email", "Email"
        PHONE = "phone", "Phone"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="verification_codes")
    channel = models.CharField(max_length=8, choices=Channel.choices)
    code_hash = models.CharField(max_length=256)
    expires_at = models.DateTimeField()
    attempts = models.PositiveSmallIntegerField(default=0)
    verified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=("user", "channel", "-created_at"), name="acct_code_latest_idx"),
        ]

    def __str__(self):
        return f"{self.user.email} · {self.channel} · {self.created_at:%Y-%m-%d %H:%M}"



def private_passenger_upload_to(instance, filename):
    suffix = Path(filename).suffix.lower()
    return f"private/passenger-verification/{instance.user_id}/{uuid.uuid4().hex}{suffix}"


class PassengerVerification(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending review"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="passenger_verification",
    )
    # Store only a masked Aadhaar copy (first eight digits hidden). Never store
    # the full Aadhaar number or biometric data in a database field.
    masked_aadhaar_document = models.FileField(
        upload_to=private_passenger_upload_to,
        storage=get_private_passenger_storage,
        validators=[validate_masked_aadhaar_file],
        max_length=255,
    )
    passenger_photo = models.FileField(
        upload_to=private_passenger_upload_to,
        storage=get_private_passenger_storage,
        validators=[validate_passenger_photo],
        max_length=255,
    )
    masked_aadhaar_file_name = models.CharField(max_length=255)
    passenger_photo_file_name = models.CharField(max_length=255)
    consent_at = models.DateTimeField()
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    review_note = models.CharField(max_length=500, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="reviewed_passenger_verifications",
        null=True,
        blank=True,
    )
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("submitted_at",)
        indexes = [
            models.Index(fields=("status", "submitted_at"), name="passenger_kyc_queue_idx"),
        ]

    def __str__(self):
        return f"Passenger verification: {self.user.email} · {self.status}"
