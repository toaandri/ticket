from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.common.domain import Entity


class OutboxEvent(Entity):
    event_type = models.CharField(max_length=40)
    aggregate_id = models.UUIDField()
    deduplication_key = models.CharField(max_length=200, unique=True)
    payload_redacted = models.JSONField(default=dict)
    published_at = models.DateTimeField(null=True)
    attempts = models.PositiveIntegerField(default=0)
    next_attempt_at = models.DateTimeField(default=timezone.now, db_index=True)
    lease_until = models.DateTimeField(null=True)
    failed_at = models.DateTimeField(null=True)


class Notification(Entity):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="notifications")
    outbox = models.OneToOneField(OutboxEvent, on_delete=models.PROTECT)
    kind = models.CharField(max_length=40)
    subject = models.CharField(max_length=200)
    body = models.TextField()
    read_at = models.DateTimeField(null=True)

    class Meta:
        ordering = ("-created_at", "id")
