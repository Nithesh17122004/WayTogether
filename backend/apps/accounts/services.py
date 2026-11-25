import logging
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.core.mail import send_mail
from django.utils import timezone

from .models import VerificationCode

logger = logging.getLogger(__name__)
OTP_TTL_MINUTES = 10
OTP_RESEND_SECONDS = 60
OTP_MAX_ATTEMPTS = 5


class OTPDeliveryUnavailable(Exception):
    """Raised when a verification channel has no configured delivery provider."""


def _generate_code():
    return f"{secrets.randbelow(1_000_000):06d}"


def _latest_code(user, channel):
    return VerificationCode.objects.filter(user=user, channel=channel).order_by("-created_at").first()


def issue_verification_code(user, channel):
    if channel not in VerificationCode.Channel.values:
        raise ValueError("Unsupported verification channel.")

    already_verified = (
        user.is_email_verified if channel == VerificationCode.Channel.EMAIL
        else user.is_phone_verified
    )
    if already_verified:
        return None

    previous = _latest_code(user, channel)
    now = timezone.now()
    if previous and previous.created_at > now - timedelta(seconds=OTP_RESEND_SECONDS):
        raise ValueError("Please wait before requesting another verification code.")

    code = _generate_code()
    VerificationCode.objects.filter(
        user=user, channel=channel, verified_at__isnull=True
    ).update(expires_at=now)

    record = VerificationCode.objects.create(
        user=user,
        channel=channel,
        code_hash=make_password(code),
        expires_at=now + timedelta(minutes=OTP_TTL_MINUTES),
    )

    if channel == VerificationCode.Channel.EMAIL:
        send_mail(
            subject="Verify your WayTogether email",
            message=(
                f"Your WayTogether verification code is {code}. "
                f"It expires in {OTP_TTL_MINUTES} minutes. "
                "If you did not request this code, you can ignore this email."
            ),
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
            recipient_list=[user.email],
            fail_silently=False,
        )
    elif getattr(settings, "SMS_OTP_CONSOLE", False) and settings.DEBUG:
        # Local development only. Never expose OTP values through an API response.
        logger.warning("WayTogether development phone OTP for %s: %s", user.phone, code)
    else:
        record.delete()
        raise OTPDeliveryUnavailable(
            "Mobile OTP delivery is not configured. Connect an approved SMS provider before production use."
        )

    return record


def verify_code(user, channel, submitted_code):
    record = _latest_code(user, channel)
    if not record or record.verified_at or record.expires_at <= timezone.now():
        return False, "The verification code is invalid or expired."
    if record.attempts >= OTP_MAX_ATTEMPTS:
        return False, "Too many incorrect attempts. Request a new code."

    if not check_password(submitted_code, record.code_hash):
        record.attempts += 1
        record.save(update_fields=["attempts"])
        return False, "The verification code is incorrect."

    record.verified_at = timezone.now()
    record.save(update_fields=["verified_at"])
    if channel == VerificationCode.Channel.EMAIL:
        user.is_email_verified = True
        user.save(update_fields=["is_email_verified"])
    elif channel == VerificationCode.Channel.PHONE:
        user.is_phone_verified = True
        user.save(update_fields=["is_phone_verified"])
    return True, "Verification completed."
