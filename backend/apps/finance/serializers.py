from rest_framework import serializers

from .models import ExpenseSettlement, PassengerContribution, SandboxPayment, SandboxRefund


class ExpenseSettlementInputSerializer(serializers.Serializer):
    actual_fuel_expense = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0, required=False, default=0)
    actual_toll_expense = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0, required=False, default=0)
    actual_parking_expense = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0, required=False, default=0)
    actual_other_expense = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0, required=False, default=0)
    actual_expense_note = serializers.CharField(max_length=1000, required=False, allow_blank=True, default="")


class ExpenseSettlementSerializer(serializers.ModelSerializer):
    journey_id = serializers.IntegerField(read_only=True)
    origin_name = serializers.CharField(source="journey.origin_name", read_only=True)
    destination_name = serializers.CharField(source="journey.destination_name", read_only=True)
    travel_date = serializers.DateField(source="journey.travel_date", read_only=True)
    driver_name = serializers.CharField(source="driver.display_name", read_only=True)

    class Meta:
        model = ExpenseSettlement
        fields = (
            "id", "journey_id", "origin_name", "destination_name", "travel_date",
            "driver_name", "actual_fuel_expense", "actual_toll_expense",
            "actual_parking_expense", "actual_other_expense", "actual_expense_note",
            "eligible_total", "driver_share", "passenger_seat_count", "currency",
            "is_finalized", "submitted_at", "finalized_at",
        )
        read_only_fields = fields


class SandboxPaymentSerializer(serializers.ModelSerializer):
    reference = serializers.UUIDField(read_only=True)
    contribution_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = SandboxPayment
        fields = ("id", "reference", "contribution_id", "provider", "status", "amount", "currency", "failure_note", "created_at", "completed_at")
        read_only_fields = fields


class SandboxRefundSerializer(serializers.ModelSerializer):
    reference = serializers.UUIDField(read_only=True)

    class Meta:
        model = SandboxRefund
        fields = ("id", "reference", "amount", "currency", "reason", "processed_at")
        read_only_fields = fields


class PassengerContributionSerializer(serializers.ModelSerializer):
    journey_id = serializers.IntegerField(source="booking.journey_id", read_only=True)
    origin_name = serializers.CharField(source="booking.journey.origin_name", read_only=True)
    destination_name = serializers.CharField(source="booking.journey.destination_name", read_only=True)
    travel_date = serializers.DateField(source="booking.journey.travel_date", read_only=True)
    driver_name = serializers.CharField(source="booking.journey.driver.display_name", read_only=True)
    latest_payment = serializers.SerializerMethodField()
    settlement_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = PassengerContribution
        fields = (
            "id", "booking_id", "journey_id", "origin_name", "destination_name",
            "travel_date", "driver_name", "seat_count", "per_seat_amount",
            "total_amount", "currency", "settlement_id", "created_at", "latest_payment",
        )
        read_only_fields = fields

    def get_latest_payment(self, obj):
        payment = obj.sandbox_payments.order_by("-created_at").first()
        return SandboxPaymentSerializer(payment).data if payment else None
