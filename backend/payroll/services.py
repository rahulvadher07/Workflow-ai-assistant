"""
Deterministic payroll calculation. Reads already-computed AttendanceDay
rollups from Part 4 (never recalculates attendance here) and approved
LeaveRequest data from Part 6. All arithmetic is plain Python - no AI
involvement anywhere in this file, per architecture.md and this Part's
explicit instruction.
"""

from calendar import monthrange
from datetime import date as date_cls
from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction
from django.utils import timezone

from attendance.models import AttendanceDay
from accounts.models import EmployeeProfile
from company.models import Company, PayrollRule
from leave.models import LeaveRequest
from .models import EmployeeSalary, PayrollPeriod, Payslip


class PayrollError(Exception):
    def __init__(self, code, message):
        self.code = code
        self.message = message
        super().__init__(message)


def _round2(value):
    return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calculate_payslip_data(employee, year, month):
    """
    Pure calculation - returns a dict, does not touch the DB. Callers
    decide whether/how to persist it (generate_draft_payroll does).
    """
    salary_config = EmployeeSalary.objects.filter(employee=employee).first()
    if salary_config is None:
        raise PayrollError("VALIDATION_ERROR", f"No salary configured for {employee}.")

    _, last_day = monthrange(year, month)
    start = date_cls(year, month, 1)
    end = date_cls(year, month, last_day)
    working_days = last_day  # simple: every calendar day is a working day (no separate holiday calendar in scope)

    days = AttendanceDay.objects.filter(employee=employee, date__gte=start, date__lte=end)
    present_days = days.filter(status=AttendanceDay.Status.PRESENT).count()
    late_days = days.filter(is_late=True).count()
    total_worked_minutes = sum(d.total_minutes for d in days)
    overtime_minutes = sum(d.overtime_minutes for d in days)

    leave_days = sum(
        (min(lr.to_date, end) - max(lr.from_date, start)).days + 1
        for lr in LeaveRequest.objects.filter(
            employee=employee,
            status=LeaveRequest.Status.APPROVED,
            from_date__lte=end,
            to_date__gte=start,
        )
    )

    company = Company.get_solo()
    rule = PayrollRule.get_solo()
    basic = Decimal(str(salary_config.basic_monthly_salary))
    allowances = Decimal(str(salary_config.allowances))
    overtime_multiplier = Decimal(str(rule.overtime_multiplier))
    pf_percent = Decimal(str(rule.pf_percent))

    # Overtime amount uses the company-configured standard shift length,
    # not a hard-coded 8-hour day.
    standard_month_minutes = Decimal(working_days * company.standard_shift_minutes)
    per_minute_rate = (basic / standard_month_minutes) if standard_month_minutes else Decimal(0)
    overtime_amount = _round2(per_minute_rate * Decimal(overtime_minutes) * overtime_multiplier)

    gross_salary = _round2(basic + allowances + overtime_amount)
    pf_deduction = _round2(gross_salary * (pf_percent / Decimal(100)))
    other_deductions = Decimal("0.00")
    net_salary = _round2(gross_salary - pf_deduction - other_deductions)

    return {
        "working_days": working_days,
        "present_days": present_days,
        "leave_days": leave_days,
        "late_days": late_days,
        "total_worked_minutes": total_worked_minutes,
        "overtime_minutes": overtime_minutes,
        "basic_salary": _round2(basic),
        "allowances": _round2(allowances),
        "overtime_amount": overtime_amount,
        "gross_salary": gross_salary,
        "pf_deduction": pf_deduction,
        "other_deductions": other_deductions,
        "net_salary": net_salary,
    }


@transaction.atomic
def generate_draft_payroll(year, month):
    """
    Idempotent: creates the PayrollPeriod if needed (unique_together
    guards against a second concurrent create), then upserts one
    Payslip per employee with EmployeeSalary configured - never creates
    a second DRAFT/HOD_APPROVED payslip for the same employee+period.
    Skips employees who already have an HOD_APPROVED payslip for this
    period (approved payroll never silently changes).
    """
    period, _ = PayrollPeriod.objects.get_or_create(year=year, month=month)

    from accounts.models import User
    employees = User.objects.filter(
        salary_config__isnull=False, status=User.Status.ACTIVE
    ).select_related("salary_config")

    created, skipped = 0, 0
    for employee in employees:
        existing = Payslip.objects.filter(employee=employee, period=period).first()
        if existing and existing.status == Payslip.Status.HOD_APPROVED:
            skipped += 1
            continue

        data = calculate_payslip_data(employee, year, month)

        if existing:
            for field, value in data.items():
                setattr(existing, field, value)
            existing.save()
        else:
            Payslip.objects.create(employee=employee, period=period, **data)
        created += 1

    if period.status == PayrollPeriod.Status.DRAFT:
        period.status = PayrollPeriod.Status.PENDING_APPROVAL
        period.save(update_fields=["status"])

    return {"period": period, "payslips_generated": created, "already_approved_skipped": skipped}


@transaction.atomic
def approve_payslip(payslip, actor):
    """HOD approves one employee's payslip. Own-department only."""
    # Same nullable-outer-join constraint as accounts/_decide_registration:
    # lock only the Payslip row, fetch the employee's department separately.
    payslip = Payslip.objects.select_for_update().select_related("employee").get(pk=payslip.pk)

    profile = EmployeeProfile.objects.select_related("department").filter(user=payslip.employee).first()
    if profile is None or not __import__("company.models", fromlist=["is_hod_of"]).is_hod_of(actor, profile.department):
        raise PayrollError("FORBIDDEN", "You can only approve payroll for your own department.")

    if payslip.status == Payslip.Status.HOD_APPROVED:
        raise PayrollError("INVALID_PAYROLL_STATE", "This payslip is already approved.")

    payslip.status = Payslip.Status.HOD_APPROVED
    payslip.approved_by = actor
    payslip.approved_at = timezone.now()
    payslip.save(update_fields=["status", "approved_by", "approved_at"])

    from notifications.services import notify
    from notifications.models import Notification
    notify(
        recipient=payslip.employee,
        verb=Notification.Verb.PAYSLIP_AVAILABLE,
        title=f"Payslip available - {payslip.period.year}-{payslip.period.month:02d}",
        message=f"Your payslip for {payslip.period.year}-{payslip.period.month:02d} has been approved. Net salary: {payslip.net_salary}.",
        related_object=payslip,
    )

    return payslip


def send_payslip_email(payslip):
    """
    Sends the approved payslip PDF via the existing email configuration
    (console backend for local dev, per architecture.md's "reuse the
    Hospital Management System approach" - no new provider introduced).
    """
    from django.core.mail import EmailMessage
    from django.conf import settings

    if not payslip.pdf_file:
        return False

    subject = f"Payslip - {payslip.period.year}-{payslip.period.month:02d}"
    body = (
        f"Hi {payslip.employee.get_full_name() or payslip.employee.username},\n\n"
        f"Your payslip for {payslip.period.year}-{payslip.period.month:02d} is attached.\n"
        f"Net salary: {payslip.net_salary}\n\n"
        "This is an automated message."
    )
    email = EmailMessage(
        subject=subject,
        body=body,
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
        to=[payslip.employee.email],
    )
    with payslip.pdf_file.open("rb") as f:
        email.attach(payslip.pdf_file.name.split("/")[-1], f.read(), "application/pdf")
    email.send(fail_silently=False)
    return True
