import re
from datetime import timedelta
from django.contrib.auth.hashers import make_password
from django.core import mail
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APITestCase
from unittest.mock import Mock, patch

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

    def test_register_sends_only_email_code_and_phone_is_optional(self):
        response = self.client.post(
            "/api/v1/auth/register/",
            self.registration_payload(phone=None),
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertTrue(response.data["email_verification_required"])
        user = User.objects.get(email="kamaresh@example.com")
        self.assertIsNone(user.phone)
        self.assertFalse(user.is_email_verified)
        self.assertFalse(user.is_phone_verified)
        self.assertEqual(response.data["verification"]["email"], "sent")
        self.assertNotIn("phone", response.data["verification"])
        self.assertEqual(len(mail.outbox), 1)

        email_match = re.search(r"code is (\d{6})", mail.outbox[0].body)
        self.assertIsNotNone(email_match)
        email_result = self.client.post(
            "/api/v1/auth/verification/confirm/",
            {"email": user.email, "code": email_match.group(1)},
            format="json",
        )
        self.assertEqual(email_result.status_code, 200)
        self.assertTrue(email_result.data["can_sign_in"])
        user.refresh_from_db()
        self.assertTrue(user.is_email_verified)
        self.assertFalse(user.is_phone_verified)

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

    def test_login_is_allowed_before_email_verification_but_account_remains_unverified(self):
        user = User.objects.create_user(
            email="kamaresh@example.com",
            phone="+919876543210",
            password="A-Strong-Unique-Password-928!",
        )
        response = self.client.post(
            "/api/v1/auth/login/",
            {"email": user.email, "password": "A-Strong-Unique-Password-928!"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertFalse(response.data["user"]["is_email_verified"])

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
        profile = self.client.get("/api/v1/auth/me/")
        self.assertEqual(profile.status_code, 200)
        self.assertFalse(profile.data["is_email_verified"])
        user.refresh_from_db()
        self.assertFalse(user.is_email_verified)

    def test_login_returns_tokens_and_profile_after_verification(self):
        user = User.objects.create_user(
            email="kamaresh@example.com",
            phone="+919876543210",
            password="A-Strong-Unique-Password-928!",
            role=User.Role.DRIVER,
            is_email_verified=True,
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

    def test_logout_blacklists_refresh_token_and_refresh_cannot_reuse_it(self):
        user = User.objects.create_user(
            email="logout@example.com",
            phone="+919876543219",
            password="A-Strong-Unique-Password-928!",
            is_email_verified=True,
        )
        login = self.client.post(
            "/api/v1/auth/login/",
            {"email": user.email, "password": "A-Strong-Unique-Password-928!"},
            format="json",
        )
        self.assertEqual(login.status_code, 200)

        logout = self.client.post(
            "/api/v1/auth/token/blacklist/",
            {"refresh": login.data["refresh"]},
            format="json",
        )
        self.assertEqual(logout.status_code, 200)

        refresh = self.client.post(
            "/api/v1/auth/token/refresh/",
            {"refresh": login.data["refresh"]},
            format="json",
        )
        self.assertEqual(refresh.status_code, 401)

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
            code_hash=make_password("111111"),
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

    @override_settings(DEBUG=False, SMS_OTP_CONSOLE=True)
    def test_phone_otp_is_not_supported(self):
        with self.assertRaises(ValueError):
            issue_verification_code(self.user, VerificationCode.Channel.PHONE)
        self.assertFalse(
            VerificationCode.objects.filter(user=self.user, channel=VerificationCode.Channel.PHONE).exists()
        )

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_otp_is_stored_as_hash_and_resend_has_cooldown(self):
        issue_verification_code(self.user, VerificationCode.Channel.EMAIL)
        record = VerificationCode.objects.get(user=self.user, channel="email")
        self.assertNotEqual(record.code_hash, "000000")
        with self.assertRaises(ValueError):
            issue_verification_code(self.user, VerificationCode.Channel.EMAIL)



@override_settings(
    EMAIL_PROVIDER="resend",
    RESEND_API_KEY="re_test_waytogether",
    RESEND_FROM_EMAIL="WayTogether <no-reply@waytogether.aclclouds.online>",
)
class ResendEmailDeliveryTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="resend-recipient@example.com",
            password="A-Strong-Unique-Password-928!",
        )

    @patch("apps.accounts.services.requests.post")
    def test_verification_email_uses_resend_https_api(self, post):
        response = Mock()
        response.raise_for_status = Mock()
        post.return_value = response

        record = issue_verification_code(self.user, VerificationCode.Channel.EMAIL)

        self.assertIsNotNone(record)
        post.assert_called_once()
        args, kwargs = post.call_args
        self.assertEqual(args[0], "https://api.resend.com/emails")
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer re_test_waytogether")
        self.assertEqual(kwargs["json"]["from"], "WayTogether <no-reply@waytogether.aclclouds.online>")
        self.assertEqual(kwargs["json"]["to"], [self.user.email])
        self.assertIn("verification code is", kwargs["json"]["text"])
        self.assertEqual(kwargs["timeout"], (5, 20))

    @patch("apps.accounts.services.requests.post")
    def test_failed_resend_request_removes_unusable_otp_record(self, post):
        import requests
        post.side_effect = requests.Timeout("test timeout")

        with self.assertRaises(requests.Timeout):
            issue_verification_code(self.user, VerificationCode.Channel.EMAIL)

        self.assertFalse(
            VerificationCode.objects.filter(
                user=self.user,
                channel=VerificationCode.Channel.EMAIL,
                verified_at__isnull=True,
            ).exists()
        )
