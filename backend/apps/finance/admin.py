from django.contrib import admin

from .models import ExpenseSettlement, PassengerContribution, RazorpayPayment, SandboxPayment, SandboxRefund


@admin.register(ExpenseSettlement)
class ExpenseSettlementAdmin(admin.ModelAdmin):
    list_display = ("id", "journey", "driver", "eligible_total", "driver_share", "is_finalized", "finalized_at")
    list_filter = ("is_finalized", "currency")
    search_fields = ("journey__origin_name", "journey__destination_name", "driver__email")
    readonly_fields = (
        "journey", "driver", "actual_fuel_expense", "actual_toll_expense",
        "actual_parking_expense", "actual_other_expense", "actual_expense_note",
        "eligible_total", "driver_share", "passenger_seat_count", "currency",
        "is_finalized", "submitted_at", "finalized_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(PassengerContribution)
class PassengerContributionAdmin(admin.ModelAdmin):
    list_display = ("id", "booking", "passenger", "seat_count", "total_amount", "currency", "created_at")
    list_filter = ("currency", "created_at")
    search_fields = ("passenger__email", "booking__journey__origin_name", "booking__journey__destination_name")
    readonly_fields = tuple(field.name for field in PassengerContribution._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(SandboxPayment)
class SandboxPaymentAdmin(admin.ModelAdmin):
    list_display = ("id", "reference", "contribution", "amount", "currency", "status", "created_at")
    list_filter = ("status", "currency", "created_at")
    search_fields = ("reference", "contribution__passenger__email")
    readonly_fields = tuple(field.name for field in SandboxPayment._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(SandboxRefund)
class SandboxRefundAdmin(admin.ModelAdmin):
    list_display = ("id", "reference", "payment", "amount", "currency", "processed_by", "processed_at")
    list_filter = ("currency", "processed_at")
    search_fields = ("reference", "payment__reference", "processed_by__email")
    readonly_fields = tuple(field.name for field in SandboxRefund._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(RazorpayPayment)
class RazorpayPaymentAdmin(admin.ModelAdmin):
    list_display = (
        "id", "order_id", "payment_id", "contribution", "amount",
        "currency", "status", "test_mode", "created_at",
    )
    list_filter = ("status", "test_mode", "currency", "created_at")
    search_fields = ("order_id", "payment_id", "contribution__passenger__email")
    readonly_fields = tuple(field.name for field in RazorpayPayment._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
