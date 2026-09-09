from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from .models import AIConversation, AIMessage
from .serializers import AIChatRequestSerializer


class AIConversationExpiryTests(TestCase):
    def test_conversation_older_than_24_hours_is_deleted(self):
        User = get_user_model()
        user = User.objects.create_user(username="expiry-user", password="TestPass123!")
        old = AIConversation.objects.create(employee=user)
        old.started_at = timezone.now() - timedelta(hours=24, seconds=1)
        old.save(update_fields=["started_at"])
        AIMessage.objects.create(conversation=old, role=AIMessage.Role.USER, content="hello")

        cutoff = timezone.now() - timedelta(hours=24)
        AIConversation.objects.filter(started_at__lt=cutoff).delete()

        self.assertFalse(AIConversation.objects.filter(pk=old.pk).exists())
        self.assertFalse(AIMessage.objects.filter(conversation_id=old.pk).exists())

    def test_conversation_under_24_hours_is_retained(self):
        User = get_user_model()
        user = User.objects.create_user(username="keep-user", password="TestPass123!")
        current = AIConversation.objects.create(employee=user)
        current.started_at = timezone.now() - timedelta(hours=23, minutes=59)
        current.save(update_fields=["started_at"])

        cutoff = timezone.now() - timedelta(hours=24)
        AIConversation.objects.filter(started_at__lt=cutoff).delete()

        self.assertTrue(AIConversation.objects.filter(pk=current.pk).exists())
