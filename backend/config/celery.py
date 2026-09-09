import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('config')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

app.conf.beat_schedule = {
    'purge-expired-ai-conversations-hourly': {
        'task': 'ai.tasks.purge_expired_ai_conversations',
        'schedule': crontab(minute=0),
    },
    'purge-expired-ai-action-executions-daily': {
        'task': 'ai.tasks.purge_expired_ai_action_executions',
        'schedule': crontab(hour=3, minute=0),
    },
    'task-reminders-hourly': {
        'task': 'workspace.tasks.send_task_reminders',
        'schedule': crontab(minute=0),  # once per hour
    },
    'overdue-tasks-hourly': {
        'task': 'workspace.tasks.detect_overdue_tasks',
        'schedule': crontab(minute=15),
    },
    'issue-escalation-hourly': {
        'task': 'workspace.tasks.escalate_stale_issues',
        'schedule': crontab(minute=30),
    },
    'hod-daily-brief': {
        'task': 'notifications.tasks.generate_daily_briefs',
        'schedule': crontab(hour=8, minute=0),  # 8 AM daily
    },
    'month-end-payroll': {
        'task': 'payroll.tasks.generate_month_end_payroll',
        'schedule': crontab(hour=1, minute=0, day_of_month=1),  # 1st of each month
    },
    'purge-expired-notifications-daily': {
        'task': 'notifications.tasks.purge_expired_notifications',
        'schedule': crontab(hour=2, minute=0),
    },
}
