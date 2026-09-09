from unittest.mock import AsyncMock, patch

from django.test import SimpleTestCase
from django.contrib.auth.models import AnonymousUser

from .consumers import NotificationConsumer


class NotificationConsumerSafetyTests(SimpleTestCase):
    def test_anonymous_user_is_rejected(self):
        consumer = NotificationConsumer.__new__(NotificationConsumer)
        consumer.scope = {"user": AnonymousUser()}
        consumer.close = AsyncMock()

        import asyncio
        asyncio.run(consumer.connect())
        consumer.close.assert_awaited_once_with(code=4401)

    def test_channel_layer_failure_does_not_abort_handshake(self):
        user = type("User", (), {"id": 2, "is_authenticated": True})()
        consumer = NotificationConsumer.__new__(NotificationConsumer)
        consumer.scope = {"user": user}
        consumer.channel_name = "test-channel"
        consumer.channel_layer = type("Layer", (), {"group_add": AsyncMock(side_effect=RuntimeError("redis down"))})()
        consumer.accept = AsyncMock()

        import asyncio
        with patch("notifications.consumers.logger.exception"):
            asyncio.run(consumer.connect())

        consumer.accept.assert_awaited_once()
        self.assertFalse(consumer.realtime_enabled)
