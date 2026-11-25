import re
from datetime import timedelta
from django.core import mail
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from .models import User, VerificationCode
from .services import issue_verification_code, verify_code


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    SMS_OTP_CONSOLE=True,
    DEBUG=True,
)
class RegistrationAndVerificationTests(APITestCase):
    def registration_payload(self, **overrides):
        payload = {
            "full_name": "Kamaresh Example",
            "email": "kamaresh@example.com",
            "phone": "+919876543210",
            "password": "A-Strong-Unique-Password-928!",
            "role": "passenger",
            "accepted_terms": True,
        }
        payload.update(overrides)
        return payload

    def test_register_sends_email_code_and_logs_phone_code_only_in_development(self):
        with self.assertLogs("apps.accounts.services", level="WARNING") as captured:
            response = self.client.post(
                "/api/v1/auth/register/",
                self.registration_payload(),
                format="json",
            )

        self.assertEqual(response.status_code, 201)
        user = User.objects.get(email="kamaresh@example.com")
        self.assertFalse(user.is_email_verified)
        self.assertFalse(user.is_phone_verified)
        self.assertEqual(response.data["verification"]["email"], "sent")
        self.assertEqual(response.data["verification"]["phone"], "sent")
        self.assertEqual(len(mail.outbox), 1)
        email_match = re.search(r"code is (\d{6})", mail.outbox[0].body)
        phone_match = re.search(r"phone OTP for \+919876543210: (\d{6})", "\n".join(captured.output))
        self.assertIsNotNone(email_match)
        self.assertIsNotNone(phone_match)

        email_result = self.client.post(
            "/api/v1/auth/verification/confirm/",
            {"email": user.email, "channel": "email", "code": email_match.group(1)},
            format="json",
        )
        phone_result = self.client.post(
            "/api/v1/auth/verification/confirm/",
            {"email": user.email, "channel": "phone", "code": phone_match.group(1)},
            format="json",
        )
        self.assertEqual(email_result.status_code, 200)
        self.assertEqual(phone_result.status_code, 200)
        user.refresh_from_db()
        self.assertTrue(user.is_email_verified)
        self.assertTrue(user.is_phone_verified)
        self.assertTrue(phone_result.data["can_sign_in"])

    def test_registration_requires_terms_acceptance(self):
        response = self.client.post(
            "/api/v1/auth/register/",
            self.registration_payload(accepted_terms=False),
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(User.objects.exists())

    def test_registration_rejects_duplicate_email_and_phone(self):
        User.objects.create_user(
            email="kamaresh@example.com",
            phone="+919876543210",
            password="A-Strong-Unique-Password-928!",
        )
        duplicate_email = self.client.post(
            "/api/v1/auth/register/",
            self.registration_payload(phone="+919876543211"),
            format="json",
        )
        duplicate_phone = self.client.post(
            "/api/v1/auth/register/",
            self.registration_payload(email="other@example.com"),
            format="json",
        )
        self.assertEqual(duplicate_email.status_code, 400)
        self.assertEqual(duplicate_phone.status_code, 400)

    def test_login_is_blocked_until_both_channels_are_verified(self):
        User.objects.create_user(
            email="kamaresh@example.com",
            phone="+919876543210",
            password="A-Strong-Unique-Password-928!",
        )
        response = self.client.post(
            "/api/v1/auth/login/",
            {"email": "kamaresh@example.com", "password": "A-Strong-Unique-Password-928!"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("verification_required", response.data)

    def test_login_returns_tokens_and_profile_after_verification(self):
        user = User.objects.create_user(
            email="kamaresh@example.com",
            phone="+919876543210",
            password="A-Strong-Unique-Password-928!",
            role=User.Role.DRIVER,
            is_email_verified=True,
            is_phone_verified=True,
        )
        response = self.client.post(
            "/api/v1/auth/login/",
            {"email": user.email, "password": "A-Strong-Unique-Password-928!"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertEqual(response.data["user"]["role"], "driver")

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
        profile = self.client.get("/api/v1/auth/me/")
        self.assertEqual(profile.status_code, 200)
        self.assertEqual(profile.data["email"], user.email)

    def test_profile_requires_authentication(self):
        response = self.client.get("/api/v1/auth/me/")
        self.assertEqual(response.status_code, 401)

    def test_incorrect_code_increments_attempts(self):
        user = User.objects.create_user(
            email="kamaresh@example.com",
            phone="+919876543210",
            password="A-Strong-Unique-Password-928!",
        )
        record = VerificationCode.objects.create(
            user=user,
            channel=VerificationCode.Channel.EMAIL,
            code_hash="not-a-valid-hash",
            expires_at=timezone.now() + timedelta(minutes=10),
        )
        valid, _ = verify_code(user, "email", "000000")
        record.refresh_from_db()
        self.assertFalse(valid)
        self.assertEqual(record.attempts, 1)

    def test_expired_code_is_rejected(self):
        user = User.objects.create_user(
            email="kamaresh@example.com",
            phone="+919876543210",
            password="A-Strong-Unique-Password-928!",
        )
        record = VerificationCode.objects.create(
            user=user,
            channel=VerificationCode.Channel.EMAIL,
            code_hash="not-a-valid-hash",
            expires_at=timezone.now() - timedelta(minutes=1),
        )
        valid, message = verify_code(user, "email", "000000")
        self.assertFalse(valid)
        self.assertIn("expired", message)
        record.refresh_from_db()
        self.assertEqual(record.attempts, 0)


class VerificationServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="service@example.com",
            phone="+919876543211",
            password="A-Strong-Unique-Password-928!",
        )

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_otp_is_stored_as_hash_and_resend_has_cooldown(self):
        issue_verification_code(self.user, VerificationCode.Channel.EMAIL)
        record = VerificationCode.objects.get(user=self.user, channel="email")
        self.assertNotEqual(record.code_hash, "000000")
        with self.assertRaises(ValueError):
            issue_verification_code(self.user, VerificationCode.Channel.EMAIL)
