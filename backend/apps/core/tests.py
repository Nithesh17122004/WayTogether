from rest_framework.test import APITestCase

from apps.accounts.models import User


class HealthCheckTests(APITestCase):
    def test_health_endpoint_is_public_and_returns_service_status(self):
        response = self.client.get("/api/v1/health/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "ok")
        self.assertEqual(response.data["service"], "waytogether-api")


class AdminWorkspaceAPITests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            email="admin@example.com",
            phone="+919900000001",
            password="StrongTestPass123!",
            first_name="Platform",
            last_name="Admin",
            is_staff=True,
            is_superuser=True,
            role=User.Role.ADMIN,
            is_email_verified=True,
            is_phone_verified=True,
        )
        self.passenger = User.objects.create_user(
            email="passenger@example.com",
            phone="+919900000002",
            password="StrongTestPass123!",
            first_name="Test",
            last_name="Passenger",
        )

    def test_admin_can_read_platform_overview(self):
        self.client.force_authenticate(self.admin)

        response = self.client.get("/api/v1/admin/overview/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["users"]["total"], 2)
        self.assertEqual(response.data["users"]["by_role"]["admin"], 1)
        self.assertIn("expense_sharing", response.data)
        self.assertEqual(response.data["expense_sharing"]["sandbox_payment_attempts"], 0)

    def test_non_staff_user_cannot_read_admin_endpoints(self):
        self.client.force_authenticate(self.passenger)

        for path in (
            "/api/v1/admin/overview/",
            "/api/v1/admin/users/",
            "/api/v1/admin/journeys/",
            "/api/v1/admin/bookings/",
            "/api/v1/admin/expense-ledger/",
        ):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 403)

    def test_admin_user_search_is_filtered_and_does_not_expose_phone(self):
        self.client.force_authenticate(self.admin)

        response = self.client.get("/api/v1/admin/users/?q=Passenger&role=passenger")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["total_count"], 1)
        self.assertEqual(response.data["results"][0]["email"], self.passenger.email)
        self.assertNotIn("phone", response.data["results"][0])

    def test_expense_ledger_is_read_only_and_returns_an_empty_collection(self):
        self.client.force_authenticate(self.admin)

        response = self.client.get("/api/v1/admin/expense-ledger/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["total_count"], 0)
        self.assertIn("does not indicate money collected", response.data["notice"])
