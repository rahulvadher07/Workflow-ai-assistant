from django.db import migrations


def create_default_casual_leave(apps, schema_editor):
    LeaveType = apps.get_model("leave", "LeaveType")
    LeaveType.objects.get_or_create(
        name="CL",
        defaults={"default_annual_quota": 12},
    )


def remove_default_casual_leave(apps, schema_editor):
    LeaveType = apps.get_model("leave", "LeaveType")
    LeaveType.objects.filter(name="CL", default_annual_quota=12).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("leave", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(create_default_casual_leave, remove_default_casual_leave),
    ]
