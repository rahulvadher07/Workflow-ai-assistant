"""Cross-app server-originated UI invalidation signals."""
from __future__ import annotations

import logging

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from core.realtime import related_user_ids, schedule_user_data_change

logger = logging.getLogger("workflow_ai.realtime")

_MODEL_RESOURCE = {
    ("attendance", "PunchRecord"): "attendance",
    ("attendance", "AttendanceDay"): "attendance",
    ("leave", "LeaveRequest"): "leave",
    ("leave", "LeaveBalance"): "leave",
    ("workspace", "Task"): "workspace",
    ("workspace", "Issue"): "workspace",
    ("workspace", "Conversation"): "workspace",
    ("workspace", "IssueMessage"): "workspace",
    ("teams", "Team"): "teams",
    ("teams", "TeamMembership"): "teams",
    ("accounts", "User"): "auth",
    ("accounts", "EmployeeProfile"): "auth",
    ("company", "Department"): "company",
    ("company", "DepartmentHOD"): "company",
    ("company", "PolicyDocument"): "company",
    ("company", "CompanyRule"): "company",
    ("company", "Company"): "company",
    ("company", "PayrollRule"): "payroll",
    ("payroll", "EmployeeSalary"): "payroll",
    ("payroll", "PayrollPeriod"): "payroll",
    ("payroll", "Payslip"): "payroll",
}


def _emit(instance, action):
    resource = _MODEL_RESOURCE.get((instance._meta.app_label, instance.__class__.__name__))
    if not resource:
        return
    try:
        user_ids = related_user_ids(instance)
        schedule_user_data_change(user_ids, resource, action=action, entity_id=instance.pk)
    except Exception:
        # Realtime is an enhancement only; never block domain persistence.
        logger.exception(
            "[REALTIME DATA ERROR] action=signal_emit model=%s.%s resource=%s",
            instance._meta.app_label,
            instance.__class__.__name__,
            resource,
        )


@receiver(post_save)
def _realtime_post_save(sender, instance, created, **kwargs):
    if (sender._meta.app_label, sender.__name__) in _MODEL_RESOURCE:
        _emit(instance, "created" if created else "updated")


@receiver(post_delete)
def _realtime_post_delete(sender, instance, **kwargs):
    if (sender._meta.app_label, sender.__name__) in _MODEL_RESOURCE:
        _emit(instance, "deleted")
