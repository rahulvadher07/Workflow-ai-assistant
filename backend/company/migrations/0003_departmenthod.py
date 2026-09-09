from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def copy_legacy_hods(apps, schema_editor):
    Department = apps.get_model("company", "Department")
    DepartmentHOD = apps.get_model("company", "DepartmentHOD")
    for department in Department.objects.exclude(hod_id__isnull=True):
        DepartmentHOD.objects.get_or_create(department_id=department.id, hod_id=department.hod_id)


class Migration(migrations.Migration):
    dependencies = [("company", "0002_alter_policydocument_file")]
    operations = [
        migrations.CreateModel(
            name="DepartmentHOD",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("assigned_at", models.DateTimeField(auto_now_add=True)),
                ("department", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="hod_assignments", to="company.department")),
                ("hod", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="department_hod_assignments", to=settings.AUTH_USER_MODEL)),
            ],
            options={"constraints": [models.UniqueConstraint(fields=("department", "hod"), name="unique_department_hod")]},
        ),
        migrations.AddField(
            model_name="department", name="hods",
            field=models.ManyToManyField(blank=True, related_name="hod_departments", through="company.DepartmentHOD", to=settings.AUTH_USER_MODEL),
        ),
        migrations.RunPython(copy_legacy_hods, migrations.RunPython.noop),
    ]
