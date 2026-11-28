import hashlib
import hmac
import secrets
from decimal import Decimal

import requests
from django.conf import settings
from django.utils import timezone

RAZORPAY_API_BASE = "https://api.razorpay.com/v1"


class RazorpayNotConfigured(Exception):
    pass


class RazorpayGatewayError(Exception):
    pass


def _credentials():
    key_id = getattr(settings, "RAZORPAY_KEY_ID", "").strip()
    key_secret = getattr(settings, "RAZORPAY_KEY_SECRET", "")
    if not getattr(settings, "RAZORPAY_TEST_MODE", True) or not key_id.startswith("rzp_test_") or not key_secret:
        raise RazorpayNotConfigured(
            "Razorpay Test Mode is not configured. Add an rzp_test_ key ID and matching secret in Render."
        )
    return key_id, key_secret


def _request(method, path, *, payload=None):
    key_id, key_secret = _credentials()
    try:
        response = requests.request(
            method, f"{RAZORPAY_API_BASE}{path}", json=payload,
            auth=(key_id, key_secret), timeout=(5, 20),
        )
    except requests.RequestException as exc:
        raise RazorpayGatewayError("Could not reach Razorpay. Please retry.") from exc
    try:
        data = response.json()
    except ValueError as exc:
        raise RazorpayGatewayError("Razorpay returned an unreadable response.") from exc
    if not response.ok:
        detail = (data.get("error") or {}).get("description") or "Razorpay rejected the request."
        raise RazorpayGatewayError(str(detail)[:300])
    return data


def create_order(*, contribution):
    """Create an order from the server-calculated contribution amount."""
    _credentials()
    amount_paise = int((Decimal(contribution.total_amount) * 100).to_integral_exact())
    if amount_paise <= 0:
        raise RazorpayGatewayError("The contribution amount must be greater than zero.")
    receipt = f"WT{contribution.pk}-{secrets.token_hex(8)}"
    order = _request("POST", "/orders", payload={
        "amount": amount_paise,
        "currency": contribution.currency,
        "receipt": receipt,
        "notes": {
            "waytogether_contribution_id": str(contribution.pk),
            "waytogether_journey_id": str(contribution.booking.journey_id),
        },
    })
    if not order.get("id") or int(order.get("amount", -1)) != amount_paise or order.get("currency") != contribution.currency:
        raise RazorpayGatewayError("Razorpay returned an order that does not match the contribution.")
    return order


def verify_checkout_signature(*, order_id, payment_id, signature):
    _, key_secret = _credentials()
    expected = hmac.new(
        key_secret.encode("utf-8"),
        f"{order_id}|{payment_id}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


def fetch_payment(payment_id):
    return _request("GET", f"/payments/{payment_id}")


def capture_payment(payment_id, amount_paise):
    return _request("POST", f"/payments/{payment_id}/capture", payload={"amount": amount_paise})


def verify_and_capture_payment(*, local_payment, gateway_payment_id, signature):
    if local_payment.status == "captured":
        return local_payment
    if not verify_checkout_signature(
        order_id=local_payment.order_id, payment_id=gateway_payment_id, signature=signature
    ):
        raise RazorpayGatewayError("Razorpay payment signature verification failed.")

    gateway_payment = fetch_payment(gateway_payment_id)
    expected_paise = int((Decimal(local_payment.amount) * 100).to_integral_exact())
    if (
        gateway_payment.get("order_id") != local_payment.order_id
        or int(gateway_payment.get("amount", -1)) != expected_paise
        or gateway_payment.get("currency") != local_payment.currency
    ):
        raise RazorpayGatewayError("The Razorpay payment does not match this contribution.")

    provider_status = gateway_payment.get("status")
    if provider_status == "authorized":
        gateway_payment = capture_payment(gateway_payment_id, expected_paise)
        provider_status = gateway_payment.get("status")

    if provider_status != "captured":
        if provider_status == "failed":
            local_payment.status = "failed"
            local_payment.payment_id = gateway_payment_id
            local_payment.failure_reason = "Razorpay reported that the payment failed."
            local_payment.save(update_fields=["status", "payment_id", "failure_reason", "updated_at"])
        raise RazorpayGatewayError(
            "Razorpay has not confirmed a captured payment. Check the Test Mode payment status and retry if needed."
        )

    local_payment.payment_id = gateway_payment_id
    local_payment.status = "captured"
    local_payment.failure_reason = ""
    local_payment.completed_at = timezone.now()
    local_payment.save(update_fields=[
        "payment_id", "status", "failure_reason", "completed_at", "updated_at"
    ])
    return local_payment
