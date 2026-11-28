from rest_framework.permissions import BasePermission
from apps.drivers.models import DriverProfile


class IsVerifiedPassenger(BasePermission):
    message = "A verified Passenger account is required."

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and user.is_active
            and user.role == "passenger"
            and user.is_email_verified
            and bool(user.phone)
            and getattr(getattr(user, "passenger_verification", None), "status", None) == "approved"
        )


class IsVerifiedDriver(BasePermission):
    message = "A verified Driver account is required."

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and user.is_active
            and user.role == "driver"
            and user.is_email_verified
            and bool(user.phone)
            and getattr(getattr(user, "driver_profile", None), "verification_status", None) == DriverProfile.VerificationStatus.APPROVED
        )
