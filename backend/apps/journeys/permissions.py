from rest_framework.permissions import BasePermission


class IsJourneyOwner(BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.driver_id == request.user.id


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
            and user.is_phone_verified
        )
