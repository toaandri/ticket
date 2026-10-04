from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from .models import Event


class AvailabilityConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        event_id = self.scope["url_route"]["kwargs"]["event_id"]
        exists = await database_sync_to_async(
            Event.objects.filter(pk=event_id, status="PUBLISHED", organization__status="ACTIVE").exists
        )()
        if not exists:
            await self.close(code=4404)
            return
        self.group = f"event.{event_id}"
        await self.channel_layer.group_add(self.group, self.channel_name)
        await self.accept()
        await self.send_json({"event_id": str(event_id), "refetch": True})

    async def disconnect(self, code):
        if hasattr(self, "group"):
            await self.channel_layer.group_discard(self.group, self.channel_name)

    async def availability_hint(self, event):
        await self.send_json({"event_id": event["event_id"], "version": event["version"], "refetch": True})
