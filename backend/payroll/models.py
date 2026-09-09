from django.db import models


class EmployeeSalary(models.Model):
    """Current salary configuration for an employee. Set by Admin/HOD."""

    employee = models.OneToOneField(
        "accounts.User", on_delete=models.CASCADE, related_name="salary_config"
    )
    basic_monthly_salary = models.DecimalField(max_digits=12, decimal_places=2)
    allowances = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    updated_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, related_name="+"
    )
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.employee} - {self.basic_monthly_salary}"


class PayrollPeriod(models.Model):
    """One calendar month's payroll run for the whole company."""

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        PENDING_APPROVAL = "PENDING_APPROVAL", "Pending Approval"
        APPROVED = "APPROVED", "Approved"

    year = models.PositiveIntegerField()
    month = models.PositiveSmallIntegerField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    generated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("year", "month")

    def __str__(self):
        return f"{self.year}-{self.month:02d} ({self.status})"


class Payslip(models.Model):
    """
    One employee's payroll calculation for one PayrollPeriod. This IS the
    calculation record - no separate PayrollCalculation model, per
    architecture.md (a value object doesn't need splitting across tables).
    """

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        HOD_APPROVED = "HOD_APPROVED", "HOD Approved"

    employee = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="payslips")
    period = models.ForeignKey(PayrollPeriod, on_delete=models.CASCADE, related_name="payslips")

    working_days = models.PositiveIntegerField()
    present_days = models.PositiveIntegerField()
    leave_days = models.PositiveIntegerField()
    late_days = models.PositiveIntegerField()
    total_worked_minutes = models.PositiveIntegerField()
    overtime_minutes = models.PositiveIntegerField()

    basic_salary = models.DecimalField(max_digits=12, decimal_places=2)
    allowances = models.DecimalField(max_digits=12, decimal_places=2)
    overtime_amount = models.DecimalField(max_digits=12, decimal_places=2)
    gross_salary = models.DecimalField(max_digits=12, decimal_places=2)
    pf_deduction = models.DecimalField(max_digits=12, decimal_places=2)
    other_deductions = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    net_salary = models.DecimalField(max_digits=12, decimal_places=2)

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    approved_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    pdf_file = models.FileField(upload_to="payslips/", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("employee", "period")

    def __str__(self):
        return f"{self.employee} - {self.period} ({self.status})"
