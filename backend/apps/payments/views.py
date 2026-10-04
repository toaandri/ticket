from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import permissions, serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import PaymentAttempt
from .providers.stripe_test import StripeTestPaymentProvider
from .services import process_payment_event


class WebhookResultSerializer(serializers.Serializer):
    received = serializers.BooleanField()


class StripeWebhookView(APIView):
    permission_classes = (permissions.AllowAny,)
    authentication_classes = ()

    @extend_schema(request=None, responses=WebhookResultSerializer)
    def post(self, request):
        if len(request.body) > 65536:
            from rest_framework.exceptions import ValidationError

            raise ValidationError("Webhook body too large.")
        provider = StripeTestPaymentProvider()
        event = provider.verify_webhook(request.headers.get("Stripe-Signature", ""), request.body)
        if event["type"] in [
            "checkout.session.completed",
            "checkout.session.expired",
            "checkout.session.async_payment_succeeded",
            "checkout.session.async_payment_failed",
        ]:
            session = event.get("data", {}).get("object") if isinstance(event.get("data"), dict) else None
            if not isinstance(session, dict) or not all(key in session for key in ["id", "amount_total", "currency"]):
                from rest_framework.exceptions import ValidationError

                raise ValidationError("Invalid checkout session payload.")
            payment = get_object_or_404(PaymentAttempt, provider="STRIPE_TEST", provider_payment_id=session["id"])
            if session.get("client_reference_id") != str(payment.pk) or session.get("livemode") is not False:
                from rest_framework.exceptions import PermissionDenied

                raise PermissionDenied("Invalid test payment linkage.")
            status = (
                "SUCCEEDED"
                if session.get("payment_status") == "paid"
                else "FAILED"
                if event["type"] in ["checkout.session.expired", "checkout.session.async_payment_failed"]
                else "PENDING"
            )
            process_payment_event(
                payment_id=payment.pk,
                provider_event_id=event["id"],
                status=status,
                amount=session["amount_total"],
                currency=session["currency"],
                payment_intent_id=session.get("payment_intent") or "",
            )
        return Response({"received": True})
