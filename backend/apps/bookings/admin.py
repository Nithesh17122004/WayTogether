from django.contrib import admin

from .models import Booking


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = (
        "id", "journey", "passenger", "seats_requested",
        "status", "estimated_contribution_total", "requested_at",
    )
    list_filter = ("status", "requested_at")
    search_fields = (
        "passenger__email", "passenger__phone",
        "journey__origin_name", "journey__destination_name",
    )
    readonly_fields = (
        "journey", "passenger", "seats_requested", "request_message",
        "driver_response", "status", "estimated_contribution_per_passenger",
        "estimated_contribution_total", "requested_at", "updated_at",
        "responded_at", "cancelled_at", "cancelled_by",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
