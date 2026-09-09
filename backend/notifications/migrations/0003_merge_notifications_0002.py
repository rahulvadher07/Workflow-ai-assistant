from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("notifications", "0002_notification_leave_cancelled"),
        ("notifications", "0002_notificationoutbox"),
    ]

    operations = []
