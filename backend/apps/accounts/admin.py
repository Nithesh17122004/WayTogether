from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User, VerificationCode


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ("email",)
    list_display = (
        "email", "phone", "role", "is_email_verified",
        "is_phone_verified", "is_active", "is_staff",
    )
    list_filter = ("role", "is_email_verified", "is_phone_verified", "is_active", "is_staff")
    search_fields = ("email", "phone", "first_name", "last_name")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal information", {"fields": ("first_name", "last_name", "phone", "role")}),
        ("Verification", {"fields": ("is_email_verified", "is_phone_verified", "terms_accepted_at")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "phone", "first_name", "last_name", "role", "password1", "password2"),
        }),
    )


@admin.register(VerificationCode)
class VerificationCodeAdmin(admin.ModelAdmin):
    list_display = ("user", "channel", "created_at", "expires_at", "attempts", "verified_at")
    list_filter = ("channel", "verified_at")
    search_fields = ("user__email", "user__phone")
    readonly_fields = ("user", "channel", "code_hash", "created_at", "expires_at", "attempts", "verified_at")
    def has_add_permission(self, request):
        return False
    def has_change_permission(self, request, obj=None):
        return False
