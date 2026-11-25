from rest_framework.permissions import BasePermission


class IsBookingParticipant(BasePermission):
    message = "Only the passenger or driver on this booking can access this thread."

    def has_object_permission(self, request, view, obj):
        return obj.passenger_id == request.user.id or obj.journey.driver_id == request.user.id
