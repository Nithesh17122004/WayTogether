from rest_framework import serializers

from .models import BookingMessage, EmergencyContact, JourneyReview, Notification, SafetyReport


class NotificationSerializer(serializers.ModelSerializer):
    actor_name = serializers.CharField(source="actor.display_name", read_only=True, allow_null=True)
    booking_id = serializers.IntegerField(read_only=True)
    journey_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = Notification
        fields = (
            "id", "event_type", "title", "body", "actor_name",
            "booking_id", "journey_id", "read_at", "created_at",
        )
        read_only_fields = fields


class BookingMessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source="sender.display_name", read_only=True)
    is_mine = serializers.SerializerMethodField()

    class Meta:
        model = BookingMessage
        fields = ("id", "booking_id", "sender_name", "is_mine", "content", "created_at")
        read_only_fields = ("id", "booking_id", "sender_name", "is_mine", "created_at")

    def get_is_mine(self, obj):
        request = self.context.get("request")
        return bool(request and request.user.is_authenticated and obj.sender_id == request.user.id)


class BookingMessageInputSerializer(serializers.Serializer):
    content = serializers.CharField(max_length=1500, trim_whitespace=True)


class EmergencyContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmergencyContact
        fields = ("id", "contact_name", "phone", "relationship", "is_primary", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")

    def validate_phone(self, value):
        user = self.context["request"].user
        qs = EmergencyContact.objects.filter(user=user, phone=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("This phone number is already saved as an emergency contact.")
        return value


class SafetyReportInputSerializer(serializers.Serializer):
    booking_id = serializers.IntegerField(min_value=1, required=False)
    journey_id = serializers.IntegerField(min_value=1, required=False)
    reported_user_id = serializers.IntegerField(min_value=1, required=False)
    category = serializers.ChoiceField(choices=SafetyReport.Category.choices)
    priority = serializers.ChoiceField(choices=SafetyReport.Priority.choices, default=SafetyReport.Priority.NORMAL)
    description = serializers.CharField(max_length=5000, trim_whitespace=True)


class SafetyReportSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(source="get_category_display", read_only=True)
    reported_user_name = serializers.CharField(source="reported_user.display_name", read_only=True, allow_null=True)

    class Meta:
        model = SafetyReport
        fields = (
            "id", "booking_id", "journey_id", "category", "category_display",
            "priority", "description", "status", "admin_note",
            "reported_user_name", "created_at", "updated_at", "resolved_at",
        )
        read_only_fields = fields


class JourneyReviewInputSerializer(serializers.Serializer):
    rating = serializers.IntegerField(min_value=1, max_value=5)
    comment = serializers.CharField(max_length=1000, required=False, allow_blank=True, default="")


class JourneyReviewSerializer(serializers.ModelSerializer):
    reviewer_name = serializers.CharField(source="reviewer.display_name", read_only=True)
    reviewee_name = serializers.CharField(source="reviewee.display_name", read_only=True)

    class Meta:
        model = JourneyReview
        fields = ("id", "booking_id", "reviewer_name", "reviewee_name", "rating", "comment", "created_at")
        read_only_fields = fields
