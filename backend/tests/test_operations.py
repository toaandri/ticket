import csv
from datetime import timedelta
from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import DatabaseError, connection, transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.analytics.services import csv_cell, event_metrics, orders_csv
from apps.events.services import cancel_event, refund_cancelled_events
from apps.inventory.models import InventoryBucket
from apps.inventory.services import reconcile_inventory
from apps.notifications.models import Notification, OutboxEvent
from apps.notifications.services import enqueue, process_outbox
from apps.orders.services import create_order
from apps.organizations.models import Membership, Organization
from apps.payments.services import initiate_payment
from apps.reservations.services import create_hold
from apps.tickets.models import Ticket

pytestmark = pytest.mark.django_db


@pytest.fixture
def paid_demo(inventory_demo):
    owner, _, _, event, ga, _ = inventory_demo
    hold = create_hold(
        actor=owner, event_id=event.pk, items=[{"ticket_type_id": str(ga.pk), "quantity": 2}], key="hold"
    )
    order = create_order(actor=owner, reservation_id=hold.pk, key="order")
    initiate_payment(actor=owner, order_id=order.pk, key="pay")
    return owner, event, ga, order


def test_metrics_refunds_and_readonly_reconciliation(paid_demo):
    owner, event, ga, order = paid_demo
    from apps.payments.services import refund_order

    ticket = Ticket.objects.first()
    refund_order(actor=owner, order_id=order.pk, ticket_ids=[ticket.pk], key="refund", reason="Demo")
    metrics = event_metrics(actor=owner, event=event)
    assert (
        metrics["issued"],
        metrics["active_tickets"],
        metrics["gross_minor"],
        metrics["refunds_minor"],
        metrics["net_minor"],
    ) == (2, 1, 2100, 1050, 1050)
    assert metrics["simulated"]
    assert not reconcile_inventory()
    InventoryBucket.objects.filter(ticket_type=ga).update(held_count=1)
    mismatches = reconcile_inventory()
    assert mismatches[0]["expected_held"] == 0
    assert InventoryBucket.objects.get(ticket_type=ga).held_count == 1


def test_csv_formula_protection_and_timezone_bucketing(paid_demo):
    owner, event, _, _ = paid_demo
    event.title = '  =HYPERLINK("malicious")'
    event.event_timezone = "Pacific/Auckland"
    event.save()
    rows = list(csv.reader(StringIO(orders_csv(actor=owner, event=event))))
    assert rows[1][1].startswith("'")
    assert csv_cell("\t=1+1").startswith("'")
    assert csv_cell("Safe event") == "Safe event"
    assert event_metrics(actor=owner, event=event)["daily_sales"][0]["orders"] == 1


def test_cancellation_refunds_are_resumable_and_release_holds(paid_demo):
    owner, event, ga, _ = paid_demo
    create_hold(actor=owner, event_id=event.pk, items=[{"ticket_type_id": str(ga.pk), "quantity": 1}], key="another")
    cancel_event(actor=owner, event_id=event.pk)
    cancel_event(actor=owner, event_id=event.pk)
    refund_cancelled_events()
    refund_cancelled_events()
    assert Ticket.objects.filter(status="REFUNDED").count() == 2
    assert InventoryBucket.objects.get(ticket_type=ga).held_count == 0
    assert not reconcile_inventory()
    assert OutboxEvent.objects.filter(event_type="event.cancelled").count() == 1


def test_outbox_dedup_retry_and_inapp_exactly_once(paid_demo, mailoutbox, settings, monkeypatch):
    owner, _, _, order = paid_demo
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    event = enqueue("order.paid", order.pk, key=f"paid:{order.pk}")
    assert enqueue("order.paid", order.pk, key=f"paid:{order.pk}").pk == event.pk
    from django.core.mail import EmailMessage

    original = EmailMessage.send

    def fail(*args, **kwargs):
        raise OSError("Synthetic SMTP outage")

    monkeypatch.setattr(EmailMessage, "send", fail)
    assert process_outbox() == 0
    assert Notification.objects.filter(user=owner).count() == 1
    event.refresh_from_db()
    assert event.attempts == 1 and not event.published_at
    assert "token" not in str(event.payload_redacted)
    monkeypatch.setattr(EmailMessage, "send", original)
    OutboxEvent.objects.filter(pk=event.pk).update(next_attempt_at=timezone.now() - timedelta(seconds=1))
    assert process_outbox() == 1
    assert process_outbox() == 0
    assert len(mailoutbox) == 1 and Notification.objects.count() == 1


