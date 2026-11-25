from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.drivers.models import DriverProfile, Vehicle, VerificationDocument
from .models import Journey, JourneyStop

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
