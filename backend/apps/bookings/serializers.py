from rest_framework import serializers

from .models import Booking


class BookingRequestSerializer(serializers.Serializer):
    journey = serializers.IntegerField(min_value=1)
    seats_requested = serializers.IntegerField(min_value=1, max_value=8)
    request_message = serializers.CharField(max_length=500, required=False, allow_blank=True, default="")


class BookingSerializer(serializers.ModelSerializer):
    journey_id = serializers.IntegerField(source="journey.id", read_only=True)
    journey_origin = serializers.CharField(source="journey.origin_name", read_only=True)
    journey_destination = serializers.CharField(source="journey.destination_name", read_only=True)
    travel_date = serializers.DateField(source="journey.travel_date", read_only=True)
    departure_time = serializers.TimeField(source="journey.departure_time", read_only=True)
    driver_name = serializers.CharField(source="journey.driver.display_name", read_only=True)
    passenger_name = serializers.CharField(source="passenger.display_name", read_only=True)
    vehicle_name = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = (
            "id", "journey_id", "journey_origin", "journey_destination",
            "travel_date", "departure_time", "driver_name", "passenger_name",
            "vehicle_name", "seats_requested", "request_message", "driver_response",
            "status", "estimated_contribution_per_passenger",
            "estimated_contribution_total", "requested_at", "updated_at",
            "responded_at", "cancelled_at",
        )
        read_only_fields = fields

    def get_vehicle_name(self, obj):
        vehicle = obj.journey.vehicle
        return f"{vehicle.make} {vehicle.model} · {vehicle.registration_number}"
