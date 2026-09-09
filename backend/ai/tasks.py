from celery import shared_task
from datetime import timedelta
from django.utils import timezone

from .models import AIConversation, AIActionExecution


@shared_task
def purge_expired_ai_conversations():
    cutoff = timezone.now() - timedelta(hours=24)
    deleted, _ = AIConversation.objects.filter(started_at__lt=cutoff).delete()
    return {"deleted": deleted}


@shared_task
def purge_expired_ai_action_executions():
    cutoff = timezone.now() - timedelta(days=7)
    deleted, _ = AIActionExecution.objects.filter(created_at__lt=cutoff).delete()
    return {"deleted": deleted}
