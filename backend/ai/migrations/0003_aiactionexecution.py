from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("ai", "0002_aiconversation_gemini_interaction_id")]

    operations = [
        migrations.CreateModel(
            name="AIActionExecution",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("key", models.CharField(max_length=128, unique=True)),
                ("tool_name", models.CharField(max_length=100)),
                ("status", models.CharField(choices=[("PROCESSING", "Processing"), ("SUCCEEDED", "Succeeded"), ("FAILED", "Failed")], default="PROCESSING", max_length=20)),
                ("result", models.JSONField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("conversation", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="action_executions", to="ai.aiconversation")),
            ],
            options={"indexes": [models.Index(fields=["conversation", "tool_name", "created_at"], name="ai_aiactione_convers_8f0b60_idx")]},
        )
    ]
