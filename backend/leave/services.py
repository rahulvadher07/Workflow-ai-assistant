from django.db import transaction
from django.utils import timezone

from .models import LeaveRequest, LeaveBalance, LeaveType


class LeaveError(Exception):
    def __init__(self, code, message):
        self.code = code
        self.message = message
        super().__init__(message)


@transaction.atomic
def create_leave_request(employee, leave_type_name, from_date, to_date, reason):
    """Create one leave request while preserving the existing business rules.

    Backend contract:
    - Scope is always the authenticated employee supplied by the caller.
    - Leave type must exist; dates must be ordered; requested days must fit balance.
    - Pending/approved overlap is rejected to prevent duplicate date ranges.
    - The employee must belong to a department with an assigned HOD.
    - The request is created as pending and routed to the existing approver flow.
    - This function never self-approves a request.
    """
    try:
        leave_type = LeaveType.objects.get(name__iexact=leave_type_name)
    except LeaveType.DoesNotExist:
        raise LeaveError("VALIDATION_ERROR", f"Unknown leave type '{leave_type_name}'.")

    if to_date < from_date:
        raise LeaveError("VALIDATION_ERROR", "to_date cannot be before from_date.")

    requested_days = (to_date - from_date).days + 1

    balance, _ = LeaveBalance.objects.select_for_update().get_or_create(
        employee=employee, leave_type=leave_type, defaults={"total": leave_type.default_annual_quota}
    )
    if balance.remaining < requested_days:
        raise LeaveError(
            "INSUFFICIENT_LEAVE",
            f"You only have {balance.remaining} {leave_type.name} day(s) remaining.",
        )

    overlapping = LeaveRequest.objects.filter(
        employee=employee,
        status__in=[LeaveRequest.Status.PENDING, LeaveRequest.Status.APPROVED],
        from_date__lte=to_date,
        to_date__gte=from_date,
    ).exists()
    if overlapping:
        raise LeaveError("DUPLICATE_REQUEST", "You already have a leave request overlapping these dates.")

    profile = getattr(employee, "employee_profile", None)
    if profile is None:
        raise LeaveError("VALIDATION_ERROR", "You are not assigned to a department.")
    from company.models import department_hod_queryset
    if not department_hod_queryset(profile.department).exists():
        raise LeaveError("VALIDATION_ERROR", "No HOD is assigned to your department to approve this request.")

    request = LeaveRequest.objects.create(
        employee=employee,
        leave_type=leave_type,
        from_date=from_date,
        to_date=to_date,
        reason=reason,
    )

    from notifications.services import notify
    from notifications.models import Notification
    from accounts.models import User
    if employee.role == User.Role.HOD:
        recipients = User.objects.filter(role=User.Role.SUPER_ADMIN, status=User.Status.ACTIVE)
    else:
        from company.models import department_hod_queryset
        recipients = department_hod_queryset(profile.department)
    for approver in recipients:
        notify(
            recipient=approver,
            verb=Notification.Verb.LEAVE_REQUESTED,
            title=f"Leave request from {employee.get_full_name() or employee.username}",
            message=f"{leave_type.name} leave, {from_date} to {to_date}: {reason}",
            related_object=request,
        )

    return request


def get_leave_balances(employee):
    balances = LeaveBalance.objects.filter(employee=employee).select_related("leave_type")
    existing_type_ids = set(balances.values_list("leave_type_id", flat=True))
    missing_types = LeaveType.objects.exclude(id__in=existing_type_ids)

    result = [
        {"leave_type": b.leave_type.name, "total": b.total, "used": b.used, "remaining": b.remaining}
        for b in balances
    ]
    for lt in missing_types:
        result.append({"leave_type": lt.name, "total": lt.default_annual_quota, "used": 0, "remaining": lt.default_annual_quota})
    return result


@transaction.atomic
def approve_leave_request(leave_request, actor):
    """Approve one exact leave request using the existing authorization matrix.

    Possible outcomes are intentionally explicit: Super Admin approves HOD
    requests; the employee's department HOD approves employee requests; only
    pending requests can be approved; sufficient leave balance is required;
    the approved balance is incremented and the employee is notified.
    """
    leave_request = LeaveRequest.objects.select_for_update().get(pk=leave_request.pk)
    employee_role = leave_request.employee.role
    department = leave_request.employee.employee_profile.department
    from accounts.models import User
    from company.models import is_hod_of
    if employee_role == User.Role.HOD:
        if actor.role != User.Role.SUPER_ADMIN:
            raise LeaveError("FORBIDDEN", "HOD leave requests can only be approved by Super Admin.")
    elif not is_hod_of(actor, department):
        raise LeaveError("FORBIDDEN", "Only the employee's department HOD can approve this request.")
    if leave_request.status != LeaveRequest.Status.PENDING:
        raise LeaveError("REGISTRATION_ALREADY_DECIDED", f"This request was already {leave_request.status.lower()}.")

    balance, _ = LeaveBalance.objects.select_for_update().get_or_create(
        employee=leave_request.employee,
        leave_type=leave_request.leave_type,
        defaults={"total": leave_request.leave_type.default_annual_quota},
    )
    if balance.remaining < leave_request.days:
        raise LeaveError(
            "INSUFFICIENT_LEAVE",
            f"Insufficient {balance.leave_type.name} balance to approve this request. Only {balance.remaining} day(s) remain.",
        )
    balance.used += leave_request.days
    balance.save(update_fields=["used"])

    from django.utils import timezone
    leave_request.status = LeaveRequest.Status.APPROVED
    leave_request.approved_by = actor
    leave_request.decided_at = timezone.now()
    leave_request.save(update_fields=["status", "approved_by", "decided_at"])

    from notifications.services import notify
    from notifications.models import Notification
    notify(
        recipient=leave_request.employee,
        verb=Notification.Verb.LEAVE_APPROVED,
        title="Leave request approved",
        message=f"Your {leave_request.leave_type.name} leave ({leave_request.from_date} to {leave_request.to_date}) was approved.",
        related_object=leave_request,
    )

    return leave_request


