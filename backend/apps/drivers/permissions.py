from rest_framework.permissions import BasePermission


class IsDriverAccount(BasePermission):
    message = "A verified driver account is required for this action."

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and user.is_active
            and user.role == "driver"
            and user.is_email_verified
        )


class IsPlatformAdmin(BasePermission):
    message = "Administrator access is required."

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.is_active and user.is_staff)
