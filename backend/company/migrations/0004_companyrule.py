from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("company", "0003_departmenthod")]

    operations = [
        migrations.CreateModel(
            name="CompanyRule",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=200)),
                ("category", models.CharField(choices=[("PAYROLL", "Payroll"), ("TIME", "Time"), ("ATTENDANCE", "Attendance"), ("LEAVE", "Leave"), ("GENERAL", "General")], default="GENERAL", max_length=20)),
                ("details", models.TextField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["category", "title"]},
        )
    ]
