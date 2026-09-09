from celery import shared_task
from django.utils import timezone

from accounts.models import User
from .services import notify
from .models import Notification, NotificationOutbox
from .daily_brief import build_daily_brief, format_brief_text
from datetime import timedelta


@shared_task
def purge_expired_notifications():
    cutoff = timezone.now() - timedelta(days=7)
    deleted, _ = Notification.objects.filter(created_at__lt=cutoff).delete()
    return {"deleted": deleted}


@shared_task
def generate_daily_briefs():
    """
    Runs once daily (scheduled 8 AM via celery beat). Generates one
    brief per HOD who has an assigned department, notifies each HOD
    with the summary text. No LLM involved - pure structured data.
    """
    from company.models import Department, department_hod_queryset
    hod_ids = set()
    for department_id in Department.objects.values_list("id", flat=True):
        department = Department.objects.filter(pk=department_id).first()
        if department:
            hod_ids.update(department_hod_queryset(department).values_list("pk", flat=True))
    hods = User.objects.filter(
        pk__in=hod_ids, role=User.Role.HOD, status=User.Status.ACTIVE
    )

    generated = 0
    for hod in hods:
        brief = build_daily_brief(hod)
        if brief is None:
            continue
        text = format_brief_text(brief)
        notify(
            recipient=hod,
            verb=Notification.Verb.DAILY_BRIEF,
            title="Your Daily Brief is ready",
            message=text,
        )
        generated += 1
    return {"briefs_generated": generated}


@shared_task(bind=True, max_retries=5, default_retry_delay=10)
def deliver_notification_outbox(self, outbox_id):
    from django.utils import timezone
    outbox = NotificationOutbox.objects.select_related("notification").filter(pk=outbox_id).first()
    if not outbox or outbox.delivered_at:
        return {"delivered": True}
    try:
        from .services import _push_realtime
        _push_realtime(outbox.notification)
        outbox.delivered_at = timezone.now()
        outbox.attempts += 1
        outbox.last_error = ""
        outbox.save(update_fields=["delivered_at", "attempts", "last_error", "updated_at"])
        return {"delivered": True}
    except Exception as exc:
        outbox.attempts += 1
        outbox.last_error = str(exc)[:1000]
        outbox.save(update_fields=["attempts", "last_error", "updated_at"])
        raise self.retry(exc=exc, countdown=min(300, 10 * (2 ** min(outbox.attempts, 5))))


@shared_task
def sweep_notification_outbox(limit=100):
    pending = NotificationOutbox.objects.filter(delivered_at__isnull=True).order_by("created_at")[:limit]
    count = 0
    for item in pending:
        deliver_notification_outbox.delay(item.id)
        count += 1
    return {"scheduled": count}
