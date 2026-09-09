"""
Month-end payroll automation. Idempotent via generate_draft_payroll's
own unique_together(year, month) + per-employee upsert-skip-if-approved
logic (Part 8 section 8/13). Never auto-approves - HOD approval is
always a separate, manual step.
"""

from celery import shared_task
from django.utils import timezone

from accounts.models import User
from notifications.services import notify
from notifications.models import Notification
from .services import generate_draft_payroll


@shared_task
def generate_month_end_payroll():
    """
    Scheduled for the 1st of each month (previous month's payroll).
    Generates drafts, then notifies each HOD with pending payslips to
    review.
    """
    now = timezone.now()
    # Previous calendar month, since this runs on the 1st for the month just ended.
    year, month = (now.year, now.month - 1) if now.month > 1 else (now.year - 1, 12)

    result = generate_draft_payroll(year, month)

    from company.models import department_hod_queryset
    departments = {
        profile.department_id
        for profile in result["period"].payslips.select_related("employee__employee_profile").values_list(
            "employee__employee_profile__department_id", flat=True
        )
        if profile
    }
    hod_ids = set()
    for department_id in departments:
        from company.models import Department
        department = Department.objects.filter(pk=department_id).first()
        if department:
            hod_ids.update(department_hod_queryset(department).values_list("pk", flat=True))
    hods = User.objects.filter(pk__in=hod_ids, role=User.Role.HOD, status=User.Status.ACTIVE)

    for hod in hods:
        notify(
            recipient=hod,
            verb=Notification.Verb.PAYSLIP_AVAILABLE,
            title=f"Payroll ready for review - {year}-{month:02d}",
            message=f"Draft payroll for {year}-{month:02d} is ready for your department. Please review and approve.",
        )

    return {"year": year, "month": month, "payslips_generated": result["payslips_generated"]}
