"""Optional hosted Stripe TEST checkout; no card data passes through Ticket."""

import hashlib
import hmac
import json
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings
from rest_framework.exceptions import APIException, PermissionDenied, ValidationError

from .base import PaymentResult


class ProviderUnavailable(APIException):
    status_code = 503
    default_detail = "The test payment provider is temporarily unavailable. Retry with the same key."


class StripeTestPaymentProvider:
    def __init__(self):
        if not settings.STRIPE_ENABLED or not settings.STRIPE_SECRET_KEY.startswith("sk_test_"):
            raise ValidationError("Stripe test checkout is disabled. Use the mock provider.")

    def request(self, method, path, data=None, key=""):
        headers = {"Authorization": f"Bearer {settings.STRIPE_SECRET_KEY}", "Stripe-Version": "2024-06-20"}
        if key:
            headers["Idempotency-Key"] = key
        body = urlencode(data).encode() if data is not None else None
        if body:
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        request = Request(f"https://api.stripe.com/v1/{path}", data=body, headers=headers, method=method)
        try:
            with urlopen(request, timeout=15) as response:
                result = json.load(response)
        except (HTTPError, URLError, TimeoutError, ValueError) as exc:
            raise ProviderUnavailable() from exc
        if not isinstance(result, dict):
            raise ProviderUnavailable()
        if result.get("livemode") is True:
            raise PermissionDenied("Live Stripe responses are never accepted.")
        return result

    def create_payment(self, payment, scenario="success"):
        result = self.request(
            "POST",
            "checkout/sessions",
            {
                "mode": "payment",
                "client_reference_id": str(payment.pk),
                "metadata[ticket_payment_id]": str(payment.pk),
                "payment_intent_data[metadata][ticket_payment_id]": str(payment.pk),
                "line_items[0][price_data][currency]": payment.currency.lower(),
                "line_items[0][price_data][unit_amount]": payment.amount_minor,
                "line_items[0][price_data][product_data][name]": f"TEST ONLY — {payment.order.event.title}",
                "line_items[0][quantity]": 1,
                "success_url": f"{settings.APP_BASE_URL.rstrip('/')}/account?checkout=returned",
                "cancel_url": f"{settings.APP_BASE_URL.rstrip('/')}/account?checkout=cancelled",
            },
            key=str(payment.pk),
        )
        return PaymentResult(result["id"], "PENDING", result["url"])

    def fetch_status(self, payment):
        session = self.request("GET", f"checkout/sessions/{payment.provider_payment_id}")
        if (
            session.get("id") != payment.provider_payment_id
            or session.get("client_reference_id") != str(payment.pk)
            or session.get("livemode") is not False
            or session.get("amount_total") != payment.amount_minor
            or str(session.get("currency", "")).upper() != payment.currency
        ):
            raise PermissionDenied("Test payment response does not match its immutable order.")
        if session.get("payment_status") == "paid":
            payment.payment_intent_id = session.get("payment_intent") or ""
            payment.save(update_fields=["payment_intent_id"])
            return "SUCCEEDED"
        return "FAILED" if session.get("status") == "expired" else "PENDING"

    def refund(self, payment, amount, key):
        if not payment.payment_intent_id:
            self.fetch_status(payment)
        if not payment.payment_intent_id:
            raise ProviderUnavailable()
        result = self.request(
            "POST", "refunds", {"payment_intent": payment.payment_intent_id, "amount": amount}, key=key
        )
        if result.get("status") != "succeeded":
            raise ProviderUnavailable()
        return result["id"]

    def verify_webhook(self, signature, body):
        if not settings.STRIPE_WEBHOOK_SECRET:
            raise PermissionDenied("Webhook verification is not configured.")
        values = {}
        try:
            for entry in signature.split(","):
                key, value = entry.split("=", 1)
                values.setdefault(key, []).append(value)
            timestamp = values["t"][0]
            if abs(time.time() - int(timestamp)) > 300:
                raise ValueError("Expired signature")
            expected = hmac.new(
                settings.STRIPE_WEBHOOK_SECRET.encode(), timestamp.encode() + b"." + body, hashlib.sha256
            ).hexdigest()
            if not any(hmac.compare_digest(expected, value) for value in values.get("v1", [])):
                raise ValueError("Signature mismatch")
            event = json.loads(body)
        except (KeyError, ValueError, TypeError) as exc:
            raise PermissionDenied("Invalid Stripe signature.") from exc
        if (
            not isinstance(event, dict)
            or not isinstance(event.get("id"), str)
            or not isinstance(event.get("type"), str)
        ):
            raise PermissionDenied("Invalid Stripe event shape.")
        if event.get("livemode") is not False:
            raise PermissionDenied("Only Stripe test events are accepted.")
        return event
