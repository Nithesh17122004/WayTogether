from django.contrib import admin

from .models import DriverProfile, Vehicle, VerificationDocument


@admin.register(DriverProfile)
class DriverProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "city", "state", "verification_status", "submitted_at")
    list_filter = ("verification_status", "state")
    search_fields = ("user__email", "user__phone", "user__first_name", "user__last_name")
    readonly_fields = ("created_at", "updated_at")


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = (
        "registration_number", "owner", "make", "model",
        "verification_status", "private_use_attested",
    )
    list_filter = ("verification_status", "vehicle_type", "private_use_attested")
    search_fields = ("registration_number", "owner__email", "make", "model")
    readonly_fields = ("created_at", "updated_at")


@admin.register(VerificationDocument)
class VerificationDocumentAdmin(admin.ModelAdmin):
    list_display = (
        "owner", "document_type", "vehicle", "review_status",
        "is_current", "expiry_date", "uploaded_at",
    )
    list_filter = ("document_type", "review_status", "is_current")
    search_fields = ("owner__email", "owner__phone", "vehicle__registration_number")
    readonly_fields = (
        "owner", "vehicle", "document_type", "file", "original_file_name",
        "content_type", "file_size", "expiry_date", "review_status",
        "review_note", "reviewed_by", "reviewed_at", "is_current", "uploaded_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
