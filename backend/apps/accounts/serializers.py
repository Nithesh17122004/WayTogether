from django.contrib.auth import authenticate, password_validation
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import User


class UserPublicSerializer(serializers.ModelSerializer):
    display_name = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = (
            "id", "email", "phone", "first_name", "last_name", "display_name",
            "role", "is_email_verified", "date_joined",
        )
        read_only_fields = fields


class RegisterSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    phone = serializers.RegexField(
        regex=r"^\+[1-9]\d{7,14}$",
        max_length=16,
        required=True,
        allow_null=False,
        allow_blank=False,
        error_messages={
            "invalid": "Use international phone format, for example +919876543210.",
            "required": "A mobile number is required for every passenger and driver account.",
        },
    )
    password = serializers.CharField(write_only=True, min_length=8, trim_whitespace=False)
    role = serializers.ChoiceField(choices=(User.Role.PASSENGER, User.Role.DRIVER))
    accepted_terms = serializers.BooleanField()

    def validate_email(self, value):
        value = value.strip().lower()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return value

    def validate_phone(self, value):
        value = value.strip() if isinstance(value, str) else value
        if not value:
            raise serializers.ValidationError("A registered mobile number is required.")
        if User.objects.filter(phone=value).exists():
            raise serializers.ValidationError("An account with this mobile number already exists.")
        return value

    def validate_accepted_terms(self, value):
        if not value:
            raise serializers.ValidationError("You must accept the terms to create an account.")
        return value

    def validate(self, attrs):
        name = " ".join(attrs["full_name"].strip().split())
        if len(name) < 2:
            raise serializers.ValidationError({"full_name": "Enter your full name."})
        attrs["full_name"] = name
        if attrs["role"] == User.Role.DRIVER and not attrs.get("phone"):
            raise serializers.ValidationError({
                "phone": "Drivers must provide a contact number for passengers after a confirmed, paid booking. Phone OTP verification is not required."
            })
        candidate = User(email=attrs["email"], phone=attrs.get("phone"), first_name=name)
        try:
            password_validation.validate_password(attrs["password"], user=candidate)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": list(exc.messages)}) from exc
        return attrs

    def create(self, validated_data):
        full_name = validated_data.pop("full_name")
        validated_data.pop("accepted_terms")
        password = validated_data.pop("password")
        first_name, _, last_name = full_name.partition(" ")
        user = User.objects.create_user(
            password=password,
            first_name=first_name,
            last_name=last_name,
            terms_accepted_at=timezone.now(),
            **validated_data,
        )
        return user



class CurrentUserPhoneSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    phone = serializers.RegexField(
        regex=r"^\+[1-9]\d{7,14}$",
        max_length=16,
        error_messages={"invalid": "Use international phone format, for example +919876543210."},
    )

    def validate_first_name(self, value):
        return value.strip()

    def validate_last_name(self, value):
        return value.strip()

    def validate_phone(self, value):
        value = value.strip()
        user = self.context["request"].user
        if User.objects.filter(phone=value).exclude(pk=user.pk).exists():
            raise serializers.ValidationError("This mobile number is already linked to another account.")
        return value


class WayTogetherTokenSerializer(TokenObtainPairSerializer):
    username_field = User.USERNAME_FIELD

    def validate(self, attrs):
        data = super().validate(attrs)
        user = self.user
        if not user.is_active:
            raise serializers.ValidationError("This account is inactive. Contact support.")
        # Allow sign-in before email OTP confirmation. The account remains
        # restricted from verified-only actions until is_email_verified is True.
        data["user"] = UserPublicSerializer(user).data
        return data
