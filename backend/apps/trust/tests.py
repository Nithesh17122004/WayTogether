from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.bookings.models import Booking
from apps.drivers.models import Vehicle
from apps.journeys.models import Journey

from .models import BookingMessage, EmergencyContact, JourneyReview, Notification, SafetyReport

User = get_user_model()


class TrustApiTests(APITestCase):
    def create_user(self, email, phone, role, *, is_staff=False):
        return User.objects.create_user(
            email=email,
            phone=phone,
            password="A-Strong-Unique-Password-928!",
            first_name=email.split("@")[0].title(),
            role=role,
            is_email_verified=True,
            is_phone_verified=True,
            is_staff=is_staff,
        )

    def setUp(self):
        cache.clear()
        self.driver = self.create_user(
            "trust-driver@example.com", "+919876541001", User.Role.DRIVER
        )
        self.passenger = self.create_user(
            "trust-passenger@example.com", "+919876541002", User.Role.PASSENGER
        )
        self.other = self.create_user(
            "trust-other@example.com", "+919876541003", User.Role.PASSENGER
        )
        self.vehicle = Vehicle.objects.create(
            owner=self.driver,
            registration_number="TN30AB1234",
            make="Honda",
            model="City",
            manufacture_year=2022,
            vehicle_type=Vehicle.VehicleType.SEDAN,
            passenger_seats=3,
            private_use_attested=True,
            verification_status=Vehicle.VerificationStatus.APPROVED,
        )
        self.journey = Journey.objects.create(
            driver=self.driver,
            vehicle=self.vehicle,
            origin_name="Chennai, Tamil Nadu",
            origin_latitude=Decimal("13.0827000"),
            origin_longitude=Decimal("80.2707000"),
            destination_name="Bengaluru, Karnataka",
            destination_latitude=Decimal("12.9716000"),
            destination_longitude=Decimal("77.5946000"),
            travel_date=timezone.localdate() + timedelta(days=3),
            departure_time="08:00",
            seats_offered=3,
            fuel_expense=Decimal("900.00"),
            independently_planned=True,
            expenses_only=True,
            status=Journey.Status.PUBLISHED,
            published_at=timezone.now(),
        )
        self.booking = Booking.objects.create(
            journey=self.journey,
            passenger=self.passenger,
            seats_requested=1,
            status=Booking.Status.PENDING,
        )

    def test_booking_participants_can_send_and_read_private_messages(self):
        self.client.force_authenticate(self.passenger)
        sent = self.client.post(
            f"/api/v1/trust/bookings/{self.booking.pk}/messages/",
            {"content": "I will meet at the agreed pickup location."},
            format="json",
        )
        self.assertEqual(sent.status_code, status.HTTP_201_CREATED)
        self.assertTrue(sent.data["message"]["is_mine"])
        self.assertEqual(BookingMessage.objects.filter(booking=self.booking).count(), 1)

        notification = Notification.objects.get(recipient=self.driver)
        self.assertEqual(notification.event_type, Notification.EventType.NEW_MESSAGE)

        self.client.force_authenticate(self.driver)
        thread = self.client.get(f"/api/v1/trust/bookings/{self.booking.pk}/messages/")
        self.assertEqual(thread.status_code, status.HTTP_200_OK)
        self.assertTrue(thread.data["can_send"])
        self.assertEqual(len(thread.data["results"]), 1)
        self.assertFalse(thread.data["results"][0]["is_mine"])

    def test_unrelated_user_cannot_read_or_send_booking_messages(self):
        self.client.force_authenticate(self.other)
        url = f"/api/v1/trust/bookings/{self.booking.pk}/messages/"
        self.assertEqual(self.client.get(url).status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(
            self.client.post(url, {"content": "Hello"}, format="json").status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_messages_are_readable_but_closed_after_booking_cancellation(self):
        BookingMessage.objects.create(
            booking=self.booking,
            sender=self.driver,
            content="Earlier message",
        )
        self.booking.status = Booking.Status.CANCELLED
        self.booking.save(update_fields=["status"])

        self.client.force_authenticate(self.passenger)
        url = f"/api/v1/trust/bookings/{self.booking.pk}/messages/"
        read = self.client.get(url)
        self.assertEqual(read.status_code, status.HTTP_200_OK)
        self.assertFalse(read.data["can_send"])
        sent = self.client.post(url, {"content": "A late message"}, format="json")
        self.assertEqual(sent.status_code, status.HTTP_409_CONFLICT)

    def test_notifications_are_private_and_can_be_marked_read(self):
        notification = Notification.objects.create(
            recipient=self.passenger,
            actor=self.driver,
            event_type=Notification.EventType.BOOKING_CONFIRMED,
            title="Booking confirmed",
            body="Your seats are reserved.",
            booking=self.booking,
            journey=self.journey,
        )
        other_notification = Notification.objects.create(
            recipient=self.other,
            event_type=Notification.EventType.BOOKING_REQUEST,
            title="Other notification",
            body="Private.",
        )
        self.client.force_authenticate(self.passenger)
        inbox = self.client.get("/api/v1/trust/notifications/")
        self.assertEqual(inbox.status_code, status.HTTP_200_OK)
        self.assertEqual(inbox.data["unread_count"], 1)
        self.assertEqual(len(inbox.data["results"]), 1)

        hidden = self.client.post(
            f"/api/v1/trust/notifications/{other_notification.pk}/read/",
            {},
            format="json",
        )
        self.assertEqual(hidden.status_code, status.HTTP_404_NOT_FOUND)
        read = self.client.post(
            f"/api/v1/trust/notifications/{notification.pk}/read/",
            {},
            format="json",
        )
        self.assertEqual(read.status_code, status.HTTP_200_OK)
        notification.refresh_from_db()
        self.assertIsNotNone(notification.read_at)

    def test_read_all_notifications_marks_only_current_users_records(self):
        one = Notification.objects.create(
            recipient=self.passenger,
            event_type=Notification.EventType.BOOKING_REQUEST,
            title="One",
            body="One",
        )
        two = Notification.objects.create(
            recipient=self.passenger,
            event_type=Notification.EventType.BOOKING_DECLINED,
            title="Two",
            body="Two",
        )
        other_notification = Notification.objects.create(
            recipient=self.other,
            event_type=Notification.EventType.BOOKING_REQUEST,
            title="Other",
            body="Other",
        )
        self.client.force_authenticate(self.passenger)
        response = self.client.post("/api/v1/trust/notifications/read-all/", {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["updated_count"], 2)
        self.assertIsNotNone(Notification.objects.get(pk=one.pk).read_at)
        self.assertIsNotNone(Notification.objects.get(pk=two.pk).read_at)
        self.assertIsNone(Notification.objects.get(pk=other_notification.pk).read_at)

    def test_user_can_manage_up_to_three_private_emergency_contacts(self):
        self.client.force_authenticate(self.passenger)
        contacts = [
            ("Parent", "+919876541101"),
            ("Sibling", "+919876541102"),
            ("Friend", "+919876541103"),
        ]
        created = []
        for name, phone in contacts:
            response = self.client.post(
                "/api/v1/trust/safety/contacts/",
                {"contact_name": name, "phone": phone, "relationship": "Family"},
                format="json",
            )
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            created.append(response.data["id"])
        fourth = self.client.post(
            "/api/v1/trust/safety/contacts/",
            {"contact_name": "Fourth", "phone": "+919876541104"},
            format="json",
        )
        self.assertEqual(fourth.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(EmergencyContact.objects.filter(user=self.passenger).count(), 3)
        self.assertEqual(EmergencyContact.objects.filter(user=self.passenger, is_primary=True).count(), 1)

        self.client.force_authenticate(self.other)
        self.assertEqual(len(self.client.get("/api/v1/trust/safety/contacts/").data), 0)
        hidden = self.client.delete(
            f"/api/v1/trust/safety/contacts/{created[0]}/",
        )
        self.assertEqual(hidden.status_code, status.HTTP_404_NOT_FOUND)

    def test_emergency_contacts_can_be_updated_and_deleted_by_owner(self):
        contact = EmergencyContact.objects.create(
            user=self.passenger,
            contact_name="Parent",
            phone="+919876541111",
            is_primary=True,
        )
        self.client.force_authenticate(self.passenger)
        updated = self.client.patch(
            f"/api/v1/trust/safety/contacts/{contact.pk}/",
            {"contact_name": "Updated parent"},
            format="json",
        )
        self.assertEqual(updated.status_code, status.HTTP_200_OK)
        self.assertEqual(updated.data["contact_name"], "Updated parent")
        deleted = self.client.delete(f"/api/v1/trust/safety/contacts/{contact.pk}/")
        self.assertEqual(deleted.status_code, status.HTTP_204_NO_CONTENT)

    def test_booking_participant_can_submit_private_safety_report(self):
        self.client.force_authenticate(self.passenger)
        response = self.client.post(
            "/api/v1/trust/safety/reports/",
            {
                "booking_id": self.booking.pk,
                "category": SafetyReport.Category.UNSAFE_DRIVING,
                "priority": SafetyReport.Priority.HIGH,
                "description": "The driver appeared to be speeding.",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        report = SafetyReport.objects.get(pk=response.data["report"]["id"])
        self.assertEqual(report.reporter, self.passenger)
        self.assertEqual(report.reported_user, self.driver)
        self.assertNotIn("admin_note", response.data["report"])

    def test_unrelated_user_cannot_submit_report_for_someone_elses_booking(self):
        self.client.force_authenticate(self.other)
        response = self.client.post(
            "/api/v1/trust/safety/reports/",
            {
                "booking_id": self.booking.pk,
                "category": SafetyReport.Category.OTHER,
                "description": "This is not my booking.",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(SafetyReport.objects.count(), 0)

    def test_reporter_can_only_see_their_own_reports_and_admin_can_update(self):
        own = SafetyReport.objects.create(
            reporter=self.passenger,
            reported_user=self.driver,
            journey=self.journey,
            booking=self.booking,
            category=SafetyReport.Category.HARASSMENT,
            description="Private report.",
        )
        SafetyReport.objects.create(
            reporter=self.other,
            journey=self.journey,
            category=SafetyReport.Category.OTHER,
            description="Another report.",
        )
        self.client.force_authenticate(self.passenger)
        mine = self.client.get("/api/v1/trust/safety/reports/mine/")
        self.assertEqual(mine.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mine.data), 1)
        self.assertNotIn("admin_note", mine.data[0])
        self.assertEqual(
            self.client.get("/api/v1/trust/safety/admin/reports/").status_code,
            status.HTTP_403_FORBIDDEN,
        )

        admin = self.create_user(
            "trust-admin@example.com", "+919876541004", User.Role.ADMIN, is_staff=True
        )
        self.client.force_authenticate(admin)
        queue = self.client.get("/api/v1/trust/safety/admin/reports/?status=open")
        self.assertEqual(queue.status_code, status.HTTP_200_OK)
        self.assertEqual(len(queue.data), 2)
        changed = self.client.patch(
            f"/api/v1/trust/safety/admin/reports/{own.pk}/",
            {"status": SafetyReport.Status.REVIEWING, "admin_note": "Assigned to safety reviewer."},
            format="json",
        )
        self.assertEqual(changed.status_code, status.HTTP_200_OK)
        self.assertEqual(changed.data["report"]["admin_note"], "Assigned to safety reviewer.")
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.passenger,
                event_type=Notification.EventType.SAFETY_UPDATE,
            ).exists()
        )

    def test_only_other_booking_participant_can_be_named_in_report(self):
        self.client.force_authenticate(self.passenger)
        response = self.client.post(
            "/api/v1/trust/safety/reports/",
            {
                "booking_id": self.booking.pk,
                "reported_user_id": self.other.pk,
                "category": SafetyReport.Category.OTHER,
                "description": "Invalid target.",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_participants_can_review_each_other_only_after_completion(self):
        self.client.force_authenticate(self.passenger)
        too_early = self.client.post(
            f"/api/v1/trust/reviews/{self.booking.pk}/",
            {"rating": 5, "comment": "Great trip."},
            format="json",
        )
        self.assertEqual(too_early.status_code, status.HTTP_409_CONFLICT)

        self.journey.status = Journey.Status.COMPLETED
        self.journey.save(update_fields=["status"])
        passenger_review = self.client.post(
            f"/api/v1/trust/reviews/{self.booking.pk}/",
            {"rating": 5, "comment": "Great trip."},
            format="json",
        )
        self.assertEqual(passenger_review.status_code, status.HTTP_201_CREATED)
        self.assertEqual(passenger_review.data["review"]["reviewee_name"], self.driver.display_name)
        duplicate = self.client.post(
            f"/api/v1/trust/reviews/{self.booking.pk}/",
            {"rating": 4, "comment": "Second review."},
            format="json",
        )
        self.assertEqual(duplicate.status_code, status.HTTP_409_CONFLICT)

        self.client.force_authenticate(self.driver)
        driver_review = self.client.post(
            f"/api/v1/trust/reviews/{self.booking.pk}/",
            {"rating": 4, "comment": "Good passenger."},
            format="json",
        )
        self.assertEqual(driver_review.status_code, status.HTTP_201_CREATED)
        self.assertEqual(JourneyReview.objects.filter(booking=self.booking).count(), 2)

    def test_unrelated_user_cannot_review_booking(self):
        self.journey.status = Journey.Status.COMPLETED
        self.journey.save(update_fields=["status"])
        self.client.force_authenticate(self.other)
        response = self.client.post(
            f"/api/v1/trust/reviews/{self.booking.pk}/",
            {"rating": 5},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
