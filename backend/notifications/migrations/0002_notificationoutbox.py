from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("notifications", "0001_initial")]
    operations = [
        migrations.CreateModel(
            name="NotificationOutbox",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("delivered_at", models.DateTimeField(blank=True, null=True)),
                ("attempts", models.PositiveIntegerField(default=0)),
                ("last_error", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("notification", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="outbox", to="notifications.notification")),
            ],
            options={"indexes": [models.Index(fields=["delivered_at", "created_at"], name="notificati_delivere_2bd8b0_idx")]},
        )
    ]
