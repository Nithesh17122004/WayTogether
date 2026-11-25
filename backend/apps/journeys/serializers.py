from decimal import Decimal

from django.utils import timezone
from rest_framework import serializers

from apps.drivers.models import Vehicle
from .models import Journey, JourneyStop


class JourneyStopSerializer(serializers.ModelSerializer):
    class Meta:
        model = JourneyStop
        fields = ("id", "sequence", "location_name", "latitude", "longitude")
        read_only_fields = ("id", "sequence")

    def validate(self, attrs):
        latitude = attrs.get("latitude")
        longitude = attrs.get("longitude")
        if latitude is not None and not Decimal("-90") <= latitude <= Decimal("90"):
            raise serializers.ValidationError({"latitude": "Latitude must be between -90 and 90."})
        if longitude is not None and not Decimal("-180") <= longitude <= Decimal("180"):
            raise serializers.ValidationError({"longitude": "Longitude must be between -180 and 180."})
        return attrs


class JourneySerializer(serializers.ModelSerializer):
    vehicle = serializers.PrimaryKeyRelatedField(queryset=Vehicle.objects.all(), write_only=True)
    vehicle_details = serializers.SerializerMethodField()
    driver_name = serializers.CharField(source="driver.display_name", read_only=True)
    driver_verification_status = serializers.SerializerMethodField()
    stops = JourneyStopSerializer(many=True, required=False)
    estimated_total_expenses = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True
    )
    estimated_contribution_per_passenger = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True
    )
    origin_match_distance_km = serializers.SerializerMethodField()
    destination_match_distance_km = serializers.SerializerMethodField()
    matched_origin_name = serializers.SerializerMethodField()
    matched_destination_name = serializers.SerializerMethodField()
    confirmed_seats = serializers.SerializerMethodField()
    available_seats = serializers.SerializerMethodField()

    class Meta:
        model = Journey
        fields = (
            "id", "driver_name", "driver_verification_status", "vehicle", "vehicle_details",
            "origin_name", "origin_latitude", "origin_longitude",
            "destination_name", "destination_latitude", "destination_longitude",
            "travel_date", "departure_time", "seats_offered",
            "fuel_expense", "toll_expense", "parking_expense", "other_expense",
            "estimated_total_expenses", "estimated_contribution_per_passenger",
            "expense_note", "description", "route_distance_km",
            "route_duration_minutes", "route_geometry", "stops",
            "independently_planned", "expenses_only", "status", "published_at",
            "created_at", "updated_at", "origin_match_distance_km",
            "destination_match_distance_km", "matched_origin_name", "matched_destination_name",
            "confirmed_seats", "available_seats",
        )
        read_only_fields = (
            "id", "driver_name", "driver_verification_status", "vehicle_details",
            "estimated_total_expenses", "estimated_contribution_per_passenger",
            "status", "published_at", "created_at", "updated_at",
            "origin_match_distance_km", "destination_match_distance_km",
        )

    def get_driver_verification_status(self, obj):
        profile = getattr(obj.driver, "driver_profile", None)
        return profile.verification_status if profile else None

    def get_vehicle_details(self, obj):
        return {
            "registration_number": obj.vehicle.registration_number,
            "make": obj.vehicle.make,
            "model": obj.vehicle.model,
            "vehicle_type": obj.vehicle.vehicle_type,
            "passenger_seats": obj.vehicle.passenger_seats,
        }

    def get_origin_match_distance_km(self, obj):
        return getattr(obj, "_origin_match_distance_km", None)

    def get_destination_match_distance_km(self, obj):
        return getattr(obj, "_destination_match_distance_km", None)

    def get_matched_origin_name(self, obj):
        return getattr(obj, "_matched_origin_name", None)

    def get_matched_destination_name(self, obj):
        return getattr(obj, "_matched_destination_name", None)

    def get_confirmed_seats(self, obj):
        if hasattr(obj, "_confirmed_bookings"):
            return sum(item.seats_requested for item in obj._confirmed_bookings)
        from apps.bookings.services import confirmed_seat_count
        return confirmed_seat_count(obj)

    def get_available_seats(self, obj):
        return max(0, obj.seats_offered - self.get_confirmed_seats(obj))

    def validate(self, attrs):
        stops = attrs.get("stops")
        if stops is not None and len(stops) > 4:
            raise serializers.ValidationError({"stops": "A journey can have up to four intermediate stops."})

        instance = self.instance
        travel_date = attrs.get("travel_date", getattr(instance, "travel_date", None))
        departure_time = attrs.get("departure_time", getattr(instance, "departure_time", None))
        if travel_date and travel_date < timezone.localdate():
            raise serializers.ValidationError({"travel_date": "Travel date cannot be in the past."})
        if (
            travel_date == timezone.localdate()
            and departure_time is not None
            and departure_time <= timezone.localtime().time().replace(tzinfo=None)
        ):
            raise serializers.ValidationError({"departure_time": "Departure time must be in the future."})

        vehicle = attrs.get("vehicle", getattr(instance, "vehicle", None))
        seats = attrs.get("seats_offered", getattr(instance, "seats_offered", None))
        if vehicle and seats and seats > vehicle.passenger_seats:
            raise serializers.ValidationError({
                "seats_offered": "Passenger seats cannot exceed the vehicle's registered passenger capacity."
            })

        for field in ("origin_latitude", "destination_latitude"):
            value = attrs.get(field, getattr(instance, field, None))
            if value is not None and not Decimal("-90") <= value <= Decimal("90"):
                raise serializers.ValidationError({field: "Latitude must be between -90 and 90."})
        for field in ("origin_longitude", "destination_longitude"):
            value = attrs.get(field, getattr(instance, field, None))
            if value is not None and not Decimal("-180") <= value <= Decimal("180"):
                raise serializers.ValidationError({field: "Longitude must be between -180 and 180."})

        for field in ("fuel_expense", "toll_expense", "parking_expense", "other_expense"):
            value = attrs.get(field, getattr(instance, field, Decimal("0.00")))
            if value < 0:
                raise serializers.ValidationError({field: "Expenses cannot be negative."})

        independently_planned = attrs.get(
            "independently_planned",
            getattr(instance, "independently_planned", False),
        )
        expenses_only = attrs.get("expenses_only", getattr(instance, "expenses_only", False))
        if not independently_planned:
            raise serializers.ValidationError({
                "independently_planned": "Confirm that you would make this journey even without passengers."
            })
        if not expenses_only:
            raise serializers.ValidationError({
                "expenses_only": "Passenger contributions must be limited to eligible shared journey expenses."
            })

        geometry = attrs.get("route_geometry", getattr(instance, "route_geometry", []))
        if geometry and (
            not isinstance(geometry, list)
            or len(geometry) > 10000
            or any(
                not isinstance(point, list)
                or len(point) != 2
                or not all(isinstance(value, (int, float)) for value in point)
                or not -180 <= point[0] <= 180
                or not -90 <= point[1] <= 90
                for point in geometry
            )
        ):
            raise serializers.ValidationError({
                "route_geometry": "Route geometry must contain valid [longitude, latitude] coordinates."
            })
        return attrs

    def create(self, validated_data):
        stops_data = validated_data.pop("stops", [])
        vehicle = validated_data["vehicle"]
        request = self.context["request"]
        if vehicle.owner_id != request.user.id:
            raise serializers.ValidationError({"vehicle": "You can only publish a journey using your own vehicle."})
        journey = Journey.objects.create(driver=request.user, **validated_data)
        self._save_stops(journey, stops_data)
        return journey

    def update(self, instance, validated_data):
        if instance.status != Journey.Status.DRAFT:
            raise serializers.ValidationError("Only draft journeys can be edited.")
        stops_data = validated_data.pop("stops", None)
        vehicle = validated_data.get("vehicle", instance.vehicle)
        if vehicle.owner_id != instance.driver_id:
            raise serializers.ValidationError({"vehicle": "You can only use your own vehicle."})
        journey = super().update(instance, validated_data)
        if stops_data is not None:
            journey.stops.all().delete()
            self._save_stops(journey, stops_data)
        return journey

    @staticmethod
    def _save_stops(journey, stops_data):
        for index, stop in enumerate(stops_data, start=1):
            JourneyStop.objects.create(journey=journey, sequence=index, **stop)
