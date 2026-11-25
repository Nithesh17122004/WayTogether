from rest_framework.test import APITestCase


class HealthCheckTests(APITestCase):
    def test_health_endpoint_is_public_and_returns_service_status(self):
        response = self.client.get("/api/v1/health/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "ok")
        self.assertEqual(response.data["service"], "waytogether-api")