def test_outbox_rolls_back_with_payment_and_availability_is_postcommit(
    inventory_demo, django_capture_on_commit_callbacks, monkeypatch
):
    owner, _, _, event, ga, _ = inventory_demo
    from unittest.mock import AsyncMock, Mock

    from apps.events import realtime

    layer = Mock(group_send=AsyncMock())
    monkeypatch.setattr(realtime, "get_channel_layer", lambda: layer)
    with django_capture_on_commit_callbacks(execute=True):
        hold = create_hold(
            actor=owner, event_id=event.pk, items=[{"ticket_type_id": str(ga.pk), "quantity": 1}], key="hint"
        )
        assert layer.group_send.call_count == 0
    assert layer.group_send.call_count == 1
    from apps.payments import services

    order = create_order(actor=owner, reservation_id=hold.pk, key="order")

    def fail(_order):
        raise RuntimeError("Synthetic issuance failure")

    monkeypatch.setattr(services, "issue_tickets_locked", fail)
    with pytest.raises(RuntimeError):
        initiate_payment(actor=owner, order_id=order.pk, key="pay")
    order.refresh_from_db()
    assert order.status == "PAYMENT_PROCESSING"
    assert not OutboxEvent.objects.filter(event_type="order.paid").exists()
    assert not Ticket.objects.exists()


def test_scanner_finance_and_cross_org_permissions(paid_demo, auth_client):
    owner, event, _, order = paid_demo
    scanner = User.objects.create_user("scanner@example.com", "example-password-93!")
    Membership.objects.create(user=scanner, organization=event.organization, role="SCANNER")
    client = auth_client(scanner)
    assert client.get(f"/api/v1/events/{event.pk}/metrics/").status_code == 403
    assert client.get(f"/api/v1/events/{event.pk}/export/").status_code == 403
    assert client.get(f"/api/v1/organizations/{event.organization_id}/orders/").status_code == 403
    assert client.get(f"/api/v1/organizations/{event.organization_id}/members/").status_code == 403
    assert (
        client.post(
            f"/api/v1/orders/{order.pk}/refunds/",
            {"ticket_ids": [str(Ticket.objects.first().pk)], "reason": "Unauthorized"},
            format="json",
            HTTP_IDEMPOTENCY_KEY="refund",
        ).status_code
        == 403
    )
    outsider = User.objects.create_superuser("admin@example.com", "example-password-93!")
    assert auth_client(outsider).get(f"/api/v1/events/{event.pk}/metrics/").status_code == 404
    assert auth_client(owner).get("/api/v1/admin/audit/").status_code == 403
    assert auth_client(outsider).get("/api/v1/admin/audit/").status_code == 200


def test_platform_moderation_closes_sales(inventory_demo, auth_client):
    owner, org, _, event, ga, _ = inventory_demo
    admin = User.objects.create_superuser("admin@example.com", "example-password-93!")
    response = auth_client(admin).post(
        f"/api/v1/admin/organizations/{org.pk}/moderate/",
        {"reason": "Synthetic incident", "suspended": True},
        format="json",
    )
    assert response.status_code == 200
    from apps.common.domain import Conflict

    with pytest.raises(Conflict):
        create_hold(
            actor=owner, event_id=event.pk, items=[{"ticket_type_id": str(ga.pk), "quantity": 1}], key="suspended"
        )


def test_database_immutable_audit_and_order_items(paid_demo):
    _, _, _, order = paid_demo
    with pytest.raises(DatabaseError), transaction.atomic(), connection.cursor() as cursor:
        cursor.execute("UPDATE audit_auditlog SET action = 'tampered'")
    with pytest.raises(DatabaseError), transaction.atomic(), connection.cursor() as cursor:
        cursor.execute("UPDATE orders_orderitem SET name = 'tampered'")
    with pytest.raises(DatabaseError), transaction.atomic(), connection.cursor() as cursor:
        cursor.execute("DELETE FROM orders_order WHERE id = %s", [order.pk])


def test_seed_is_idempotent_and_guarded(settings):
    settings.DEBUG = True
    output = StringIO()
    call_command("seed_demo", password="synthetic-demo-password-94!", stdout=output)
    assert Organization.objects.count() == 3
    from apps.events.models import Event

    assert Event.objects.count() == 8
    assert Ticket.objects.count() == 9
    assert not reconcile_inventory()
    call_command("seed_demo", stdout=output)
    assert Event.objects.count() == 8
    assert "No data or passwords changed" in output.getvalue()
    with pytest.raises(CommandError):
        call_command("seed_demo", reset_demo=True)
    settings.DEBUG = False
    with pytest.raises(CommandError):
        call_command("seed_demo")
