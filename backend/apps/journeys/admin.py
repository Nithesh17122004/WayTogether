from django.contrib import admin

from .models import Journey, JourneyStop


class JourneyStopInline(admin.TabularInline):
    model = JourneyStop
    extra = 0
    readonly_fields = ("sequence", "location_name", "latitude", "longitude")


@admin.register(Journey)
class JourneyAdmin(admin.ModelAdmin):
    list_display = (
        "id", "origin_name", "destination_name", "travel_date",
        "driver", "vehicle", "seats_offered", "status",
    )
    list_filter = ("status", "travel_date")
    search_fields = (
        "origin_name", "destination_name", "driver__email",
        "vehicle__registration_number",
    )
    readonly_fields = (
        "driver", "vehicle", "origin_name", "origin_latitude", "origin_longitude",
        "destination_name", "destination_latitude", "destination_longitude",
        "travel_date", "departure_time", "seats_offered", "fuel_expense",
        "toll_expense", "parking_expense", "other_expense", "expense_note",
        "description", "route_distance_km", "route_duration_minutes",
        "route_geometry", "independently_planned", "expenses_only",
        "status", "published_at", "created_at", "updated_at",
    )
    inlines = [JourneyStopInline]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
