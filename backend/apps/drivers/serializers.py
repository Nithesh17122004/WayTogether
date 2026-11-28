from pathlib import Path

from django.utils import timezone

from apps.accounts.models import User
from rest_framework import serializers

from .models import DriverProfile, Vehicle, VerificationDocument
from .validators import validate_document_file, validate_driver_profile_photo
from .services import recompute_driver_status, recompute_vehicle_status


class DriverProfileSerializer(serializers.ModelSerializer):
    verification_status_display = serializers.CharField(
        source="get_verification_status_display",
        read_only=True,
    )
    contact_phone = serializers.CharField(
        source="user.phone",
        required=False,
        allow_blank=True,
        allow_null=True,
        max_length=16,
    )
    driver_photo_url = serializers.SerializerMethodField()

    class Meta:
        model = DriverProfile
        fields = (
            "id", "bio", "city", "state", "contact_phone", "driver_photo_url", "verification_status",
            "verification_status_display", "submitted_at", "created_at", "updated_at",
        )
        read_only_fields = (
            "id", "driver_photo_url", "verification_status", "verification_status_display",
            "submitted_at", "created_at", "updated_at",
        )

    def validate_contact_phone(self, value):
        value = (value or "").strip()
        if not value:
            return None
        import re
        if not re.fullmatch(r"\+[1-9]\d{7,14}", value):
            raise serializers.ValidationError("Use international format, for example +919876543210.")
        request = self.context.get("request")
        if request and User.objects.filter(phone=value).exclude(pk=request.user.pk).exists():
            raise serializers.ValidationError("This contact number is already linked to another account.")
        return value

    def update(self, instance, validated_data):
        user_data = validated_data.pop("user", {})
        if "phone" in user_data:
            instance.user.phone = user_data["phone"] or None
            instance.user.save(update_fields=["phone"])
        return super().update(instance, validated_data)

    def get_driver_photo_url(self, obj):
        request = self.context.get("request")
        if not request:
            return None
        has_approved_photo = VerificationDocument.objects.filter(
            owner_id=obj.user_id,
            document_type=VerificationDocument.DocumentType.DRIVER_PHOTO,
            review_status=VerificationDocument.ReviewStatus.APPROVED,
            is_current=True,
        ).exists()
        if not has_approved_photo:
            return None
        from django.urls import reverse
        return request.build_absolute_uri(
            reverse("driver-public-photo", kwargs={"driver_id": obj.user_id})
        )


class VehicleSerializer(serializers.ModelSerializer):
    verification_status_display = serializers.CharField(
        source="get_verification_status_display",
        read_only=True,
    )

    class Meta:
        model = Vehicle
        fields = (
            "id", "registration_number", "make", "model", "manufacture_year",
            "colour", "vehicle_category", "vehicle_type", "passenger_seats", "private_use_attested",
            "verification_status", "verification_status_display", "created_at", "updated_at",
        )
        read_only_fields = (
            "id", "verification_status", "verification_status_display", "created_at", "updated_at",
        )

    def validate_registration_number(self, value):
        return "".join(value.upper().split())

    def validate_private_use_attested(self, value):
        if not value:
            raise serializers.ValidationError(
                "You must confirm that this is a privately used vehicle and not being registered as a commercial taxi."
            )
        return value

    def validate(self, attrs):
        instance = self.instance
        category = attrs.get(
            "vehicle_category",
            getattr(instance, "vehicle_category", Vehicle.VehicleCategory.FOUR_WHEELER),
        )
        vehicle_type = attrs.get("vehicle_type", getattr(instance, "vehicle_type", None))
        passenger_seats = attrs.get("passenger_seats", getattr(instance, "passenger_seats", 1))
        two_wheeler_types = {
            Vehicle.VehicleType.MOTORCYCLE,
            Vehicle.VehicleType.SCOOTER,
            Vehicle.VehicleType.OTHER,
        }
        four_wheeler_types = {
            Vehicle.VehicleType.HATCHBACK,
            Vehicle.VehicleType.SEDAN,
            Vehicle.VehicleType.SUV,
            Vehicle.VehicleType.MUV,
            Vehicle.VehicleType.OTHER,
        }
        allowed_types = two_wheeler_types if category == Vehicle.VehicleCategory.TWO_WHEELER else four_wheeler_types
        if vehicle_type not in allowed_types:
            raise serializers.ValidationError({
                "vehicle_type": "Choose a vehicle subtype that matches the selected two-wheel or four-wheel category."
            })
        if category == Vehicle.VehicleCategory.TWO_WHEELER and passenger_seats > 1:
            raise serializers.ValidationError({
                "passenger_seats": "A two-wheeler can offer one passenger seat."
            })
        return attrs

    def create(self, validated_data):
        return Vehicle.objects.create(owner=self.context["request"].user, **validated_data)

    def update(self, instance, validated_data):
        identity_fields = {
            "registration_number", "make", "model", "manufacture_year",
            "vehicle_category", "vehicle_type", "passenger_seats", "colour",
        }
        changed_identity = any(
            field in validated_data and getattr(instance, field) != validated_data[field]
            for field in identity_fields
        )
        vehicle = super().update(instance, validated_data)
        if changed_identity:
            # A changed vehicle record must be checked against its RC/insurance
            # again. Re-queue the current documents rather than retaining stale
            # approvals against changed vehicle details.
            VerificationDocument.objects.filter(
                vehicle=vehicle,
                is_current=True,
            ).update(
                review_status=VerificationDocument.ReviewStatus.PENDING,
                review_note="",
                reviewed_by=None,
                reviewed_at=None,
            )
            recompute_vehicle_status(vehicle)
            recompute_driver_status(vehicle.owner)
        return vehicle


