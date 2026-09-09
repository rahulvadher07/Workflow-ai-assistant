from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Custom user. An HOD is just a User with role=HOD - Department.hod
    points here directly, no separate HOD model.
    """

    class Role(models.TextChoices):
        SUPER_ADMIN = "SUPER_ADMIN", "Super Admin"
        HOD = "HOD", "HOD"
        EMPLOYEE = "EMPLOYEE", "Employee"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        ACTIVE = "ACTIVE", "Active"
        REJECTED = "REJECTED", "Rejected"
        SUSPENDED = "SUSPENDED", "Suspended"

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.EMPLOYEE)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.role})"

    @property
    def is_active_approved(self):
        return self.status == self.Status.ACTIVE


class EmployeeProfile(models.Model):
    """
    1:1 profile for any User (Employee or HOD) that belongs to a department.
    Super Admin does not need a profile.
    """

    user = models.OneToOneField(
        "accounts.User", on_delete=models.CASCADE, related_name="employee_profile"
    )
    department = models.ForeignKey(
        "company.Department",
        on_delete=models.PROTECT,
        related_name="employee_profiles",
    )
    employee_code = models.CharField(max_length=30, unique=True)
    phone = models.CharField(max_length=20, blank=True)
    date_joined_company = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} - {self.department.name}"
