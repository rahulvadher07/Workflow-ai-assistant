from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("ai", "0003_aiactionexecution"),
    ]

    operations = [
        migrations.AddField(
            model_name="knowledgechunk",
            name="semantic_embedding",
            field=models.TextField(blank=True, default=""),
        ),
    ]
