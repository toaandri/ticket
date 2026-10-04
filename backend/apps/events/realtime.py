from contextlib import suppress

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction


def availability_changed(event):
    event_id, version = str(event.pk), event.version

    def broadcast():
        with suppress(Exception):
            async_to_sync(get_channel_layer().group_send)(
                f"event.{event_id}", {"type": "availability.hint", "event_id": event_id, "version": version}
            )

    transaction.on_commit(broadcast)
