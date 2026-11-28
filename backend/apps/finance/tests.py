from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import PassengerVerification
from apps.bookings.models import Booking
from apps.drivers.models import DriverProfile, Vehicle
from apps.journeys.models import Journey

from .models import ExpenseSettlement, PassengerContribution, RazorpayPayment, SandboxPayment, SandboxRefund

User = get_user_model()


class FinanceApiTests(APITestCase):
    def create_user(self, email, phone, role, *, is_staff=False):
        user = User.objects.create_user(
            email=email,
            phone=phone,
            password="A-Strong-Unique-Password-928!",
            first_name=email.split("@")[0].title(),
            role=role,
            is_email_verified=True,
            is_phone_verified=True,
            is_staff=is_staff,
        )
        if role == User.Role.DRIVER:
            DriverProfile.objects.create(
                user=user,
                verification_status=DriverProfile.VerificationStatus.APPROVED,
            )
        if role == User.Role.PASSENGER:
            PassengerVerification.objects.create(
                user=user,
                masked_aadhaar_document="private/test-aadhaar.pdf",
                passenger_photo="private/test-passenger-photo.jpg",
                masked_aadhaar_file_name="test-aadhaar.pdf",
                passenger_photo_file_name="test-passenger-photo.jpg",
                consent_at=timezone.now(),
                status=PassengerVerification.Status.APPROVED,
                reviewed_at=timezone.now(),
            )
        return user

    def setUp(self):
        # Avoid cross-test DRF throttle state leaking between API test cases.
        cache.clear()
        self.driver = self.create_user(
            "finance-driver@example.com", "+919876540001", User.Role.DRIVER
        )
        self.passenger_one = self.create_user(
            "finance-passenger1@example.com", "+919876540002", User.Role.PASSENGER
        )
        self.passenger_two = self.create_user(
            "finance-passenger2@example.com", "+919876540003", User.Role.PASSENGER
        )
        self.vehicle = Vehicle.objects.create(
            owner=self.driver,
            registration_number="TN20AB1234",
            make="Honda",
            model="City",
            manufacture_year=2022,
            vehicle_type=Vehicle.VehicleType.SEDAN,
            passenger_seats=4,
            private_use_attested=True,
            verification_status=Vehicle.VerificationStatus.APPROVED,
        )
        self.journey = self.create_journey()

    def create_journey(self, *, days_offset=-1):
        return Journey.objects.create(
            driver=self.driver,
            vehicle=self.vehicle,
            origin_name="Chennai, Tamil Nadu",
            origin_latitude=Decimal("13.0827000"),
            origin_longitude=Decimal("80.2707000"),
            destination_name="Bengaluru, Karnataka",
            destination_latitude=Decimal("12.9716000"),
            destination_longitude=Decimal("77.5946000"),
            travel_date=timezone.localdate() + timedelta(days=days_offset),
            departure_time="08:00",
            seats_offered=4,
            fuel_expense=Decimal("1000.00"),
            independently_planned=True,
            expenses_only=True,
            status=Journey.Status.PUBLISHED,
            published_at=timezone.now(),
        )

    def create_booking(self, passenger, seats=1, journey=None):
        return Booking.objects.create(
            journey=journey or self.journey,
            passenger=passenger,
            seats_requested=seats,
            status=Booking.Status.CONFIRMED,
        )

    def submit_settlement(self, journey=None, *, driver=None, **expenses):
        self.client.force_authenticate(driver or self.driver)
        return self.client.post(
            f"/api/v1/finance/journeys/{(journey or self.journey).pk}/settlement/",
            expenses or {"actual_fuel_expense": "1000.00"},
            format="json",
        )

    @override_settings(FINANCE_SANDBOX_ENABLED=True)
    def test_finalizes_actual_expenses_and_allocates_by_confirmed_seat_count(self):
        booking_one = self.create_booking(self.passenger_one, seats=2)
        booking_two = self.create_booking(self.passenger_two, seats=1)

        response = self.submit_settlement(
            actual_fuel_expense="1000.00",
            actual_toll_expense="200.00",
            actual_parking_expense="0.00",
            actual_other_expense="0.00",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        settlement = ExpenseSettlement.objects.get(journey=self.journey)
        self.journey.refresh_from_db()
        self.assertEqual(self.journey.status, Journey.Status.COMPLETED)
        self.assertEqual(settlement.eligible_total, Decimal("1200.00"))
        self.assertEqual(settlement.passenger_seat_count, 3)
        self.assertEqual(settlement.driver_share, Decimal("300.00"))

        share_one = PassengerContribution.objects.get(booking=booking_one)
        share_two = PassengerContribution.objects.get(booking=booking_two)
        self.assertEqual(share_one.per_seat_amount, Decimal("300.00"))
        self.assertEqual(share_one.total_amount, Decimal("600.00"))
        self.assertEqual(share_two.total_amount, Decimal("300.00"))
        self.assertEqual(
            settlement.driver_share + share_one.total_amount + share_two.total_amount,
            settlement.eligible_total,
        )

    def test_rounding_remainder_is_assigned_to_driver_and_ledger_reconciles(self):
        booking_one = self.create_booking(self.passenger_one)
        booking_two = self.create_booking(self.passenger_two)
        response = self.submit_settlement(actual_fuel_expense="1000.01")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        settlement = ExpenseSettlement.objects.get(journey=self.journey)
        shares = list(PassengerContribution.objects.filter(
            booking__in=(booking_one, booking_two)
        ))
        self.assertEqual(settlement.driver_share, Decimal("333.35"))
        self.assertEqual(sum(x.total_amount for x in shares), Decimal("666.66"))
        self.assertEqual(
            settlement.driver_share + sum(x.total_amount for x in shares),
            Decimal("1000.01"),
        )

    def test_driver_share_is_full_amount_when_no_passenger_seats_confirmed(self):
        response = self.submit_settlement(actual_fuel_expense="875.50")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        settlement = ExpenseSettlement.objects.get(journey=self.journey)
        self.assertEqual(settlement.passenger_seat_count, 0)
        self.assertEqual(settlement.driver_share, Decimal("875.50"))
        self.assertEqual(PassengerContribution.objects.count(), 0)

    def test_cannot_finalize_before_departure(self):
        future_journey = self.create_journey(days_offset=3)
        response = self.submit_settlement(
            future_journey,
            actual_fuel_expense="100.00",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(ExpenseSettlement.objects.filter(journey=future_journey).exists())

    def test_pending_requests_are_closed_when_expenses_are_finalized(self):
        pending = Booking.objects.create(
            journey=self.journey,
            passenger=self.passenger_one,
            seats_requested=1,
            status=Booking.Status.PENDING,
        )
        self.create_booking(self.passenger_two)
        response = self.submit_settlement(actual_fuel_expense="500.00")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        pending.refresh_from_db()
        self.assertEqual(pending.status, Booking.Status.CANCELLED)
        self.assertEqual(pending.cancelled_by_id, self.driver.id)

    def test_settlement_can_only_be_finalized_once(self):
        self.submit_settlement(actual_fuel_expense="100.00")
        second = self.submit_settlement(actual_fuel_expense="125.00")
        self.assertEqual(second.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(ExpenseSettlement.objects.filter(journey=self.journey).count(), 1)

    def test_passenger_cannot_finalize_journey_expenses(self):
        self.client.force_authenticate(self.passenger_one)
        response = self.client.post(
            f"/api/v1/finance/journeys/{self.journey.pk}/settlement/",
            {"actual_fuel_expense": "100.00"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_driver_cannot_finalize_another_drivers_journey(self):
        other_driver = self.create_user(
            "other-finance-driver@example.com", "+919876540004", User.Role.DRIVER
        )
        response = self.submit_settlement(
            driver=other_driver,
            actual_fuel_expense="100.00",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_negative_expenses_are_rejected(self):
        response = self.submit_settlement(actual_fuel_expense="-1.00")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_passenger_only_sees_their_own_final_contributions(self):
        booking_one = self.create_booking(self.passenger_one)
        self.create_booking(self.passenger_two)
        self.submit_settlement(actual_fuel_expense="900.00")

        self.client.force_authenticate(self.passenger_one)
        response = self.client.get("/api/v1/finance/contributions/mine/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["booking_id"], booking_one.pk)
        self.assertEqual(response.data[0]["total_amount"], "300.00")

    @override_settings(FINANCE_SANDBOX_ENABLED=True)
    def test_passenger_can_create_and_complete_a_sandbox_payment(self):
        booking = self.create_booking(self.passenger_one)
        self.submit_settlement(actual_fuel_expense="600.00")
        contribution = PassengerContribution.objects.get(booking=booking)

        self.client.force_authenticate(self.passenger_one)
        created = self.client.post(
            f"/api/v1/finance/contributions/{contribution.pk}/sandbox-payment/",
            {},
            format="json",
        )
        self.assertEqual(created.status_code, status.HTTP_201_CREATED)
        payment_id = created.data["payment"]["id"]
        self.assertEqual(created.data["payment"]["provider"], "sandbox")
        self.assertEqual(created.data["payment"]["status"], SandboxPayment.Status.CREATED)

        completed = self.client.post(
            f"/api/v1/finance/payments/{payment_id}/sandbox-result/",
            {"outcome": "succeeded"},
            format="json",
        )
        self.assertEqual(completed.status_code, status.HTTP_200_OK)
        self.assertEqual(completed.data["payment"]["status"], SandboxPayment.Status.SUCCEEDED)
        self.assertFalse(hasattr(SandboxPayment.objects.get(pk=payment_id), "provider_transaction_id"))

    @override_settings(FINANCE_SANDBOX_ENABLED=True)
    def test_passenger_cannot_simulate_another_passengers_contribution(self):
        booking = self.create_booking(self.passenger_one)
        self.submit_settlement(actual_fuel_expense="600.00")
        contribution = PassengerContribution.objects.get(booking=booking)

        self.client.force_authenticate(self.passenger_two)
        response = self.client.post(
            f"/api/v1/finance/contributions/{contribution.pk}/sandbox-payment/",
            {},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @override_settings(FINANCE_SANDBOX_ENABLED=True)
    def test_failed_sandbox_payment_can_be_retried(self):
        booking = self.create_booking(self.passenger_one)
        self.submit_settlement(actual_fuel_expense="600.00")
        contribution = PassengerContribution.objects.get(booking=booking)
        self.client.force_authenticate(self.passenger_one)

        created = self.client.post(
            f"/api/v1/finance/contributions/{contribution.pk}/sandbox-payment/",
            {},
            format="json",
        )
        payment_id = created.data["payment"]["id"]
        failed = self.client.post(
            f"/api/v1/finance/payments/{payment_id}/sandbox-result/",
            {"outcome": "failed", "failure_note": "Test decline"},
            format="json",
        )
        self.assertEqual(failed.status_code, status.HTTP_200_OK)
        retry = self.client.post(
            f"/api/v1/finance/contributions/{contribution.pk}/sandbox-payment/",
            {},
            format="json",
        )
        self.assertEqual(retry.status_code, status.HTTP_201_CREATED)
        self.assertNotEqual(retry.data["payment"]["id"], payment_id)

    @override_settings(FINANCE_SANDBOX_ENABLED=True)
    def test_successful_sandbox_payment_can_be_refunded_by_admin_only(self):
        booking = self.create_booking(self.passenger_one)
        self.submit_settlement(actual_fuel_expense="600.00")
        contribution = PassengerContribution.objects.get(booking=booking)
        self.client.force_authenticate(self.passenger_one)
        created = self.client.post(
            f"/api/v1/finance/contributions/{contribution.pk}/sandbox-payment/",
            {},
            format="json",
        )
        payment_id = created.data["payment"]["id"]
        self.client.post(
            f"/api/v1/finance/payments/{payment_id}/sandbox-result/",
            {"outcome": "succeeded"},
            format="json",
        )

        non_admin = self.client.post(
            f"/api/v1/finance/payments/{payment_id}/sandbox-refund/",
            {"reason": "Test refund"},
            format="json",
        )
        self.assertEqual(non_admin.status_code, status.HTTP_403_FORBIDDEN)

        admin = self.create_user(
            "finance-admin@example.com", "+919876540005", User.Role.ADMIN, is_staff=True
        )
        self.client.force_authenticate(admin)
        refunded = self.client.post(
            f"/api/v1/finance/payments/{payment_id}/sandbox-refund/",
            {"reason": "Sandbox test scenario"},
            format="json",
        )
        self.assertEqual(refunded.status_code, status.HTTP_200_OK)
        self.assertEqual(refunded.data["refund"]["amount"], "300.00")
        self.assertEqual(SandboxPayment.objects.get(pk=payment_id).status, SandboxPayment.Status.REFUNDED)
        self.assertEqual(SandboxRefund.objects.filter(payment_id=payment_id).count(), 1)

    @override_settings(FINANCE_SANDBOX_ENABLED=False)
    def test_sandbox_endpoints_are_disabled_when_feature_flag_is_false(self):
        booking = self.create_booking(self.passenger_one)
        self.submit_settlement(actual_fuel_expense="600.00")
        contribution = PassengerContribution.objects.get(booking=booking)
        self.client.force_authenticate(self.passenger_one)
        response = self.client.post(
            f"/api/v1/finance/contributions/{contribution.pk}/sandbox-payment/",
            {},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_contact_numbers_are_hidden_until_booking_payment_is_captured(self):
        booking = self.create_booking(self.passenger_one)
        self.client.force_authenticate(self.passenger_one)

        unpaid = self.client.get(f"/api/v1/bookings/{booking.pk}/")
        self.assertEqual(unpaid.status_code, status.HTTP_200_OK)
        self.assertFalse(unpaid.data["contact_details_released"])
        self.assertIsNone(unpaid.data["driver_phone"])
        self.assertIsNone(unpaid.data["passenger_phone"])

        self.submit_settlement(actual_fuel_expense="600.00")
        contribution = PassengerContribution.objects.get(booking=booking)
        RazorpayPayment.objects.create(
            contribution=contribution,
            order_id="order_contact_release_test",
            payment_id="pay_contact_release_test",
            status=RazorpayPayment.Status.CAPTURED,
            amount=contribution.total_amount,
            currency=contribution.currency,
            test_mode=True,
            completed_at=timezone.now(),
        )

        self.client.force_authenticate(self.passenger_one)
        released = self.client.get(f"/api/v1/bookings/{booking.pk}/")
        self.assertEqual(released.status_code, status.HTTP_200_OK)
        self.assertTrue(released.data["contact_details_released"])
        self.assertEqual(released.data["driver_phone"], self.driver.phone)
        self.assertEqual(released.data["passenger_phone"], self.passenger_one.phone)

        other_passenger = self.create_user(
            "other-contact@example.com", "+919876540009", User.Role.PASSENGER
        )
        self.client.force_authenticate(other_passenger)
        hidden_from_other_user = self.client.get(f"/api/v1/bookings/{booking.pk}/")
        self.assertEqual(hidden_from_other_user.status_code, status.HTTP_404_NOT_FOUND)