class VerificationDocumentSerializer(serializers.ModelSerializer):
    file = serializers.FileField(write_only=True, validators=[validate_document_file])
    download_url = serializers.SerializerMethodField()
    vehicle_registration = serializers.CharField(
        source="vehicle.registration_number",
        read_only=True,
        default=None,
    )
    review_status_display = serializers.CharField(source="get_review_status_display", read_only=True)

    class Meta:
        model = VerificationDocument
        fields = (
            "id", "document_type", "vehicle", "vehicle_registration", "file",
            "original_file_name", "content_type", "file_size", "expiry_date",
            "review_status", "review_status_display", "review_note", "reviewed_at",
            "is_current", "uploaded_at", "download_url",
        )
        read_only_fields = (
            "id", "original_file_name", "content_type", "file_size", "review_status",
            "review_status_display", "review_note", "reviewed_at", "is_current",
            "uploaded_at", "download_url",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            self.fields["vehicle"].queryset = Vehicle.objects.filter(owner=request.user)
        else:
            self.fields["vehicle"].queryset = Vehicle.objects.none()

    def get_download_url(self, obj):
        request = self.context.get("request")
        if not request:
            return None
        from django.urls import reverse
        url = reverse("driver-document-download", kwargs={"document_id": obj.pk})
        return request.build_absolute_uri(url)

    def validate(self, attrs):
        document_type = attrs.get("document_type", getattr(self.instance, "document_type", None))
        vehicle = attrs.get("vehicle", getattr(self.instance, "vehicle", None))
        vehicle_document_types = {
            VerificationDocument.DocumentType.VEHICLE_REGISTRATION,
            VerificationDocument.DocumentType.INSURANCE,
            VerificationDocument.DocumentType.POLLUTION_CERTIFICATE,
            VerificationDocument.DocumentType.VEHICLE_PHOTO,
        }
        if document_type in vehicle_document_types and vehicle is None:
            raise serializers.ValidationError({"vehicle": "Select the vehicle this document belongs to."})
        if document_type in {
            VerificationDocument.DocumentType.DRIVER_LICENSE,
            VerificationDocument.DocumentType.DRIVER_PHOTO,
        } and vehicle is not None:
            raise serializers.ValidationError({"vehicle": "Driver identity documents do not belong to a vehicle."})
        if document_type == VerificationDocument.DocumentType.DRIVER_PHOTO and attrs.get("file"):
            try:
                validate_driver_profile_photo(attrs["file"])
            except Exception as exc:
                raise serializers.ValidationError({"file": str(exc)})

        expiry_date = attrs.get("expiry_date")
        if expiry_date and expiry_date < timezone.localdate():
            raise serializers.ValidationError({"expiry_date": "The document expiry date cannot be in the past."})
        return attrs

    def create(self, validated_data):
        request = self.context["request"]
        uploaded_file = validated_data.pop("file")
        document_type = validated_data["document_type"]
        vehicle = validated_data.get("vehicle")
        owner = request.user

        VerificationDocument.objects.filter(
            owner=owner,
            document_type=document_type,
            vehicle=vehicle,
            is_current=True,
        ).update(is_current=False)

        document = VerificationDocument(
            owner=owner,
            file=uploaded_file,
            original_file_name=Path(uploaded_file.name).name,
            content_type=getattr(uploaded_file, "content_type", "") or "application/octet-stream",
            file_size=uploaded_file.size,
            **validated_data,
        )
        document.full_clean()
        document.save()

        profile, _ = DriverProfile.objects.get_or_create(user=owner)
        if profile.submitted_at is None:
            profile.submitted_at = timezone.now()
            profile.save(update_fields=["submitted_at", "updated_at"])

        # Every uploaded document is independently reviewable. The admin queue
        # receives this document immediately; the overall profile/vehicle
        # remains pending until all mandatory documents are approved.
        if vehicle:
            recompute_vehicle_status(vehicle)
        recompute_driver_status(owner)
        return document


class AdminVerificationDocumentSerializer(serializers.ModelSerializer):
    owner_email = serializers.EmailField(source="owner.email", read_only=True)
    owner_name = serializers.CharField(source="owner.display_name", read_only=True)
    vehicle_registration = serializers.CharField(source="vehicle.registration_number", read_only=True, default=None)
    vehicle_category = serializers.CharField(source="vehicle.vehicle_category", read_only=True, default=None)
    vehicle_type = serializers.CharField(source="vehicle.vehicle_type", read_only=True, default=None)
    document_type_display = serializers.CharField(source="get_document_type_display", read_only=True)
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = VerificationDocument
        fields = (
            "id", "owner_email", "owner_name", "vehicle", "vehicle_registration",
            "vehicle_category", "vehicle_type", "document_type", "document_type_display", "original_file_name", "content_type",
            "file_size", "expiry_date", "review_status", "review_note", "uploaded_at",
            "download_url",
        )

    def get_download_url(self, obj):
        request = self.context.get("request")
        if not request:
            return None
        from django.urls import reverse
        return request.build_absolute_uri(
            reverse("driver-document-download", kwargs={"document_id": obj.pk})
        )


class DocumentReviewSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=("approved", "rejected"))
    review_note = serializers.CharField(max_length=500, required=False, allow_blank=True, default="")

    def validate(self, attrs):
        if attrs["decision"] == "rejected" and not attrs.get("review_note", "").strip():
            raise serializers.ValidationError({"review_note": "A reason is required when rejecting a document."})
        return attrs
