from django.db import IntegrityError, transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.bookings.models import Booking
from apps.journeys.models import Journey

from .models import (
    BookingMessage,
    EmergencyContact,
    JourneyReview,
    Notification,
    SafetyReport,
)
from .serializers import (
    AdminSafetyReportSerializer,
    BookingMessageInputSerializer,
    BookingMessageSerializer,
    EmergencyContactSerializer,
    JourneyReviewInputSerializer,
    JourneyReviewSerializer,
    NotificationSerializer,
    PublicSafetyReportSerializer,
)
from .services import mark_notification_read, notify, notify_booking_participants


def _is_booking_participant(booking, user):
    return booking.passenger_id == user.id or booking.journey.driver_id == user.id


class NotificationInboxView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = Notification.objects.filter(recipient=request.user).select_related("actor", "booking", "journey")
        unread_count = queryset.filter(read_at__isnull=True).count()
        items = queryset[:100]
        return Response({
            "unread_count": unread_count,
            "results": NotificationSerializer(items, many=True).data,
        })


class NotificationReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        notification = get_object_or_404(Notification, pk=pk, recipient=request.user)
        mark_notification_read(notification)
        return Response({"detail": "Notification marked as read.", "notification": NotificationSerializer(notification).data})


class NotificationReadAllView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        updated = Notification.objects.filter(
            recipient=request.user,
            read_at__isnull=True,
        ).update(read_at=timezone.now())
        return Response({"detail": "Unread notifications marked as read.", "updated_count": updated})


class BookingMessageThreadView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_scope = "message_send"

    def get(self, request, booking_id):
        booking = get_object_or_404(
            Booking.objects.select_related("journey", "journey__driver", "passenger"),
            pk=booking_id,
        )
        if not _is_booking_participant(booking, request.user):
            return Response({"detail": "Message thread not found."}, status=status.HTTP_404_NOT_FOUND)
        messages = BookingMessage.objects.filter(booking=booking).select_related("sender")
        return Response({
            "booking_id": booking.pk,
            "can_send": booking.status in (Booking.Status.PENDING, Booking.Status.CONFIRMED)
                and booking.journey.status == Journey.Status.PUBLISHED,
            "results": BookingMessageSerializer(
                messages[:250], many=True, context={"request": request}
            ).data,
        })

    def post(self, request, booking_id):
        serializer = BookingMessageInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        content = serializer.validated_data["content"]
        with transaction.atomic():
            booking = get_object_or_404(
                Booking.objects.select_for_update().select_related(
                    "journey", "journey__driver", "passenger"
                ),
                pk=booking_id,
            )
            if not _is_booking_participant(booking, request.user):
                return Response({"detail": "Message thread not found."}, status=status.HTTP_404_NOT_FOUND)
            if booking.status not in (Booking.Status.PENDING, Booking.Status.CONFIRMED):
                return Response({"detail": "Messages are closed for this booking."}, status=status.HTTP_409_CONFLICT)
            if booking.journey.status != Journey.Status.PUBLISHED:
                return Response({"detail": "Messages are closed because this journey is no longer active."}, status=status.HTTP_409_CONFLICT)

            message = BookingMessage.objects.create(
                booking=booking,
                sender=request.user,
                content=content,
            )
            notify_booking_participants(
                booking=booking,
                event_type=Notification.EventType.NEW_MESSAGE,
                title="New booking message",
                body=f"{request.user.display_name} sent you a message about your shared journey.",
                actor=request.user,
            )
        return Response({
            "detail": "Message sent.",
            "message": BookingMessageSerializer(message, context={"request": request}).data,
        }, status=status.HTTP_201_CREATED)


