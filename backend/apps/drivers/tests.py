from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from .models import DriverProfile, Vehicle, VerificationDocument

User = get_user_model()
PDF_BYTES = b"%PDF-1.4\nWayTogether test document\n%%EOF"
JPEG_BYTES = b"\xff\xd8\xffWayTogether test photo"


def make_pdf(name="test-document.pdf", content=PDF_BYTES, content_type="application/pdf"):
    return SimpleUploadedFile(name, content, content_type=content_type)


def make_jpg(name="driver-photo.jpg"):
    return SimpleUploadedFile(name, JPEG_BYTES, content_type="image/jpeg")


class DriverVerificationApiTests(APITestCase):
    def create_driver(self, email="driver@example.com", phone="+919876543210", role=User.Role.DRIVER):
        return User.objects.create_user(
            email=email,
            phone=phone,
            password="A-Strong-Unique-Password-928!",
            first_name="Test Driver",
            role=role,
            is_email_verified=True,
            is_phone_verified=False,
        )

    def create_vehicle(self, owner):
        return Vehicle.objects.create(
            owner=owner,
            registration_number="tn 01 ab 1234",
            make="Honda",
            model="City",
            manufacture_year=2022,
            colour="Blue",
            vehicle_category=Vehicle.VehicleCategory.FOUR_WHEELER,
            vehicle_type=Vehicle.VehicleType.SEDAN,
            passenger_seats=3,
            private_use_attested=True,
        )

    def upload_document(self, client, document_type, vehicle=None, expiry_date=None, name=None):
        uploaded = make_jpg(name or "driver-photo.jpg") if document_type == "driver_photo" else make_pdf(name or f"{document_type}.pdf")
        payload = {
            "document_type": document_type,
            "file": uploaded,
        }
        if vehicle:
            payload["vehicle"] = str(vehicle.pk)
        if expiry_date:
            payload["expiry_date"] = expiry_date.isoformat()
        return client.post("/api/v1/drivers/documents/", payload, format="multipart")

    def test_passenger_cannot_access_driver_profile(self):
        passenger = self.create_driver(role=User.Role.PASSENGER)
        self.client.force_authenticate(passenger)
        response = self.client.get("/api/v1/drivers/profile/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_driver_profile_is_created_for_verified_driver(self):
        driver = self.create_driver()
        self.assertTrue(driver.is_email_verified)
        self.assertFalse(driver.is_phone_verified)
        self.client.force_authenticate(driver)
        response = self.client.get("/api/v1/drivers/profile/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["verification_status"], "draft")
        self.assertTrue(DriverProfile.objects.filter(user=driver).exists())

    def test_vehicle_registration_is_normalized_and_owned_by_driver(self):
        driver = self.create_driver()
        self.client.force_authenticate(driver)
        response = self.client.post(
            "/api/v1/drivers/vehicles/",
            {
                "registration_number": "tn 01 ab 1234",
                "make": "Honda",
                "model": "City",
                "manufacture_year": 2022,
                "colour": "Blue",
                "vehicle_category": "four_wheeler",
                "vehicle_type": "sedan",
                "passenger_seats": 3,
                "private_use_attested": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["registration_number"], "TN01AB1234")
        self.assertEqual(response.data["vehicle_category"], "four_wheeler")
        self.assertEqual(Vehicle.objects.get(pk=response.data["id"]).owner, driver)

    def test_vehicle_requires_private_use_attestation(self):
        driver = self.create_driver()
        self.client.force_authenticate(driver)
        response = self.client.post(
            "/api/v1/drivers/vehicles/",
            {
                "registration_number": "TN01AB1234",
                "make": "Honda",
                "model": "City",
                "manufacture_year": 2022,
                "vehicle_type": "sedan",
                "passenger_seats": 3,
                "private_use_attested": False,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_document_upload_is_private_and_metadata_is_returned(self):
        driver = self.create_driver()
        self.client.force_authenticate(driver)
        response = self.upload_document(
            self.client,
            VerificationDocument.DocumentType.DRIVER_LICENSE,
            expiry_date=date.today() + timedelta(days=365),
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        document = VerificationDocument.objects.get(pk=response.data["id"])
        self.assertTrue(document.file.name.startswith("private/driver-verification/"))
        self.assertNotIn("file", response.data)
        self.assertTrue(response.data["download_url"].endswith(f"/{document.pk}/download/"))

    def test_document_upload_rejects_extension_and_signature_mismatch(self):
        driver = self.create_driver()
        self.client.force_authenticate(driver)
        response = self.upload_document(
            self.client,
            VerificationDocument.DocumentType.DRIVER_LICENSE,
            name="not-a-pdf.pdf",
        )
        # The helper supplies a valid PDF. Now send a spoofed PDF signature.
        response = self.client.post(
            "/api/v1/drivers/documents/",
            {
                "document_type": "driver_license",
                "file": make_pdf(content=b"this is not a PDF"),
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_document_cannot_be_downloaded_by_another_user(self):
        driver = self.create_driver()
        other = self.create_driver(email="other@example.com", phone="+919876543211")
        self.client.force_authenticate(driver)
        uploaded = self.upload_document(self.client, "driver_license")
        self.assertEqual(uploaded.status_code, status.HTTP_201_CREATED)

        document = VerificationDocument.objects.get(pk=uploaded.data["id"])
        self.client.force_authenticate(other)
        response = self.client.get(reverse("driver-document-download", kwargs={"document_id": document.pk}))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_admin_can_download_document(self):
        driver = self.create_driver()
        admin = User.objects.create_superuser(
            email="admin@example.com",
            phone="+919876543299",
            password="A-Strong-Unique-Password-928!",
        )
        self.assertEqual(admin.role, User.Role.ADMIN)
        self.client.force_authenticate(driver)
        uploaded = self.upload_document(self.client, "driver_license")
        document = VerificationDocument.objects.get(pk=uploaded.data["id"])
        self.client.force_authenticate(admin)
        response = self.client.get(reverse("driver-document-download", kwargs={"document_id": document.pk}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")
        response.close()

    def test_submission_reports_missing_required_documents(self):
        driver = self.create_driver()
        vehicle = self.create_vehicle(driver)
        self.client.force_authenticate(driver)
        response = self.client.post(
            "/api/v1/drivers/verification/submit/",
            {"vehicle_id": vehicle.pk},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(len(response.data["missing_documents"]), 4)

    def test_documents_must_be_admin_approved_before_driver_is_approved(self):
        driver = self.create_driver()
        vehicle = self.create_vehicle(driver)
        admin = User.objects.create_superuser(
            email="reviewer@example.com",
            phone="+919876543298",
            password="A-Strong-Unique-Password-928!",
        )
        self.client.force_authenticate(driver)
        uploads = [
            self.upload_document(self.client, "driver_license"),
            self.upload_document(self.client, "driver_photo"),
            self.upload_document(self.client, "vehicle_registration", vehicle),
            self.upload_document(self.client, "insurance", vehicle, date.today() + timedelta(days=365)),
        ]
        self.assertTrue(all(item.status_code == status.HTTP_201_CREATED for item in uploads))

        submitted = self.client.post(
            "/api/v1/drivers/verification/submit/",
            {"vehicle_id": vehicle.pk},
            format="json",
        )
        self.assertEqual(submitted.status_code, status.HTTP_200_OK)
        self.assertEqual(submitted.data["driver_status"], "pending")
        self.assertEqual(submitted.data["vehicle_status"], "pending")

        self.client.force_authenticate(admin)
        for upload in uploads:
            reviewed = self.client.post(
                f"/api/v1/drivers/admin/verification/documents/{upload.data['id']}/review/",
                {"decision": "approved"},
                format="json",
            )
            self.assertEqual(reviewed.status_code, status.HTTP_200_OK)

        vehicle.refresh_from_db()
        profile = DriverProfile.objects.get(user=driver)
        self.assertEqual(vehicle.verification_status, Vehicle.VerificationStatus.APPROVED)
        self.assertEqual(profile.verification_status, DriverProfile.VerificationStatus.APPROVED)

        # Editing the vehicle invalidates the existing approvals for that vehicle.
        self.client.force_authenticate(driver)
        edited = self.client.patch(
            f"/api/v1/drivers/vehicles/{vehicle.pk}/",
            {"model": "Civic"},
            format="json",
        )
        self.assertEqual(edited.status_code, status.HTTP_200_OK)
        vehicle.refresh_from_db()
        profile.refresh_from_db()
        self.assertEqual(vehicle.verification_status, Vehicle.VerificationStatus.PENDING)
        self.assertEqual(profile.verification_status, DriverProfile.VerificationStatus.PENDING)
        self.assertTrue(VerificationDocument.objects.filter(
            vehicle=vehicle,
            is_current=True,
            review_status=VerificationDocument.ReviewStatus.PENDING,
        ).exists())

    def test_two_wheeler_category_limits_passenger_capacity_to_one(self):
        driver = self.create_driver()
        self.client.force_authenticate(driver)
        payload = {
            "registration_number": "TN57AC1314",
            "make": "Royal Enfield",
            "model": "Classic 350",
            "manufacture_year": 2018,
            "vehicle_category": "two_wheeler",
            "vehicle_type": "motorcycle",
            "passenger_seats": 2,
            "private_use_attested": True,
        }
        invalid = self.client.post("/api/v1/drivers/vehicles/", payload, format="json")
        self.assertEqual(invalid.status_code, status.HTTP_400_BAD_REQUEST)

        payload["passenger_seats"] = 1
        valid = self.client.post("/api/v1/drivers/vehicles/", payload, format="json")
        self.assertEqual(valid.status_code, status.HTTP_201_CREATED)
        self.assertEqual(valid.data["vehicle_category"], "two_wheeler")
        self.assertEqual(valid.data["vehicle_type"], "motorcycle")

    def test_each_uploaded_driver_document_can_be_reviewed_independently(self):
        driver = self.create_driver()
        admin = User.objects.create_superuser(
            email="partial-reviewer@example.com",
            phone="+919876543296",
            password="A-Strong-Unique-Password-928!",
        )
        self.client.force_authenticate(driver)
        uploaded = self.upload_document(self.client, "driver_license")
        self.assertEqual(uploaded.status_code, status.HTTP_201_CREATED)

        profile = DriverProfile.objects.get(user=driver)
        self.assertEqual(profile.verification_status, DriverProfile.VerificationStatus.PENDING)

        self.client.force_authenticate(admin)
        queue = self.client.get("/api/v1/drivers/admin/verification/queue/")
        self.assertEqual(queue.status_code, status.HTTP_200_OK)
        self.assertEqual(len(queue.data), 1)
        self.assertEqual(queue.data[0]["document_type"], "driver_license")

        reviewed = self.client.post(
            f"/api/v1/drivers/admin/verification/documents/{uploaded.data['id']}/review/",
            {"decision": "approved"},
            format="json",
        )
        self.assertEqual(reviewed.status_code, status.HTTP_200_OK)
        document = VerificationDocument.objects.get(pk=uploaded.data["id"])
        self.assertEqual(document.review_status, VerificationDocument.ReviewStatus.APPROVED)
        profile.refresh_from_db()
        self.assertEqual(profile.verification_status, DriverProfile.VerificationStatus.PENDING)
        self.assertFalse(VerificationDocument.objects.filter(
            owner=driver,
            document_type=VerificationDocument.DocumentType.VEHICLE_REGISTRATION,
            is_current=True,
        ).exists())

    def test_document_rejection_requires_a_reason(self):
        driver = self.create_driver()
        admin = User.objects.create_superuser(
            email="admin2@example.com",
            phone="+919876543297",
            password="A-Strong-Unique-Password-928!",
        )
        self.client.force_authenticate(driver)
        uploaded = self.upload_document(self.client, "driver_license")
        self.client.force_authenticate(admin)
        response = self.client.post(
            f"/api/v1/drivers/admin/verification/documents/{uploaded.data['id']}/review/",
            {"decision": "rejected", "review_note": ""},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_existing_driver_without_mobile_can_open_profile_and_add_one(self):
        driver = User.objects.create_user(
            email="legacy-driver@example.com",
            phone=None,
            password="A-Strong-Unique-Password-928!",
            role=User.Role.DRIVER,
            is_email_verified=True,
        )
        self.client.force_authenticate(driver)
        profile = self.client.get("/api/v1/drivers/profile/")
        self.assertEqual(profile.status_code, status.HTTP_200_OK)
        self.assertFalse(profile.data["contact_phone"])

        updated = self.client.patch(
            "/api/v1/drivers/profile/",
            {"contact_phone": "+919876543260"},
            format="json",
        )
        self.assertEqual(updated.status_code, status.HTTP_200_OK)
        driver.refresh_from_db()
        self.assertEqual(driver.phone, "+919876543260")

    @override_settings(PRIVATE_MEDIA_STORAGE_READY=False)
    def test_driver_document_upload_is_blocked_without_private_storage(self):
        driver = self.create_driver()
        self.client.force_authenticate(driver)
        response = self.client.post(
            "/api/v1/drivers/documents/",
            {"document_type": "driver_license", "file": make_pdf()},
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertFalse(VerificationDocument.objects.filter(owner=driver).exists())

    def test_driver_face_photo_accepts_only_jpeg_or_png(self):
        driver = self.create_driver()
        self.client.force_authenticate(driver)
        response = self.client.post(
            "/api/v1/drivers/documents/",
            {"document_type": "driver_photo", "file": make_pdf()},
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(VerificationDocument.objects.filter(owner=driver).exists())

    def test_unverified_driver_cannot_upload_documents(self):
        driver = User.objects.create_user(
            email="unverified@example.com",
            phone="+919876543212",
            password="A-Strong-Unique-Password-928!",
            role=User.Role.DRIVER,
        )
        self.client.force_authenticate(driver)
        response = self.client.get("/api/v1/drivers/documents/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
