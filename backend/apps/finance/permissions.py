from rest_framework.permissions import BasePermission


class IsVerifiedPassenger(BasePermission):
    message = "A verified Passenger account is required."

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user and user.is_authenticated and user.is_active
            and user.role == "passenger"
            and user.is_email_verified
            and getattr(getattr(user, "passenger_verification", None), "status", None) == "approved"
        )


class IsVerifiedDriver(BasePermission):
    message = "A verified Driver account is required."

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user and user.is_authenticated and user.is_active
            and user.role == "driver"
            and user.is_email_verified
        )
