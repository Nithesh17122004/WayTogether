from pathlib import Path

from rest_framework import serializers

from .models import PassengerVerification
from .validators import validate_masked_aadhaar_file, validate_passenger_photo


class PassengerVerificationUploadSerializer(serializers.Serializer):
    masked_aadhaar_document = serializers.FileField(validators=[validate_masked_aadhaar_file])
    passenger_photo = serializers.FileField(validators=[validate_passenger_photo])
    consent = serializers.BooleanField()

    def validate_consent(self, value):
        if not value:
            raise serializers.ValidationError("Consent is required before submitting identity documents.")
        return value


class PassengerVerificationStatusSerializer(serializers.ModelSerializer):
    has_masked_aadhaar_document = serializers.SerializerMethodField()
    has_passenger_photo = serializers.SerializerMethodField()

    class Meta:
        model = PassengerVerification
        fields = (
            "status", "review_note", "submitted_at", "reviewed_at",
            "has_masked_aadhaar_document", "has_passenger_photo",
        )
        read_only_fields = fields

    def get_has_masked_aadhaar_document(self, obj):
        return bool(obj.masked_aadhaar_document)

    def get_has_passenger_photo(self, obj):
        return bool(obj.passenger_photo)


class AdminPassengerVerificationSerializer(serializers.ModelSerializer):
    owner_email = serializers.EmailField(source="user.email", read_only=True)
    owner_name = serializers.CharField(source="user.display_name", read_only=True)

    class Meta:
        model = PassengerVerification
        fields = (
            "id", "owner_email", "owner_name", "masked_aadhaar_file_name",
            "passenger_photo_file_name", "consent_at", "status", "review_note",
            "submitted_at",
        )
        read_only_fields = fields


class PassengerVerificationReviewSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=("approved", "rejected"))
    review_note = serializers.CharField(max_length=500, required=False, allow_blank=True, default="")

    def validate(self, attrs):
        if attrs["decision"] == "rejected" and not attrs.get("review_note", "").strip():
            raise serializers.ValidationError({"review_note": "A reason is required when rejecting verification."})
        return attrs


def safe_original_name(uploaded_file):
    return Path(uploaded_file.name).name[:255]
