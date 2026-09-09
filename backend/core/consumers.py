import json
import logging

from channels.generic.websocket import AsyncWebsocketConsumer

logger = logging.getLogger("workflow_ai.realtime")


class DataChangeConsumer(AsyncWebsocketConsumer):
    """Authenticated per-user invalidation stream for server-side changes."""

    async def connect(self):
        user = self.scope.get("user")
        if user is None or not getattr(user, "is_authenticated", False):
            await self.close(code=4401)
            return
        self.group_name = f"user_{user.id}_data_changes"
        try:
            await self.channel_layer.group_add(self.group_name, self.channel_name)
            await self.accept()
        except Exception:
            logger.exception("[REALTIME DATA ERROR] action=connect user_id=%s", user.id)
            await self.close(code=1011)

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            try:
                await self.channel_layer.group_discard(self.group_name, self.channel_name)
            except Exception:
                logger.exception("[REALTIME DATA ERROR] action=disconnect group=%s", self.group_name)

    async def data_change(self, event):
        await self.send(text_data=json.dumps(event.get("change") or {}))
