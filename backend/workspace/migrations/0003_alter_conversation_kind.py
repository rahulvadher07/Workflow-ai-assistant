from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("workspace", "0002_issue_escalated_at_task_overdue_notified_at_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="conversation",
            name="kind",
            field=models.CharField(
                choices=[
                    ("TEAM_GENERAL", "Team General"),
                    ("ISSUE", "Issue"),
                    ("TASK", "Task"),
                ],
                max_length=20,
            ),
        ),
    ]