@transaction.atomic
def reject_leave_request(leave_request, actor):
    """Reject one exact pending leave request using existing permissions.

    HOD requests are decided by Super Admin; employee requests are decided by
    their department HOD. Already-decided requests are rejected and the employee
    receives the existing rejection notification.
    """
    leave_request = LeaveRequest.objects.select_for_update().get(pk=leave_request.pk)
    employee_role = leave_request.employee.role
    department = leave_request.employee.employee_profile.department
    from accounts.models import User
    from company.models import is_hod_of
    if employee_role == User.Role.HOD:
        if actor.role != User.Role.SUPER_ADMIN:
            raise LeaveError("FORBIDDEN", "HOD leave requests can only be rejected by Super Admin.")
    elif not is_hod_of(actor, department):
        raise LeaveError("FORBIDDEN", "Only the employee's department HOD can reject this request.")
    if leave_request.status != LeaveRequest.Status.PENDING:
        raise LeaveError("REGISTRATION_ALREADY_DECIDED", f"This request was already {leave_request.status.lower()}.")

    from django.utils import timezone
    leave_request.status = LeaveRequest.Status.REJECTED
    leave_request.approved_by = actor
    leave_request.decided_at = timezone.now()
    leave_request.save(update_fields=["status", "approved_by", "decided_at"])

    from notifications.services import notify
    from notifications.models import Notification
    notify(
        recipient=leave_request.employee,
        verb=Notification.Verb.LEAVE_REJECTED,
        title="Leave request rejected",
        message=f"Your {leave_request.leave_type.name} leave ({leave_request.from_date} to {leave_request.to_date}) was rejected.",
        related_object=leave_request,
    )

    return leave_request


@transaction.atomic
def cancel_leave_request(leave_request, actor):
    """Cancel one exact leave request safely and atomically.

    Backend action contract (the rule catalog may route to this function, but
    this function remains the final authority):
    1. Reload and lock the exact request so concurrent cancellation/approval cannot
       operate on stale state.
    2. CANCELLED requests return ALREADY_CANCELLED; REJECTED requests cannot be
       cancelled.
    3. The actor must be the request owner, Super Admin, or (for an employee leave)
       the HOD of that employee's department. No other employee can cancel it.
    4. APPROVED cancellation releases the request's used balance by the request
       duration; pending cancellation does not change used balance.
    5. Mark the request CANCELLED, record the cancelling actor/time, and notify the
       affected employee/appropriate approver exactly once per recipient.

    The function deliberately accepts one exact LeaveRequest object; bulk actions
    must preselect exact request IDs and call this function once per request inside
    their existing transaction.
    """
    leave_request = LeaveRequest.objects.select_for_update().select_related("employee__employee_profile__department", "leave_type").get(pk=leave_request.pk)
    from accounts.models import User
    from company.models import is_hod_of
    if leave_request.status == LeaveRequest.Status.CANCELLED:
        raise LeaveError("ALREADY_CANCELLED", "This leave request is already cancelled.")
    if leave_request.status == LeaveRequest.Status.REJECTED:
        raise LeaveError("VALIDATION_ERROR", "A rejected leave request cannot be cancelled.")
    owner = actor.id == leave_request.employee_id
    admin = actor.role == User.Role.SUPER_ADMIN
    hod = False
    if actor.role == User.Role.HOD and leave_request.employee.role == User.Role.EMPLOYEE:
        dept = getattr(getattr(leave_request.employee, "employee_profile", None), "department", None)
        hod = dept is not None and is_hod_of(actor, dept)
    if not (owner or admin or hod):
        raise LeaveError("FORBIDDEN", "You are not authorized to cancel this leave request.")
    if leave_request.status == LeaveRequest.Status.APPROVED:
        balance, _ = LeaveBalance.objects.select_for_update().get_or_create(
            employee=leave_request.employee,
            leave_type=leave_request.leave_type,
            defaults={"total": leave_request.leave_type.default_annual_quota},
        )
        balance.used = max(0, balance.used - leave_request.days)
        balance.save(update_fields=["used"])
    leave_request.status = LeaveRequest.Status.CANCELLED
    leave_request.cancelled_by = actor
    leave_request.cancelled_at = timezone.now()
    leave_request.save(update_fields=["status", "cancelled_by", "cancelled_at"])
    from notifications.services import notify
    from notifications.models import Notification
    from company.models import department_hod_queryset
    recipients=[]
    if leave_request.employee_id != actor.id:
        recipients.append(leave_request.employee)
    if leave_request.employee.role == User.Role.HOD:
        recipients.extend(User.objects.filter(role=User.Role.SUPER_ADMIN, status=User.Status.ACTIVE))
    else:
        dept=getattr(leave_request.employee.employee_profile, "department", None)
        if dept is not None:
            recipients.extend(department_hod_queryset(dept))
    seen=set()
    for recipient in recipients:
        if recipient.id in seen: continue
        seen.add(recipient.id)
        notify(recipient=recipient, verb=Notification.Verb.LEAVE_CANCELLED, title="Leave request cancelled", message=f"{leave_request.leave_type.name} leave ({leave_request.from_date} to {leave_request.to_date}) was cancelled by {actor.get_full_name() or actor.username}.", related_object=leave_request)
    return leave_request
