"""
notify() is the single write path for creating a notification - called
directly from service functions across apps (not via signals, so it's
never silently missed when debugging). After creating the row, pushes
to the recipient's WebSocket group if connected; REST GET remains the
always-works fallback/source of truth (see architecture.md section 17).
"""

from django.db import transaction

from .models import Notification, NotificationOutbox


@transaction.atomic
def notify(recipient, verb, title, message="", related_object=None):
    notification = Notification.objects.create(
        recipient=recipient,
        verb=verb,
        title=title,
        message=message,
        related_object=related_object,
    )
    NotificationOutbox.objects.create(notification=notification)
    transaction.on_commit(lambda notification_id=notification.id: _schedule_notification_delivery(notification_id))
    return notification


def _schedule_notification_delivery(notification_id):
    try:
        from .tasks import deliver_notification_outbox
        deliver_notification_outbox.delay(notification_id)
    except Exception:
        # The durable outbox row remains; a periodic worker sweep can deliver it later.
        pass


def _push_realtime(notification):
    try:
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync

        channel_layer = get_channel_layer()
        if channel_layer is None:
            return
        async_to_sync(channel_layer.group_send)(
            f"user_{notification.recipient_id}_notifications",
            {
                "type": "notification.message",
                "notification": {
                    "id": notification.id,
                    "verb": notification.verb,
                    "title": notification.title,
                    "message": notification.message,
                    "is_read": notification.is_read,
                    "created_at": notification.created_at.isoformat(),
                },
            },
        )
    except Exception:
        # The notification row/outbox are already persisted. Re-raise here so
        # the outbox worker can retry realtime delivery; notification creation
        # itself remains authoritative in the database.
        raise
