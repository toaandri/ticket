import hashlib
import json
import uuid

from django.db import models
from rest_framework.exceptions import APIException, PermissionDenied, ValidationError


class Conflict(APIException):
    status_code = 409
    default_code = "conflict"
    default_detail = "The resource is no longer available."


class Entity(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True


def require_role(user, organization_id, roles=("OWNER", "MANAGER", "EDITOR")):
    from apps.organizations.models import Membership

    member = Membership.objects.filter(user=user, organization_id=organization_id).first()
    if not member or member.role not in roles:
        raise PermissionDenied("Your organization role does not permit this action.")
    return member


def fingerprint(payload):
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def idempotency_key(request):
    key = request.headers.get("Idempotency-Key", "")
    if not key or len(key) > 128:
        raise ValidationError({"Idempotency-Key": "Provide a unique key of at most 128 characters."})
    return key


def replay(existing, digest):
    if existing and existing.fingerprint != digest:
        raise Conflict("This idempotency key was used with a different request.")
    return existing
