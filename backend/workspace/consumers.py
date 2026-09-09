import json

from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async


class ConversationConsumer(AsyncWebsocketConsumer):
    """
    ws/workspace/conversations/{conversation_id}/

    Auth: relies on scope["user"] populated by JWTAuthMiddleware
    (core/middleware/jwt_ws_auth.py). Authorization: verifies team
    membership/HOD-of-department/Super-Admin before accepting the
    connection - never accept-then-filter.
    """

    async def connect(self):
        self.conversation_id = self.scope["url_route"]["kwargs"]["conversation_id"]
        self.group_name = f"conversation_{self.conversation_id}"
        user = self.scope.get("user")

        if user is None or not getattr(user, "is_authenticated", False):
            await self.close(code=4401)
            return

        allowed = await self._user_can_access_conversation(user, self.conversation_id)
        if not allowed:
            await self.close(code=4403)
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            return

        text = (data.get("text") or "").strip()
        if not text:
            return

        user = self.scope["user"]
        message = await self._save_message(user, self.conversation_id, text)
        if message is None:
            return

        await self.channel_layer.group_send(
            self.group_name,
            {"type": "chat.message", "message": message},
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event["message"]))

    @database_sync_to_async
    def _user_can_access_conversation(self, user, conversation_id):
        from .models import Conversation
        from .views import _can_access_team

        conv = Conversation.objects.filter(pk=conversation_id).select_related(
            "team", "team__department"
        ).first()
        if conv is None:
            return False
        return _can_access_team(user, conv.team)

    @database_sync_to_async
    def _save_message(self, user, conversation_id, text):
        from .models import Conversation
        from .serializers import IssueMessageSerializer
        from .services import post_message

        from .views import _can_access_team
        conv = Conversation.objects.filter(pk=conversation_id).select_related("team", "team__department").first()
        if conv is None or not _can_access_team(user, conv.team):
            return None
        msg = post_message(conv, user, text)
        return IssueMessageSerializer(msg).data
