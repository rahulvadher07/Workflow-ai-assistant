from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("notifications", "0001_initial")]
    operations = [
        migrations.AlterField(
            model_name="notification",
            name="verb",
            field=models.CharField(
                choices=[
                    ("REGISTRATION_SUBMITTED", "Registration Submitted"),
                    ("REGISTRATION_APPROVED", "Registration Approved"),
                    ("REGISTRATION_REJECTED", "Registration Rejected"),
                    ("LEAVE_REQUESTED", "Leave Requested"),
                    ("LEAVE_APPROVED", "Leave Approved"),
                    ("LEAVE_REJECTED", "Leave Rejected"),
                    ("LEAVE_CANCELLED", "Leave Cancelled"),
                    ("TASK_ASSIGNED", "Task Assigned"),
                    ("TASK_REMINDER", "Task Reminder"),
                    ("TASK_OVERDUE", "Task Overdue"),
                    ("ISSUE_ESCALATED", "Issue Escalated"),
                    ("ISSUE_UPDATED", "Issue Updated"),
                    ("PAYSLIP_AVAILABLE", "Payslip Available"),
                    ("DAILY_BRIEF", "Daily Brief"),
                    ("ANNOUNCEMENT", "Announcement"),
                ],
                max_length=40,
            ),
        )
    ]
