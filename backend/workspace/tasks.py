"""
Celery periodic tasks for task reminders, overdue detection, and issue
escalation. Idempotency is enforced via timestamp flags on the model
rows themselves (reminder_sent_at / overdue_notified_at / escalated_at)
rather than a separate log table - simplest mechanism that guarantees
each event fires at most once.
"""

from celery import shared_task
from django.conf import settings
from django.utils import timezone

from notifications.services import notify
from notifications.models import Notification
from .models import Task, Issue


@shared_task
def send_task_reminders():
    """
    Notifies the assignee (or creator if unassigned) once when a task's
    deadline is within TASK_REMINDER_WINDOW_HOURS and hasn't already
    been reminded. Completed tasks are excluded.
    """
    now = timezone.now()
    window_end = now + timezone.timedelta(hours=settings.TASK_REMINDER_WINDOW_HOURS)

    candidates = Task.objects.filter(
        deadline__isnull=False,
        deadline__gt=now,
        deadline__lte=window_end,
        reminder_sent_at__isnull=True,
    ).exclude(status=Task.Status.COMPLETED)

    sent = 0
    for task in candidates:
        recipient = task.assignee or task.creator
        if recipient is None:
            continue
        notify(
            recipient=recipient,
            verb=Notification.Verb.TASK_REMINDER,
            title=f"{task.display_number} is due soon",
            message=f"'{task.description[:80]}' is due on {task.deadline.strftime('%d %b, %H:%M')}.",
            related_object=task,
        )
        task.reminder_sent_at = now
        task.save(update_fields=["reminder_sent_at"])
        sent += 1
    return {"reminders_sent": sent}


@shared_task
def detect_overdue_tasks():
    """
    Notifies the assignee/creator AND the department HOD once when a
    task's deadline has passed and it isn't completed.
    """
    now = timezone.now()

    candidates = Task.objects.filter(
        deadline__isnull=False,
        deadline__lt=now,
        overdue_notified_at__isnull=True,
    ).exclude(status=Task.Status.COMPLETED).select_related("conversation__team__department")

    notified = 0
    for task in candidates:
        recipient = task.assignee or task.creator
        if recipient:
            notify(
                recipient=recipient,
                verb=Notification.Verb.TASK_OVERDUE,
                title=f"{task.display_number} is overdue",
                message=f"'{task.description[:80]}' was due on {task.deadline.strftime('%d %b, %H:%M')}.",
                related_object=task,
            )

        from company.models import department_hod_queryset
        for hod in department_hod_queryset(task.conversation.team.department):
            if hod.id == getattr(recipient, "id", None):
                continue
            notify(
                recipient=hod,
                verb=Notification.Verb.TASK_OVERDUE,
                title=f"{task.display_number} is overdue",
                message=f"'{task.description[:80]}' assigned in {task.conversation.team.name} is overdue.",
                related_object=task,
            )

        task.overdue_notified_at = now
        task.save(update_fields=["overdue_notified_at"])
        notified += 1
    return {"overdue_notified": notified}


@shared_task
def escalate_stale_issues():
    """
    Notifies the department HOD once when an issue has been OPEN or
    IN_PROGRESS for more than ISSUE_ESCALATION_HOURS. Resolved issues
    are excluded by the status filter itself.
    """
    now = timezone.now()
    threshold = now - timezone.timedelta(hours=settings.ISSUE_ESCALATION_HOURS)

    candidates = Issue.objects.filter(
        status__in=[Issue.Status.OPEN, Issue.Status.IN_PROGRESS],
        created_at__lte=threshold,
        escalated_at__isnull=True,
    ).select_related("conversation__team__department")

    escalated = 0
    for issue in candidates:
        from company.models import department_hod_queryset
        hods = department_hod_queryset(issue.conversation.team.department)
        if not hods.exists():
            continue
        for hod in hods:
            notify(
                recipient=hod,
            verb=Notification.Verb.ISSUE_ESCALATED,
            title=f"{issue.display_number} requires attention",
            message=f"'{issue.title}' has been unresolved for over {settings.ISSUE_ESCALATION_HOURS} hours.",
            related_object=issue,
        )
        issue.escalated_at = now
        issue.save(update_fields=["escalated_at"])
        escalated += 1
    return {"issues_escalated": escalated}
