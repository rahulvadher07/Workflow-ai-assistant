import json
import logging

from channels.generic.websocket import AsyncWebsocketConsumer

logger = logging.getLogger(__name__)


class NotificationConsumer(AsyncWebsocketConsumer):
    """ws/notifications/ - per-user group, auth via JWTAuthMiddleware."""

    async def connect(self):
        user = self.scope.get("user")
        if user is None or not getattr(user, "is_authenticated", False):
            await self.close(code=4401)
            return

        self.group_name = f"user_{user.id}_notifications"
        try:
            await self.channel_layer.group_add(self.group_name, self.channel_name)
        except Exception:
            # Do not turn a channel-layer/realtime delivery problem into a
            # failed WebSocket handshake. REST notification endpoints remain
            # the source of truth and the client can continue normally.
            logger.exception(
                "[AI NOTIFICATION WS ERROR] action=group_add user_id=%s group=%s",
                user.id,
                self.group_name,
            )
            self.realtime_enabled = False
        else:
            self.realtime_enabled = True

        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "group_name") and getattr(self, "realtime_enabled", False):
            try:
                await self.channel_layer.group_discard(self.group_name, self.channel_name)
            except Exception:
                logger.exception(
                    "[AI NOTIFICATION WS ERROR] action=group_discard group=%s close_code=%s",
                    self.group_name,
                    close_code,
                )

    async def notification_message(self, event):
        if not getattr(self, "realtime_enabled", False):
            return
        await self.send(text_data=json.dumps(event["notification"]))
