from django.contrib import admin

from .models import BookingMessage, JourneyReview, Notification, SafetyReport


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("id", "recipient", "event_type", "title", "read_at", "created_at")
    list_filter = ("event_type", "read_at", "created_at")
    search_fields = ("recipient__email", "actor__email", "title")
    readonly_fields = tuple(field.name for field in Notification._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(BookingMessage)
class BookingMessageAdmin(admin.ModelAdmin):
    list_display = ("id", "booking", "sender", "created_at")
    search_fields = ("sender__email", "content")
    readonly_fields = tuple(field.name for field in BookingMessage._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(SafetyReport)
class SafetyReportAdmin(admin.ModelAdmin):
    list_display = ("id", "category", "priority", "status", "reporter", "reported_user", "created_at")
    list_filter = ("status", "priority", "category", "created_at")
    search_fields = ("reporter__email", "reported_user__email", "description")
    readonly_fields = tuple(
        field.name for field in SafetyReport._meta.fields
        if field.name not in ("status", "admin_note", "assigned_to", "resolved_at")
    )

    def has_add_permission(self, request):
        return False


@admin.register(JourneyReview)
class JourneyReviewAdmin(admin.ModelAdmin):
    list_display = ("id", "booking", "reviewer", "reviewee", "rating", "created_at")
    list_filter = ("rating", "created_at")
    search_fields = ("reviewer__email", "reviewee__email", "comment")
    readonly_fields = tuple(field.name for field in JourneyReview._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
