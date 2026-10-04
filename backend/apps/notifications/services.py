from datetime import timedelta
from email.utils import format_datetime
from urllib.parse import urlencode

from django.conf import settings
from django.core.mail import EmailMessage
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from .models import Notification, OutboxEvent


def enqueue(kind, aggregate_id, *, key, **payload):
    return OutboxEvent.objects.get_or_create(
        deduplication_key=key,
        defaults={
            "event_type": kind,
            "aggregate_id": aggregate_id,
            "payload_redacted": {field: str(value) for field, value in payload.items()},
        },
    )[0]


def render_message(event):
    from apps.accounts.models import User
    from apps.accounts.services import make_verification_token
    from apps.orders.models import Order
    from apps.organizations.models import Invitation
    from apps.organizations.services import invitation_secret
    from apps.payments.models import Refund

    base = settings.APP_BASE_URL.rstrip("/")
    if event.event_type in ["account.verify", "account.reset"]:
        user = User.objects.get(pk=event.aggregate_id)
        if event.event_type == "account.verify":
            token = make_verification_token(user)
            subject = "Verify your Ticket email"
            body = f"Verify your email at {base}/account?{urlencode({'verify': token})}\n\nToken:\n{token}"
        else:
            from django.contrib.auth.tokens import default_token_generator
            from django.utils.encoding import force_bytes
            from django.utils.http import urlsafe_base64_encode

            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            subject = "Reset your Ticket password"
            body = f"Reset your password at {base}/account?{urlencode({'uid': uid, 'reset': token})}\n\nUID: {uid}\nToken: {token}"
        return user, user.email, subject, body
    if event.event_type == "team.invite":
        invitation = Invitation.objects.select_related("organization").get(pk=event.aggregate_id)
        token = invitation_secret(invitation)
        subject = "Invitation to Ticket"
        body = f"Join {invitation.organization.name} at {base}/account?{urlencode({'invitation': token})}\n\nToken:\n{token}"
        return None, invitation.email, subject, body
    if event.event_type == "order.refund":
        refund = Refund.objects.select_related("order__user", "order__event").get(pk=event.aggregate_id)
        order = refund.order
        subject = "Your simulated refund is complete"
        body = f"Refund: {refund.amount_minor} minor units {refund.currency}, order {order.public_reference}. View your account at {base}/account."
    else:
        order = Order.objects.select_related("user", "event").get(pk=event.aggregate_id)
        subject = {
            "order.paid": "Your Ticket admission is ready",
            "event.cancelled": "Your event has been cancelled",
            "event.reminder": "Your event starts tomorrow",
        }[event.event_type]
        body = f"{order.event.title}\nOrder {order.public_reference}\nView your tickets at {base}/account.\nSynthetic event; all payments and refunds are simulated."
    return order.user, order.user.email, subject, body


def process_outbox(limit=100):
    processed = 0
    for _index in range(limit):
        with transaction.atomic():
            now = timezone.now()
            event = (
                OutboxEvent.objects.select_for_update(skip_locked=True)
                .filter(published_at__isnull=True, failed_at__isnull=True, next_attempt_at__lte=now)
                .filter(Q(lease_until__isnull=True) | Q(lease_until__lte=now))
                .order_by("created_at")
                .first()
            )
            if not event:
                break
            event.attempts += 1
            event.lease_until = now + timedelta(minutes=2)
            event.save(update_fields=["attempts", "lease_until"])
        try:
            user, email, subject, body = render_message(event)
            # Sensitive verification/reset tokens never enter the notification inbox.
            if user and not event.event_type.startswith("account."):
                Notification.objects.get_or_create(
                    outbox=event, defaults={"user": user, "kind": event.event_type, "subject": subject, "body": body}
                )
            message = EmailMessage(
                subject,
                body,
                settings.DEFAULT_FROM_EMAIL,
                [email],
                headers={"Message-ID": f"<{event.pk}@ticket.local>", "Date": format_datetime(event.created_at)},
            )
            message.send(fail_silently=False)
        except Exception:
            event.lease_until = None
            event.next_attempt_at = timezone.now() + timedelta(seconds=min(3600, 2**event.attempts * 5))
            if event.attempts >= 8:
                event.failed_at = timezone.now()
            event.save(update_fields=["lease_until", "next_attempt_at", "failed_at"])
        else:
            event.published_at = timezone.now()
            event.lease_until = None
            event.save(update_fields=["published_at", "lease_until"])
            processed += 1
    return processed


def enqueue_reminders():
    from apps.orders.models import Order

    now = timezone.now()
    for order in Order.objects.filter(
        status__in=["PAID", "PARTIALLY_REFUNDED"],
        event__status="PUBLISHED",
        event__start_at__gte=now + timedelta(hours=23),
        event__start_at__lt=now + timedelta(hours=25),
    ):
        enqueue("event.reminder", order.pk, key=f"reminder:{order.pk}")
