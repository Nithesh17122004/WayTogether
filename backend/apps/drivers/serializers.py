from pathlib import Path

from django.utils import timezone
from rest_framework import serializers

from .models import DriverProfile, Vehicle, VerificationDocument
from .validators import validate_document_file


class DriverProfileSerializer(serializers.ModelSerializer):
    verification_status_display = serializers.CharField(
        source="get_verification_status_display",
        read_only=True,
    )

    class Meta:
        model = DriverProfile
        fields = (
            "id", "bio", "city", "state", "verification_status",
            "verification_status_display", "submitted_at", "created_at", "updated_at",
        )
        read_only_fields = (
            "id", "verification_status", "verification_status_display",
            "submitted_at", "created_at", "updated_at",
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
            "colour", "vehicle_type", "passenger_seats", "private_use_attested",
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
        if instance and instance.verification_status == Vehicle.VerificationStatus.APPROVED:
            protected_fields = {"registration_number", "make", "model", "manufacture_year", "vehicle_type"}
            if protected_fields.intersection(attrs):
                raise serializers.ValidationError(
                    "An approved vehicle's identity details cannot be edited. Contact support if a correction is required."
                )
        return attrs

    def create(self, validated_data):
        return Vehicle.objects.create(owner=self.context["request"].user, **validated_data)


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
        if document_type == VerificationDocument.DocumentType.DRIVER_LICENSE and vehicle is not None:
            raise serializers.ValidationError({"vehicle": "A driving licence belongs to the driver, not a vehicle."})

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

        profile = DriverProfile.objects.filter(user=owner).first()
        if profile and profile.verification_status in (
            DriverProfile.VerificationStatus.APPROVED,
            DriverProfile.VerificationStatus.NEEDS_RESUBMISSION,
        ):
            profile.verification_status = DriverProfile.VerificationStatus.NEEDS_RESUBMISSION
            profile.save(update_fields=["verification_status", "updated_at"])
        if vehicle and vehicle.verification_status in (
            Vehicle.VerificationStatus.APPROVED,
            Vehicle.VerificationStatus.NEEDS_RESUBMISSION,
        ):
            vehicle.verification_status = Vehicle.VerificationStatus.NEEDS_RESUBMISSION
            vehicle.save(update_fields=["verification_status", "updated_at"])
        return document


class AdminVerificationDocumentSerializer(serializers.ModelSerializer):
    owner_email = serializers.EmailField(source="owner.email", read_only=True)
    owner_name = serializers.CharField(source="owner.display_name", read_only=True)
    vehicle_registration = serializers.CharField(source="vehicle.registration_number", read_only=True, default=None)
    document_type_display = serializers.CharField(source="get_document_type_display", read_only=True)
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = VerificationDocument
        fields = (
            "id", "owner_email", "owner_name", "vehicle", "vehicle_registration",
            "document_type", "document_type_display", "original_file_name", "content_type",
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
