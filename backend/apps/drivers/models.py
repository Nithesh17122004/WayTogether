import uuid
from pathlib import Path

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.text import get_valid_filename

from .storage import get_private_driver_storage
from .validators import validate_document_file, validate_driver_profile_photo


def private_driver_photo_upload_to(instance, filename):
    suffix = Path(filename).suffix.lower()
    return f"private/driver-profile/{instance.user_id}/{uuid.uuid4().hex}{suffix}"


def private_document_upload_to(instance, filename):
    suffix = Path(filename).suffix.lower()
    return f"private/driver-verification/{instance.owner_id}/{uuid.uuid4().hex}{suffix}"


class DriverProfile(models.Model):
    class VerificationStatus(models.TextChoices):
        DRAFT = "draft", "Draft"
        PENDING = "pending", "Pending review"
        APPROVED = "approved", "Approved"
        NEEDS_RESUBMISSION = "needs_resubmission", "Needs resubmission"
        SUSPENDED = "suspended", "Suspended"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="driver_profile",
    )
    bio = models.CharField(max_length=500, blank=True)
    profile_photo = models.FileField(
        upload_to=private_driver_photo_upload_to,
        storage=get_private_driver_storage,
        validators=[validate_driver_profile_photo],
        blank=True,
        max_length=255,
    )
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    verification_status = models.CharField(
        max_length=24,
        choices=VerificationStatus.choices,
        default=VerificationStatus.DRAFT,
    )
    submitted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Driver profile: {self.user.email}"


class Vehicle(models.Model):
    class VehicleType(models.TextChoices):
        HATCHBACK = "hatchback", "Hatchback"
        SEDAN = "sedan", "Sedan"
        SUV = "suv", "SUV"
        MUV = "muv", "MUV"
        OTHER = "other", "Other"

    class VerificationStatus(models.TextChoices):
        DRAFT = "draft", "Draft"
        PENDING = "pending", "Pending review"
        APPROVED = "approved", "Approved"
        NEEDS_RESUBMISSION = "needs_resubmission", "Needs resubmission"
        SUSPENDED = "suspended", "Suspended"

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="vehicles",
    )
    registration_number = models.CharField(max_length=20, unique=True)
    make = models.CharField(max_length=60)
    model = models.CharField(max_length=60)
    manufacture_year = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1980), MaxValueValidator(2100)]
    )
    colour = models.CharField(max_length=40, blank=True)
    vehicle_type = models.CharField(max_length=12, choices=VehicleType.choices)
    passenger_seats = models.PositiveSmallIntegerField(
        default=3,
        validators=[MinValueValidator(1), MaxValueValidator(8)],
    )
    private_use_attested = models.BooleanField(default=False)
    verification_status = models.CharField(
        max_length=24,
        choices=VerificationStatus.choices,
        default=VerificationStatus.DRAFT,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)

    def save(self, *args, **kwargs):
        self.registration_number = "".join(self.registration_number.upper().split())
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.registration_number} · {self.make} {self.model}"


class VerificationDocument(models.Model):
    class DocumentType(models.TextChoices):
        DRIVER_LICENSE = "driver_license", "Driving licence"
        VEHICLE_REGISTRATION = "vehicle_registration", "Vehicle registration certificate"
        INSURANCE = "insurance", "Insurance certificate"
        POLLUTION_CERTIFICATE = "pollution_certificate", "Pollution certificate"
        VEHICLE_PHOTO = "vehicle_photo", "Vehicle photograph"
        DRIVER_PHOTO = "driver_photo", "Driver face photo"

    class ReviewStatus(models.TextChoices):
        PENDING = "pending", "Pending review"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="driver_documents",
    )
    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.CASCADE,
        related_name="documents",
        null=True,
        blank=True,
    )
    document_type = models.CharField(max_length=32, choices=DocumentType.choices)
    file = models.FileField(
        upload_to=private_document_upload_to,
        storage=get_private_driver_storage,
        validators=[validate_document_file],
        max_length=255,
    )
    original_file_name = models.CharField(max_length=255)
    content_type = models.CharField(max_length=80)
    file_size = models.PositiveIntegerField()
    expiry_date = models.DateField(null=True, blank=True)
    review_status = models.CharField(
        max_length=12,
        choices=ReviewStatus.choices,
        default=ReviewStatus.PENDING,
    )
    review_note = models.CharField(max_length=500, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="reviewed_driver_documents",
        null=True,
        blank=True,
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    is_current = models.BooleanField(default=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-uploaded_at",)
        indexes = [
            models.Index(
                fields=("owner", "document_type", "is_current"),
                name="driver_doc_current_idx",
            ),
            models.Index(
                fields=("review_status", "is_current"),
                name="driver_doc_review_idx",
            ),
        ]

    def clean(self):
        super().clean()
        vehicle_document_types = {
            self.DocumentType.VEHICLE_REGISTRATION,
            self.DocumentType.INSURANCE,
            self.DocumentType.POLLUTION_CERTIFICATE,
            self.DocumentType.VEHICLE_PHOTO,
        }
        if self.document_type in vehicle_document_types and not self.vehicle_id:
            from django.core.exceptions import ValidationError
            raise ValidationError({"vehicle": "Select the vehicle this document belongs to."})
        if self.document_type in {self.DocumentType.DRIVER_LICENSE, self.DocumentType.DRIVER_PHOTO} and self.vehicle_id:
            from django.core.exceptions import ValidationError
            raise ValidationError({"vehicle": "A driver identity document belongs to the driver, not a vehicle."})
        if self.vehicle_id and self.vehicle.owner_id != self.owner_id:
            from django.core.exceptions import ValidationError
            raise ValidationError({"vehicle": "The selected vehicle does not belong to this driver."})

    def save(self, *args, **kwargs):
        if self.original_file_name:
            self.original_file_name = get_valid_filename(Path(self.original_file_name).name)[:255]
        super().save(*args, **kwargs)

    @property
    def is_expired(self):
        return bool(self.expiry_date and self.expiry_date < timezone.localdate())

    def __str__(self):
        return f"{self.get_document_type_display()} · {self.owner.email}"
