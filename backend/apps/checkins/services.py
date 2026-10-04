import hashlib
from datetime import timedelta
from urllib.parse import parse_qs, urlparse

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.accounts.models import User
from apps.audit.models import AuditLog
from apps.common.domain import fingerprint, replay, require_role
from apps.events.models import Event
from apps.organizations.models import EventStaffAssignment
from apps.tickets.models import Ticket

from .models import CheckIn


@transaction.atomic
def check_in(*, actor, event_id, token, key, device_id=""):
    if len(token) > 2000:
        raise ValidationError("Invalid QR token.")
    # Lock actor namespace first, then event, then ticket: same ordering as holds.
    User.objects.select_for_update().get(pk=actor.pk)
    event = get_object_or_404(Event.objects.select_for_update(), pk=event_id)
    member = require_role(actor, event.organization_id, ("OWNER", "MANAGER", "SCANNER"))
    if member.role == "SCANNER" and not EventStaffAssignment.objects.filter(event=event, membership=member).exists():
        raise PermissionDenied("You are not assigned to scan this event.")
    if "://" in token:
        token = parse_qs(urlparse(token).query).get("token", [""])[0]
    digest = fingerprint(
        {"event_id": str(event_id), "token_hash": hashlib.sha256(token.encode()).hexdigest(), "device_id": device_id}
    )
    existing = replay(CheckIn.objects.filter(scanned_by=actor, idempotency_key=key).first(), digest)
    if existing:
        return existing
    ticket = Ticket.objects.select_for_update().filter(token_hash=hashlib.sha256(token.encode()).hexdigest()).first()
    if not ticket:
        result = "INVALID"
    elif ticket.event_id != event.pk:
        result = "WRONG_EVENT"
        ticket = None  # Never reveal a foreign ticket identifier in gate responses.
    elif ticket.status == "USED":
        result = "DUPLICATE"
    elif ticket.status != "VALID" or event.status != "PUBLISHED":
        result = "REVOKED"
    elif not event.start_at - timedelta(hours=2) <= timezone.now() <= event.end_at:
        result = "CLOSED"
    else:
        result = "ACCEPTED"
        ticket.status = "USED"
        ticket.used_at = timezone.now()
        ticket.save(update_fields=["status", "used_at"])
    scan = CheckIn.objects.create(
        ticket=ticket,
        event=event,
        scanned_by=actor,
        result=result,
        device_id=device_id,
        idempotency_key=key,
        fingerprint=digest,
    )
    AuditLog.objects.create(
        actor=actor,
        organization_id=event.organization_id,
        action=f"checkin.{result.lower()}",
        entity_type="CheckIn",
        entity_id=scan.pk,
    )
    return scan