class EmergencyContactListCreateView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_scope = "safety_action"

    def get(self, request):
        contacts = EmergencyContact.objects.filter(user=request.user)
        return Response(EmergencyContactSerializer(contacts, many=True).data)

    def post(self, request):
        with transaction.atomic():
            # Lock the owner row so simultaneous create requests cannot exceed the limit.
            from apps.accounts.models import User
            User.objects.select_for_update().get(pk=request.user.pk)
            contacts = EmergencyContact.objects.filter(user=request.user)
            if contacts.count() >= 3:
                return Response(
                    {"detail": "You can save up to three emergency contacts."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            serializer = EmergencyContactSerializer(data=request.data, context={"request": request})
            serializer.is_valid(raise_exception=True)
            make_primary = serializer.validated_data.get("is_primary", False) or not contacts.exists()
            if make_primary:
                contacts.update(is_primary=False)
            contact = serializer.save(user=request.user, is_primary=make_primary)
        return Response(EmergencyContactSerializer(contact).data, status=status.HTTP_201_CREATED)


class EmergencyContactDetailView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_scope = "safety_action"

    def patch(self, request, pk):
        contact = get_object_or_404(EmergencyContact, pk=pk, user=request.user)
        serializer = EmergencyContactSerializer(
            contact,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        make_primary = serializer.validated_data.get("is_primary", contact.is_primary)
        with transaction.atomic():
            if make_primary:
                EmergencyContact.objects.filter(user=request.user).exclude(pk=contact.pk).update(is_primary=False)
            updated = serializer.save(is_primary=make_primary)
        return Response(EmergencyContactSerializer(updated).data)

    def delete(self, request, pk):
        contact = get_object_or_404(EmergencyContact, pk=pk, user=request.user)
        was_primary = contact.is_primary
        contact.delete()
        if was_primary:
            next_contact = EmergencyContact.objects.filter(user=request.user).first()
            if next_contact:
                next_contact.is_primary = True
                next_contact.save(update_fields=("is_primary", "updated_at"))
        return Response(status=status.HTTP_204_NO_CONTENT)


class SafetyReportCreateView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_scope = "safety_action"

    def post(self, request):
        serializer = SafetyReportInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        booking_id = data.get("booking_id")
        journey_id = data.get("journey_id")
        reported_user_id = data.get("reported_user_id")

        if not booking_id and not journey_id:
            return Response({"detail": "Provide a booking_id or journey_id so the report can be reviewed."}, status=400)

        booking = None
        journey = None
        participants = set()
        if booking_id:
            booking = get_object_or_404(
                Booking.objects.select_related("journey", "journey__driver", "passenger"),
                pk=booking_id,
            )
            journey = booking.journey
            participants = {booking.passenger_id, journey.driver_id}
            if request.user.id not in participants:
                return Response({"detail": "You can report only a booking you participated in."}, status=404)
            if journey_id and journey_id != journey.pk:
                return Response({"detail": "The booking and journey identifiers do not match."}, status=400)
        else:
            journey = get_object_or_404(
                Journey.objects.select_related("driver"),
                pk=journey_id,
            )
            if request.user.id != journey.driver_id:
                booking_match = Booking.objects.filter(
                    journey=journey,
                    passenger=request.user,
                ).first()
                if not booking_match:
                    return Response({"detail": "You can report only a journey you participated in."}, status=404)
                booking = booking_match
            participants = {journey.driver_id}
            if booking:
                participants.add(booking.passenger_id)

        reported_user = None
        if reported_user_id:
            if reported_user_id not in participants or reported_user_id == request.user.id:
                return Response({"detail": "The reported user must be the other participant in this journey."}, status=400)
            from apps.accounts.models import User
            reported_user = get_object_or_404(User, pk=reported_user_id)
        elif booking:
            reported_user_id = journey.driver_id if request.user.id == booking.passenger_id else booking.passenger_id
            from apps.accounts.models import User
            reported_user = User.objects.filter(pk=reported_user_id).first()

        report = SafetyReport.objects.create(
            reporter=request.user,
            reported_user=reported_user,
            journey=journey,
            booking=booking,
            category=data["category"],
            priority=data["priority"],
            description=data["description"],
        )
        return Response({
            "detail": "Your report has been submitted privately to the safety team.",
            "report": PublicSafetyReportSerializer(report).data,
        }, status=status.HTTP_201_CREATED)


class MySafetyReportsView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PublicSafetyReportSerializer

    def get_queryset(self):
        return SafetyReport.objects.filter(reporter=self.request.user).select_related("journey", "booking")


class AdminSafetyReportQueueView(generics.ListAPIView):
    permission_classes = [IsAdminUser]
    serializer_class = AdminSafetyReportSerializer
    queryset = SafetyReport.objects.select_related("reporter", "reported_user", "journey", "booking").all()

    def get_queryset(self):
        queryset = super().get_queryset()
        report_status = self.request.query_params.get("status")
        priority = self.request.query_params.get("priority")
        if report_status in {choice[0] for choice in SafetyReport.Status.choices}:
            queryset = queryset.filter(status=report_status)
        if priority in {choice[0] for choice in SafetyReport.Priority.choices}:
            queryset = queryset.filter(priority=priority)
        return queryset


class AdminSafetyReportUpdateView(APIView):
    permission_classes = [IsAdminUser]
    throttle_scope = "safety_action"

    def patch(self, request, pk):
        report = get_object_or_404(SafetyReport, pk=pk)
        new_status = request.data.get("status", report.status)
        admin_note = str(request.data.get("admin_note", report.admin_note)).strip()[:1000]
        allowed = {choice[0] for choice in SafetyReport.Status.choices}
        if new_status not in allowed:
            return Response({"detail": "Choose a valid report status."}, status=400)
        report.status = new_status
        report.admin_note = admin_note
        report.assigned_to = request.user
        if new_status in (SafetyReport.Status.RESOLVED, SafetyReport.Status.CLOSED):
            report.resolved_at = timezone.now()
        else:
            report.resolved_at = None
        report.save(update_fields=("status", "admin_note", "assigned_to", "resolved_at", "updated_at"))
        notify(
            recipient=report.reporter,
            event_type=Notification.EventType.SAFETY_UPDATE,
            title="Safety report updated",
            body=f"Your report #{report.pk} is now marked {report.get_status_display().lower()}.",
            actor=request.user,
            booking=report.booking,
            journey=report.journey,
        )
        return Response({
            "detail": "Safety report updated.",
            "report": AdminSafetyReportSerializer(report).data,
        })


class SubmitJourneyReviewView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_scope = "safety_action"

    def post(self, request, booking_id):
        serializer = JourneyReviewInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        booking = get_object_or_404(
            Booking.objects.select_related("journey", "journey__driver", "passenger"),
            pk=booking_id,
        )
        if booking.status != Booking.Status.CONFIRMED or booking.journey.status != Journey.Status.COMPLETED:
            return Response({"detail": "Reviews are available only after a confirmed booking is completed."}, status=409)
        if request.user.id == booking.passenger_id:
            reviewee = booking.journey.driver
        elif request.user.id == booking.journey.driver_id:
            reviewee = booking.passenger
        else:
            return Response({"detail": "You can review only the other participant in your booking."}, status=404)

        try:
            review = JourneyReview.objects.create(
                booking=booking,
                reviewer=request.user,
                reviewee=reviewee,
                rating=serializer.validated_data["rating"],
                comment=serializer.validated_data["comment"],
            )
        except IntegrityError:
            return Response({"detail": "You have already submitted a review for this booking."}, status=409)

        return Response({
            "detail": "Your journey review has been submitted.",
            "review": JourneyReviewSerializer(review).data,
        }, status=status.HTTP_201_CREATED)


class MyJourneyReviewsView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = JourneyReviewSerializer

    def get_queryset(self):
        received = self.request.query_params.get("type") == "received"
        field = "reviewee" if received else "reviewer"
        return JourneyReview.objects.filter(**{field: self.request.user}).select_related(
            "booking", "reviewer", "reviewee"
        )
