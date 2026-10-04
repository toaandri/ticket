import uuid

from django.conf import settings
from django.db import models


class AppendOnlyQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise ValueError("Audit records cannot be updated.")

    def delete(self):
        raise ValueError("Audit records cannot be deleted.")


class AuditLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True)
    organization = models.ForeignKey("organizations.Organization", on_delete=models.PROTECT, null=True)
    action = models.CharField(max_length=100)
    entity_id = models.UUIDField()
    created_at = models.DateTimeField(auto_now_add=True)
    objects = AppendOnlyQuerySet.as_manager()

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValueError("Audit records cannot be updated.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("Audit records cannot be deleted.")
