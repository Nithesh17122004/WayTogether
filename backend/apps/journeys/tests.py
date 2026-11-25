from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.drivers.models import DriverProfile, Vehicle, VerificationDocument
from .models import Journey, JourneyStop
from .services import MapsProviderError, MapsRateLimitError, get_route_preview, search_locations

User = get_user_model()


class JourneyApiTests(APITestCase):
    def create_driver(self, email="driver@example.com", approved=False):
        user = User.objects.create_user(
            email=email,
            phone="+919876543210" if email == "driver@example.com" else "+919876543211",
            password="A-Strong-Unique-Password-928!",
            first_name="Test Driver",
            role=User.Role.DRIVER,
            is_email_verified=True,
            is_phone_verified=True,
        )
        profile = DriverProfile.objects.create(
            user=user,
            verification_status=(
                DriverProfile.VerificationStatus.APPROVED
                if approved else DriverProfile.VerificationStatus.DRAFT
            ),
        )
        return user, profile

    def create_vehicle(self, owner, approved=False):
        return Vehicle.objects.create(
            owner=owner,
            registration_number="TN01AB1234" if owner.email == "driver@example.com" else "TN02CD4567",
            make="Honda",
            model="City",
            manufacture_year=2022,
            vehicle_type=Vehicle.VehicleType.SEDAN,
            passenger_seats=3,
            private_use_attested=True,
            verification_status=(
                Vehicle.VerificationStatus.APPROVED
                if approved else Vehicle.VerificationStatus.DRAFT
            ),
        )

    def create_approved_documents(self, owner, vehicle):
        expiry = timezone.localdate() + timedelta(days=365)
        common = {
            "owner": owner,
            "file": "private/test-document.pdf",
            "original_file_name": "test-document.pdf",
            "content_type": "application/pdf",
            "file_size": 128,
            "review_status": VerificationDocument.ReviewStatus.APPROVED,
            "reviewed_at": timezone.now(),
            "is_current": True,
        }
        VerificationDocument.objects.create(
            document_type=VerificationDocument.DocumentType.DRIVER_LICENSE,
            **common,
        )
        for document_type in (
            VerificationDocument.DocumentType.VEHICLE_REGISTRATION,
            VerificationDocument.DocumentType.INSURANCE,
            VerificationDocument.DocumentType.VEHICLE_PHOTO,
        ):
            VerificationDocument.objects.create(
                document_type=document_type,
                vehicle=vehicle,
                expiry_date=expiry if document_type == VerificationDocument.DocumentType.INSURANCE else None,
                **common,
            )

    def draft_payload(self, vehicle, **overrides):
        payload = {
            "vehicle": vehicle.pk,
            "origin_name": "Chennai, Tamil Nadu",
            "origin_latitude": "13.0827000",
            "origin_longitude": "80.2707000",
            "destination_name": "Bengaluru, Karnataka",
            "destination_latitude": "12.9716000",
            "destination_longitude": "77.5946000",
            "travel_date": (timezone.localdate() + timedelta(days=3)).isoformat(),
            "departure_time": "07:30",
            "seats_offered": 2,
            "fuel_expense": "1200.00",
            "toll_expense": "250.00",
            "parking_expense": "0.00",
            "other_expense": "50.00",
            "expense_note": "Estimated shared journey costs",
            "description": "A journey I was already planning to make.",
            "route_distance_km": "350.00",
            "route_duration_minutes": 375,
            "route_geometry": [[80.2707, 13.0827], [81.0, 13.0], [77.5946, 12.9716]],
            "stops": [
                {
                    "location_name": "Vellore, Tamil Nadu",
                    "latitude": "12.9165000",
                    "longitude": "79.1325000",
                }
            ],
            "independently_planned": True,
            "expenses_only": True,
        }
        payload.update(overrides)
        return payload

    def create_published_journey(self, driver, vehicle, travel_date=None):
        journey = Journey.objects.create(
            driver=driver,
            vehicle=vehicle,
            origin_name="Chennai, Tamil Nadu",
            origin_latitude=Decimal("13.0827000"),
            origin_longitude=Decimal("80.2707000"),
            destination_name="Bengaluru, Karnataka",
            destination_latitude=Decimal("12.9716000"),
            destination_longitude=Decimal("77.5946000"),
            travel_date=travel_date or timezone.localdate() + timedelta(days=3),
            departure_time="07:30",
            seats_offered=2,
            fuel_expense=Decimal("1200.00"),
            toll_expense=Decimal("250.00"),
            other_expense=Decimal("50.00"),
            route_distance_km=Decimal("350.00"),
            route_duration_minutes=375,
            route_geometry=[[80.2707, 13.0827], [77.5946, 12.9716]],
            independently_planned=True,
            expenses_only=True,
            status=Journey.Status.PUBLISHED,
            published_at=timezone.now(),
        )
        return journey

    def test_verified_driver_can_create_draft_with_ordered_stops(self):
        driver, _ = self.create_driver()
        vehicle = self.create_vehicle(driver)
        self.client.force_authenticate(driver)
        response = self.client.post(
            "/api/v1/journeys/",
            self.draft_payload(vehicle),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        journey = Journey.objects.get(pk=response.data["id"])
        self.assertEqual(journey.driver, driver)
        self.assertEqual(journey.status, Journey.Status.DRAFT)
        self.assertEqual(journey.stops.count(), 1)
        self.assertEqual(journey.stops.first().sequence, 1)
        self.assertEqual(response.data["estimated_total_expenses"], "1500.00")
        self.assertEqual(response.data["estimated_contribution_per_passenger"], "500.00")

    def test_passenger_cannot_create_a_journey(self):
        passenger = User.objects.create_user(
            email="passenger@example.com",
            phone="+919876543219",
            password="A-Strong-Unique-Password-928!",
            role=User.Role.PASSENGER,
            is_email_verified=True,
            is_phone_verified=True,
        )
        self.client.force_authenticate(passenger)
        response = self.client.post("/api/v1/journeys/", {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_driver_cannot_use_another_users_vehicle(self):
        driver, _ = self.create_driver()
        other, _ = self.create_driver("other@example.com")
        vehicle = self.create_vehicle(other)
        self.client.force_authenticate(driver)
        response = self.client.post(
            "/api/v1/journeys/",
            self.draft_payload(vehicle),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_seats_cannot_exceed_vehicle_capacity(self):
        driver, _ = self.create_driver()
        vehicle = self.create_vehicle(driver)
        self.client.force_authenticate(driver)
        response = self.client.post(
            "/api/v1/journeys/",
            self.draft_payload(vehicle, seats_offered=4),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_driver_must_attest_independently_planned_and_expense_only(self):
        driver, _ = self.create_driver()
        vehicle = self.create_vehicle(driver)
        self.client.force_authenticate(driver)
        response = self.client.post(
            "/api/v1/journeys/",
            self.draft_payload(vehicle, independently_planned=False),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_publishing_is_blocked_until_driver_and_vehicle_are_approved(self):
        driver, _ = self.create_driver()
        vehicle = self.create_vehicle(driver)
        self.client.force_authenticate(driver)
        created = self.client.post("/api/v1/journeys/", self.draft_payload(vehicle), format="json")
        response = self.client.post(f"/api/v1/journeys/{created.data['id']}/publish/", {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_approved_driver_and_vehicle_can_publish_a_draft(self):
        driver, profile = self.create_driver(approved=True)
        vehicle = self.create_vehicle(driver, approved=True)
        self.create_approved_documents(driver, vehicle)
        self.client.force_authenticate(driver)
        created = self.client.post("/api/v1/journeys/", self.draft_payload(vehicle), format="json")
        self.assertEqual(created.status_code, status.HTTP_201_CREATED)

        response = self.client.post(f"/api/v1/journeys/{created.data['id']}/publish/", {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["journey"]["status"], Journey.Status.PUBLISHED)

    def test_driver_can_only_list_own_journeys(self):
        driver, _ = self.create_driver()
        other, _ = self.create_driver("other@example.com")
        vehicle = self.create_vehicle(driver)
        other_vehicle = self.create_vehicle(other)
        Journey.objects.create(
            driver=driver, vehicle=vehicle,
            origin_name="A", origin_latitude=1, origin_longitude=1,
            destination_name="B", destination_latitude=2, destination_longitude=2,
            travel_date=timezone.localdate() + timedelta(days=2),
            departure_time="08:00", seats_offered=1,
            independently_planned=True, expenses_only=True,
        )
        Journey.objects.create(
            driver=other, vehicle=other_vehicle,
            origin_name="C", origin_latitude=3, origin_longitude=3,
            destination_name="D", destination_latitude=4, destination_longitude=4,
            travel_date=timezone.localdate() + timedelta(days=2),
            departure_time="09:00", seats_offered=1,
            independently_planned=True, expenses_only=True,
        )
        self.client.force_authenticate(driver)
        response = self.client.get("/api/v1/journeys/mine/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_search_matches_nearby_origin_and_destination_and_seat_count(self):
        driver, _ = self.create_driver(approved=True)
        vehicle = self.create_vehicle(driver, approved=True)
        self.create_approved_documents(driver, vehicle)
        travel_date = timezone.localdate() + timedelta(days=3)
        journey = self.create_published_journey(driver, vehicle, travel_date)

        params = {
            "origin_lat": "13.08",
            "origin_lon": "80.27",
            "destination_lat": "12.97",
            "destination_lon": "77.59",
            "date": travel_date.isoformat(),
            "seats": "2",
        }
        response = self.client.get("/api/v1/journeys/", params)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([item["id"] for item in response.data], [journey.pk])

        no_seats = self.client.get("/api/v1/journeys/", {**params, "seats": "4"})
        self.assertEqual(no_seats.status_code, status.HTTP_200_OK)
        self.assertEqual(no_seats.data, [])

    def test_search_can_match_a_journey_segment_using_intermediate_stops(self):
        driver, _ = self.create_driver(approved=True)
        vehicle = self.create_vehicle(driver, approved=True)
        self.create_approved_documents(driver, vehicle)
        travel_date = timezone.localdate() + timedelta(days=4)
        journey = self.create_published_journey(driver, vehicle, travel_date)
        JourneyStop.objects.create(
            journey=journey, sequence=1, location_name="Vellore, Tamil Nadu",
            latitude=Decimal("12.9165000"), longitude=Decimal("79.1325000"),
        )
        JourneyStop.objects.create(
            journey=journey, sequence=2, location_name="Hosur, Tamil Nadu",
            latitude=Decimal("12.7409000"), longitude=Decimal("77.8253000"),
        )
        response = self.client.get("/api/v1/journeys/", {
            "origin_lat": "12.9165",
            "origin_lon": "79.1325",
            "destination_lat": "12.7409",
            "destination_lon": "77.8253",
            "date": travel_date.isoformat(),
            "seats": "1",
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["matched_origin_name"], "Vellore, Tamil Nadu")
        self.assertEqual(response.data[0]["matched_destination_name"], "Hosur, Tamil Nadu")

    def test_published_journey_is_public_but_draft_is_private(self):
        driver, _ = self.create_driver()
        vehicle = self.create_vehicle(driver)
        draft = Journey.objects.create(
            driver=driver, vehicle=vehicle,
            origin_name="A", origin_latitude=1, origin_longitude=1,
            destination_name="B", destination_latitude=2, destination_longitude=2,
            travel_date=timezone.localdate() + timedelta(days=2),
            departure_time="08:00", seats_offered=1,
            independently_planned=True, expenses_only=True,
        )
        response = self.client.get(f"/api/v1/journeys/{draft.pk}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.client.force_authenticate(driver)
        own_draft = self.client.get(f"/api/v1/journeys/{draft.pk}/")
        self.assertEqual(own_draft.status_code, status.HTTP_200_OK)

    def test_cancelled_journey_does_not_appear_in_public_search(self):
        driver, _ = self.create_driver(approved=True)
        vehicle = self.create_vehicle(driver, approved=True)
        self.create_approved_documents(driver, vehicle)
        journey = self.create_published_journey(driver, vehicle)
        journey.status = Journey.Status.CANCELLED
        journey.save(update_fields=["status"])
        params = {
            "origin_lat": "13.08", "origin_lon": "80.27",
            "destination_lat": "12.97", "destination_lon": "77.59",
            "date": journey.travel_date.isoformat(), "seats": "1",
        }
        response = self.client.get("/api/v1/journeys/", params)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    @patch("apps.journeys.services.requests.get")
    def test_location_search_caches_queries_and_enforces_global_limit(self, request_mock):
        cache.clear()
        response = request_mock.return_value
        response.json.return_value = [{
            "lat": "13.0827",
            "lon": "80.2707",
            "display_name": "Chennai, Tamil Nadu, India",
            "address": {"city": "Chennai", "state": "Tamil Nadu"},
        }]
        response.raise_for_status.return_value = None

        first = search_locations("Chennai Central")
        second = search_locations("Chennai Central")
        self.assertEqual(first, second)
        self.assertEqual(request_mock.call_count, 1)
        self.assertEqual(first[0]["name"], "Chennai")

        with self.assertRaises(MapsRateLimitError):
            search_locations("Madurai")

    def test_route_preview_requires_configured_provider(self):
        with patch("apps.journeys.services.OSRM_ROUTE_URL", ""):
            with self.assertRaises(MapsProviderError):
                get_route_preview(13.08, 80.27, 12.97, 77.59)

    @patch("apps.journeys.views.search_locations")
    def test_location_search_uses_geocoding_service(self, search_mock):
        search_mock.return_value = [{"name": "Chennai", "latitude": 13.08, "longitude": 80.27}]
        response = self.client.get("/api/v1/journeys/locations/search/?q=Chennai")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["results"][0]["name"], "Chennai")
        search_mock.assert_called_once_with("Chennai")

    @patch("apps.journeys.views.get_route_preview")
    def test_route_preview_returns_distance_duration_and_geometry(self, route_mock):
        driver, _ = self.create_driver()
        self.client.force_authenticate(driver)
        route_mock.return_value = {
            "distance_km": 350.2,
            "duration_minutes": 380,
            "geometry": [[80.27, 13.08], [77.59, 12.97]],
        }
        response = self.client.get(
            "/api/v1/journeys/route-preview/",
            {
                "origin_lat": 13.08, "origin_lon": 80.27,
                "destination_lat": 12.97, "destination_lon": 77.59,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["distance_km"], 350.2)
        route_mock.assert_called_once()



from apps.bookings.models import Booking


class BookingApiTests(APITestCase):
    def create_driver(self, email="driver@example.com", phone="+919876543210"):
        user = User.objects.create_user(
            email=email,
            phone=phone,
            password="A-Strong-Unique-Password-928!",
            first_name="Verified Driver",
            role=User.Role.DRIVER,
            is_email_verified=True,
            is_phone_verified=True,
        )
        DriverProfile.objects.create(
            user=user,
            verification_status=DriverProfile.VerificationStatus.APPROVED,
        )
        return user

    def create_passenger(self, email="passenger@example.com", phone="+919876543220"):
        return User.objects.create_user(
            email=email,
            phone=phone,
            password="A-Strong-Unique-Password-928!",
            first_name="Test Passenger",
            role=User.Role.PASSENGER,
            is_email_verified=True,
            is_phone_verified=True,
        )

    def create_approved_vehicle(self, driver, seats=3):
        return Vehicle.objects.create(
            owner=driver,
            registration_number="TN09AB1234" if driver.email == "driver@example.com" else "TN10CD5678",
            make="Honda",
            model="City",
            manufacture_year=2022,
            vehicle_type=Vehicle.VehicleType.SEDAN,
            passenger_seats=seats,
            private_use_attested=True,
            verification_status=Vehicle.VerificationStatus.APPROVED,
        )

    def create_approved_documents(self, driver, vehicle):
        expiry = timezone.localdate() + timedelta(days=365)
        base = {
            "owner": driver,
            "file": "private/test-driver-document.pdf",
            "original_file_name": "test-driver-document.pdf",
            "content_type": "application/pdf",
            "file_size": 128,
            "review_status": VerificationDocument.ReviewStatus.APPROVED,
            "reviewed_at": timezone.now(),
            "is_current": True,
        }
        VerificationDocument.objects.create(
            document_type=VerificationDocument.DocumentType.DRIVER_LICENSE,
            **base,
        )
        for document_type in (
            VerificationDocument.DocumentType.VEHICLE_REGISTRATION,
            VerificationDocument.DocumentType.INSURANCE,
            VerificationDocument.DocumentType.VEHICLE_PHOTO,
        ):
            VerificationDocument.objects.create(
                document_type=document_type,
                vehicle=vehicle,
                expiry_date=expiry if document_type == VerificationDocument.DocumentType.INSURANCE else None,
                **base,
            )

    def create_journey(self, driver, vehicle, seats=2):
        self.create_approved_documents(driver, vehicle)
        travel_date = timezone.localdate() + timedelta(days=4)
        journey = Journey.objects.create(
            driver=driver,
            vehicle=vehicle,
            origin_name="Chennai, Tamil Nadu",
            origin_latitude=Decimal("13.0827000"),
            origin_longitude=Decimal("80.2707000"),
            destination_name="Bengaluru, Karnataka",
            destination_latitude=Decimal("12.9716000"),
            destination_longitude=Decimal("77.5946000"),
            travel_date=travel_date,
            departure_time="08:00",
            seats_offered=seats,
            fuel_expense=Decimal("1200.00"),
            toll_expense=Decimal("250.00"),
            parking_expense=Decimal("0.00"),
            other_expense=Decimal("50.00"),
            independently_planned=True,
            expenses_only=True,
            status=Journey.Status.PUBLISHED,
            published_at=timezone.now(),
        )
        return journey

    def create_request(self, passenger, journey, seats=1):
        self.client.force_authenticate(passenger)
        return self.client.post(
            "/api/v1/bookings/",
            {
                "journey": journey.pk,
                "seats_requested": seats,
                "request_message": "I can meet at the agreed pickup point.",
            },
            format="json",
        )

    def approve(self, driver, booking_id):
        self.client.force_authenticate(driver)
        return self.client.post(
            f"/api/v1/bookings/{booking_id}/approve/",
            {"driver_response": "Confirmed. See you at the pickup point."},
            format="json",
        )

    def test_passenger_can_request_seats_but_request_does_not_reserve_them(self):
        driver = self.create_driver()
        vehicle = self.create_approved_vehicle(driver, seats=3)
        journey = self.create_journey(driver, vehicle, seats=2)
        passenger = self.create_passenger()

        response = self.create_request(passenger, journey, seats=1)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        booking = Booking.objects.get(pk=response.data["booking"]["id"])
        self.assertEqual(booking.status, Booking.Status.PENDING)

        journey_response = self.client.get(f"/api/v1/journeys/{journey.pk}/")
        self.assertEqual(journey_response.status_code, status.HTTP_200_OK)
        self.assertEqual(journey_response.data["confirmed_seats"], 0)
        self.assertEqual(journey_response.data["available_seats"], 2)

    def test_passenger_cannot_book_own_journey(self):
        driver = self.create_driver()
        vehicle = self.create_approved_vehicle(driver)
        journey = self.create_journey(driver, vehicle)
        self.client.force_authenticate(driver)
        response = self.client.post(
            "/api/v1/bookings/",
            {"journey": journey.pk, "seats_requested": 1},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_passenger_can_have_only_one_active_booking_for_a_journey(self):
        driver = self.create_driver()
        vehicle = self.create_approved_vehicle(driver)
        journey = self.create_journey(driver, vehicle)
        passenger = self.create_passenger()

        first = self.create_request(passenger, journey, 1)
        second = self.create_request(passenger, journey, 1)
        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(Booking.objects.filter(journey=journey, passenger=passenger).count(), 1)

    def test_only_journey_driver_can_approve_booking(self):
        driver = self.create_driver()
        other_driver = self.create_driver("other-driver@example.com", "+919876543212")
        vehicle = self.create_approved_vehicle(driver)
        journey = self.create_journey(driver, vehicle)
        passenger = self.create_passenger()
        booking_response = self.create_request(passenger, journey)
        booking_id = booking_response.data["booking"]["id"]

        self.client.force_authenticate(other_driver)
        response = self.client.post(f"/api/v1/bookings/{booking_id}/approve/", {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_driver_approval_reserves_seats_and_calculates_provisional_share(self):
        driver = self.create_driver()
        vehicle = self.create_approved_vehicle(driver)
        journey = self.create_journey(driver, vehicle, seats=2)
        passenger = self.create_passenger()
        request = self.create_request(passenger, journey, seats=1)
        booking_id = request.data["booking"]["id"]

        response = self.approve(driver, booking_id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        booking = Booking.objects.get(pk=booking_id)
        self.assertEqual(booking.status, Booking.Status.CONFIRMED)
        self.assertEqual(booking.estimated_contribution_per_passenger, Decimal("750.00"))
        self.assertEqual(booking.estimated_contribution_total, Decimal("750.00"))

        journey_response = self.client.get(f"/api/v1/journeys/{journey.pk}/")
        self.assertEqual(journey_response.data["confirmed_seats"], 1)
        self.assertEqual(journey_response.data["available_seats"], 1)

    def test_pending_requests_do_not_lock_seats_but_approvals_cannot_oversell(self):
        driver = self.create_driver()
        vehicle = self.create_approved_vehicle(driver, seats=3)
        journey = self.create_journey(driver, vehicle, seats=2)
        passenger_one = self.create_passenger()
        passenger_two = self.create_passenger("passenger2@example.com", "+919876543221")

        first = self.create_request(passenger_one, journey, seats=2)
        second = self.create_request(passenger_two, journey, seats=2)
        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second.status_code, status.HTTP_201_CREATED)

        first_approval = self.approve(driver, first.data["booking"]["id"])
        second_approval = self.approve(driver, second.data["booking"]["id"])
        self.assertEqual(first_approval.status_code, status.HTTP_200_OK)
        self.assertEqual(second_approval.status_code, status.HTTP_409_CONFLICT)

        journey_response = self.client.get(f"/api/v1/journeys/{journey.pk}/")
        self.assertEqual(journey_response.data["confirmed_seats"], 2)
        self.assertEqual(journey_response.data["available_seats"], 0)

    def test_driver_can_decline_pending_request_with_response(self):
        driver = self.create_driver()
        vehicle = self.create_approved_vehicle(driver)
        journey = self.create_journey(driver, vehicle)
        passenger = self.create_passenger()
        request = self.create_request(passenger, journey)

        self.client.force_authenticate(driver)
        response = self.client.post(
            f"/api/v1/bookings/{request.data['booking']['id']}/decline/",
            {"driver_response": "The pickup location is not suitable."},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["booking"]["status"], Booking.Status.DECLINED)
        self.assertEqual(response.data["booking"]["driver_response"], "The pickup location is not suitable.")

    def test_passenger_can_cancel_confirmed_booking_and_release_seats(self):
        driver = self.create_driver()
        vehicle = self.create_approved_vehicle(driver)
        journey = self.create_journey(driver, vehicle, seats=2)
        passenger = self.create_passenger()
        request = self.create_request(passenger, journey)
        self.approve(driver, request.data["booking"]["id"])

        self.client.force_authenticate(passenger)
        response = self.client.post(f"/api/v1/bookings/{request.data['booking']['id']}/cancel/", {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["booking"]["status"], Booking.Status.CANCELLED)

        journey_response = self.client.get(f"/api/v1/journeys/{journey.pk}/")
        self.assertEqual(journey_response.data["confirmed_seats"], 0)
        self.assertEqual(journey_response.data["available_seats"], 2)

    def test_journey_driver_cancellation_cancels_pending_and_confirmed_bookings(self):
        driver = self.create_driver()
        vehicle = self.create_approved_vehicle(driver)
        journey = self.create_journey(driver, vehicle)
        passenger_one = self.create_passenger()
        passenger_two = self.create_passenger("passenger2@example.com", "+919876543221")
        first = self.create_request(passenger_one, journey)
        second = self.create_request(passenger_two, journey)
        self.approve(driver, first.data["booking"]["id"])

        self.client.force_authenticate(driver)
        response = self.client.post(f"/api/v1/journeys/{journey.pk}/cancel/", {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            Booking.objects.filter(
                journey=journey,
                status__in=(Booking.Status.PENDING, Booking.Status.CONFIRMED),
            ).count(),
            0,
        )
        self.assertEqual(Booking.objects.get(pk=first.data["booking"]["id"]).status, Booking.Status.CANCELLED)
        self.assertEqual(Booking.objects.get(pk=second.data["booking"]["id"]).status, Booking.Status.CANCELLED)

    def test_passenger_cannot_see_another_passengers_booking(self):
        driver = self.create_driver()
        vehicle = self.create_approved_vehicle(driver)
        journey = self.create_journey(driver, vehicle)
        passenger_one = self.create_passenger()
        passenger_two = self.create_passenger("passenger2@example.com", "+919876543221")
        request = self.create_request(passenger_one, journey)
        booking_id = request.data["booking"]["id"]

        self.client.force_authenticate(passenger_two)
        response = self.client.get(f"/api/v1/bookings/{booking_id}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_driver_request_queue_contains_only_the_drivers_journeys(self):
        driver = self.create_driver()
        other_driver = self.create_driver("other-driver@example.com", "+919876543212")
        vehicle = self.create_approved_vehicle(driver)
        other_vehicle = self.create_approved_vehicle(other_driver)
        journey = self.create_journey(driver, vehicle)
        other_journey = self.create_journey(other_driver, other_vehicle)
        passenger = self.create_passenger()
        other_passenger = self.create_passenger("passenger2@example.com", "+919876543221")
        self.create_request(passenger, journey)
        self.create_request(other_passenger, other_journey)

        self.client.force_authenticate(driver)
        response = self.client.get("/api/v1/bookings/driver/requests/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["journey_id"], journey.pk)

    def test_cancelled_or_departed_journey_rejects_new_booking_requests(self):
        driver = self.create_driver()
        vehicle = self.create_approved_vehicle(driver)
        journey = self.create_journey(driver, vehicle)
        journey.status = Journey.Status.CANCELLED
        journey.save(update_fields=["status"])
        passenger = self.create_passenger()
        response = self.create_request(passenger, journey)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_unverified_passenger_cannot_create_booking(self):
        driver = self.create_driver()
        vehicle = self.create_approved_vehicle(driver)
        journey = self.create_journey(driver, vehicle)
        passenger = User.objects.create_user(
            email="unverified-passenger@example.com",
            phone="+919876543222",
            password="A-Strong-Unique-Password-928!",
            role=User.Role.PASSENGER,
        )
        self.client.force_authenticate(passenger)
        response = self.client.post(
            "/api/v1/bookings/",
            {"journey": journey.pk, "seats_requested": 1},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
