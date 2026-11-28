from rest_framework.permissions import BasePermission


class IsJourneyOwner(BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.driver_id == request.user.id


class IsDriverAccount(BasePermission):
    message = "An active Driver account with a verified email is required."

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user and user.is_authenticated and user.is_active
            and user.role == "driver"
            and user.is_email_verified
        )


class IsVerifiedDriver(BasePermission):
    message = "Administrator-approved Driver verification and a registered mobile number are required."

    def has_permission(self, request, view):
        from apps.drivers.models import DriverProfile
        user = request.user
        return bool(
            user and user.is_authenticated and user.is_active
            and user.role == "driver"
            and user.is_email_verified
            and user.phone
            and getattr(getattr(user, "driver_profile", None), "verification_status", None)
                == DriverProfile.VerificationStatus.APPROVED
        )
