from django.db import models
from django.core.validators import FileExtensionValidator
from decimal import Decimal


class Company(models.Model):
    """Singleton — one row representing the company itself."""

    name = models.CharField(max_length=200)
    standard_break_minutes = models.PositiveIntegerField(default=60)
    shift_start_time = models.TimeField(default="09:00:00")
    standard_shift_minutes = models.PositiveIntegerField(default=480)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # Enforce singleton: always overwrite pk=1
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1, defaults={"name": "My Company"})
        return obj


class Department(models.Model):
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="departments"
    )
    name = models.CharField(max_length=150, unique=True)
    # Legacy primary HOD kept for backward compatibility with existing data/API.
    hod = models.OneToOneField(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="department_headed",
        limit_choices_to={"role": "HOD"},
    )
    # New relation allows multiple HODs per department without breaking the
    # existing Department.hod field used by older code/data.
    hods = models.ManyToManyField(
        "accounts.User",
        through="DepartmentHOD",
        related_name="hod_departments",
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class DepartmentHOD(models.Model):
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name="hod_assignments")
    hod = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="department_hod_assignments")
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["department", "hod"], name="unique_department_hod"),
        ]

    def __str__(self):
        return f"{self.hod} -> {self.department.name}"


def department_hod_queryset(department):
    """Return all active HODs for a department, including legacy primary HOD data."""
    from accounts.models import User
    from django.db.models import Q

    return User.objects.filter(
        Q(hod_departments=department) | Q(department_headed=department),
        role=User.Role.HOD,
        status=User.Status.ACTIVE,
    ).distinct()


def is_hod_of(user, department):
    if not user or getattr(user, "role", None) != "HOD":
        return False
    if getattr(user, "status", None) != user.Status.ACTIVE or not getattr(user, "is_active", False):
        return False
    if department.hod_id == user.id:
        return True
    return DepartmentHOD.objects.filter(department=department, hod=user).exists()


class PolicyDocument(models.Model):
    """
    Model only in this Part — no upload/indexing logic yet.
    Indexing/RAG belongs to the `ai` app (later part) per approved architecture.
    """

    class Category(models.TextChoices):
        LEAVE = "LEAVE", "Leave Policy"
        ATTENDANCE = "ATTENDANCE", "Attendance Policy"
        OVERTIME = "OVERTIME", "Overtime Policy"
        PAYROLL = "PAYROLL", "Payroll Rules"
        GENERAL = "GENERAL", "Company Guidelines"

    title = models.CharField(max_length=200)
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.GENERAL)
    file = models.FileField(
        upload_to="policy_documents/",
        validators=[FileExtensionValidator(allowed_extensions=["pdf"])],
    )
    uploaded_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, related_name="uploaded_policies"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class PayrollRule(models.Model):
    """Singleton — company-wide payroll configuration."""

    pf_percent = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("12.00"))
    overtime_multiplier = models.DecimalField(max_digits=4, decimal_places=2, default=Decimal("1.50"))
    late_threshold_minutes = models.PositiveIntegerField(default=15)

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return "Payroll Rules"


class CompanyRule(models.Model):
    class Category(models.TextChoices):
        PAYROLL = "PAYROLL", "Payroll"
        TIME = "TIME", "Time"
        ATTENDANCE = "ATTENDANCE", "Attendance"
        LEAVE = "LEAVE", "Leave"
        GENERAL = "GENERAL", "General"

    title = models.CharField(max_length=200)
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.GENERAL)
    details = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["category", "title"]

    def __str__(self):
        return self.title
