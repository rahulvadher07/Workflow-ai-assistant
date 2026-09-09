"""Controlled AI actions that reuse existing Django business services.

The model can request these tools, but every tool binds the real authenticated
user server-side and enforces the same permissions/business rules as the
existing application services/views. No AI tool accepts a raw user id as the
actor.
"""
from datetime import date as date_cls, timedelta

from accounts.models import User
from django.db import transaction
from teams.models import Team, TeamMembership
from attendance.models import PunchRecord
from attendance.services import create_punch, InvalidPunchError
from workspace.models import Task
from workspace.services import end_task as _end_task, start_task as _start_task, WorkspaceError
from leave.models import LeaveRequest
from leave.services import LeaveError, approve_leave_request, reject_leave_request, cancel_leave_request
from company.models import is_hod_of


def punch_attendance(user, requested_type=None):
    """Record exactly one punch for the authenticated user.

    The underlying attendance service remains authoritative and derives IN/OUT
    from punch parity. If the user explicitly requests IN/OUT, reject a
    mismatch rather than silently doing the opposite action.
    """
    requested_type = (requested_type or "").strip().upper() or None
    if requested_type not in (None, "IN", "OUT"):
        return {"error": "requested_type must be IN, OUT, or omitted."}

    from django.utils import timezone
    from django.db import transaction
    with transaction.atomic():
        # Keep the requested IN/OUT validation in the same transaction as the
        # punch creation so two concurrent AI requests cannot both observe the
        # same next punch type.
        user = User.objects.select_for_update().get(pk=user.pk)
        today = timezone.localdate()
        count = PunchRecord.objects.filter(employee=user, timestamp__date=today).count()
        expected_type = "IN" if count % 2 == 0 else "OUT"
        if requested_type and requested_type != expected_type:
            return {
                "error": f"Your next punch is {expected_type}, not {requested_type}. No punch was recorded."
            }

        try:
            record = create_punch(user)
        except InvalidPunchError as exc:
            return {"error": exc.message, "code": exc.code}

    return {
        "success": True,
        "type": expected_type,
        "timestamp": record.timestamp.isoformat(),
        "message": f"Punched {expected_type} successfully.",
    }


def complete_my_task(user, task_number):
    """Complete a task only when the authenticated user is its creator.

    This deliberately does not use the broader HOD override rule from the
    generic end_task tool because the AI command is explicitly a "my task"
    action and must verify creator ownership first.
    """
    number = _parse_task_number(task_number)
    if number is None:
        return {"error": "Invalid task number format."}

    from .workspace_tools import _find_task
    task, find_error = _find_task(user, task_number)
    if task is None:
        return {"error": find_error}
    if task.creator_id != user.id:
        return {"error": "You did not create this task, so I cannot complete it for you."}

    try:
        updated = _end_task(task, user)
    except WorkspaceError as exc:
        return {"error": exc.message, "code": exc.code}
    return {"success": True, "task_number": updated.display_number, "status": updated.status}


def start_my_task(user, task_number):
    """Start a task the authenticated user created or is assigned to."""
    number = _parse_task_number(task_number)
    if number is None:
        return {"error": "Invalid task number format."}
    from .workspace_tools import _find_task
    task, find_error = _find_task(user, task_number)
    if task is None:
        return {"error": find_error}
    try:
        updated = _start_task(task, user)
    except WorkspaceError as exc:
        return {"error": exc.message, "code": exc.code}
    return {"success": True, "task_number": updated.display_number, "status": updated.status}


def _hod_teams(user):
    """Return teams in departments the authenticated HOD is assigned to."""
    if user.role != User.Role.HOD:
        return Team.objects.none()
    department_ids = user.hod_departments.values_list("id", flat=True)
    legacy_department_id = getattr(user, "department_headed_id", None)
    qs = Team.objects.filter(department_id__in=department_ids)
    if legacy_department_id:
        qs = qs | Team.objects.filter(department_id=legacy_department_id)
    return qs.distinct()


def _resolve_hod_team(user, team_name):
    if user.role != User.Role.HOD:
        return None, {"error": "Only an HOD can use this team action."}
    target = " ".join(str(team_name or "").strip().lower().split())
    if not target:
        teams = list(_hod_teams(user).order_by("name"))
        if len(teams) == 1:
            return teams[0], None
        if len(teams) == 0:
            return None, {"error": "You do not have any team assigned to your department."}
        return None, {"error": "Please specify the team name because you manage multiple teams."}
    teams = list(_hod_teams(user).filter(name__iexact=str(team_name).strip()).order_by("id")[:6])
    if not teams:
        teams = [t for t in _hod_teams(user) if " ".join(t.name.lower().split()) == target][:6]
    if not teams:
        return None, {"error": f"I could not find an accessible team named '{team_name}'."}
    if len(teams) > 1:
        return None, {"error": f"More than one accessible team matches '{team_name}'. Please specify the exact team name."}
    return teams[0], None


def _team_leave_queryset(user, team_name=None, days=10, employee_names=None):
    team, error = _resolve_hod_team(user, team_name)
    if error:
        return None, error, None
    from django.utils import timezone
    start = timezone.localdate()
    end = start + timedelta(days=days)
    qs = LeaveRequest.objects.filter(
        employee__role=User.Role.EMPLOYEE,
        employee__team_memberships__team=team,
        status__in=[LeaveRequest.Status.PENDING, LeaveRequest.Status.APPROVED],
        from_date__lte=end,
        to_date__gte=start,
    ).select_related("employee", "leave_type").order_by("from_date", "employee__first_name", "id").distinct()
    if employee_names:
        normalized = {" ".join(str(n).lower().split()) for n in employee_names if str(n).strip()}
        usernames = {str(n).strip().lower() for n in employee_names if str(n).strip()}
        qs = qs.filter(employee__status=User.Status.ACTIVE)
        matches=[]
        for employee in User.objects.filter(team_memberships__team=team, role=User.Role.EMPLOYEE, status=User.Status.ACTIVE).distinct():
            full = " ".join((employee.get_full_name() or "").lower().split())
            if employee.username.lower() in usernames or full in normalized:
                matches.append(employee.id)
        qs = qs.filter(employee_id__in=matches)
    return qs, None, team


def get_team_leave_schedule(user, team_name=None, days=10):
    """Return upcoming employee leave for one explicitly scoped HOD team."""
    try:
        days = max(1, min(int(days), 31))
    except (TypeError, ValueError):
        days = 10
    qs, error, team = _team_leave_queryset(user, team_name, days)
    if error:
        return error
    return {
        "team": team.name,
        "days_checked": days,
        "requests": [
            {
                "id": r.id,
                "employee_name": r.employee.get_full_name() or r.employee.username,
                "employee_username": r.employee.username,
                "leave_type": r.leave_type.name,
                "from_date": str(r.from_date),
                "to_date": str(r.to_date),
                "days": r.days,
                "status": r.status,
                "reason": r.reason,
            }
            for r in qs
        ],
    }


def approve_team_leave(user, request_id):
    """Approve an employee leave request for the HOD's own department.
    Super Admin can approve HOD requests via the same underlying service.
    """
    try:
        request_id = int(request_id)
    except (TypeError, ValueError):
        return {"error": "Leave request id must be an integer."}
    leave_request = LeaveRequest.objects.filter(pk=request_id).select_related(
        "employee__employee_profile__department", "leave_type"
    ).first()
    if not leave_request:
        return {"error": "Leave request not found."}
    if user.role == User.Role.HOD:
        if leave_request.employee.role != User.Role.EMPLOYEE:
            return {"error": "An HOD can only approve employee leave requests."}
        department = getattr(getattr(leave_request.employee, "employee_profile", None), "department", None)
        if department is None or not is_hod_of(user, department):
            return {"error": "You are not the HOD for this employee's department."}
    elif user.role != User.Role.SUPER_ADMIN:
        return {"error": "You are not authorized to approve this leave request."}
    try:
        updated = approve_leave_request(leave_request, user)
    except LeaveError as exc:
        return {"error": exc.message, "code": exc.code}
    return {"success": True, "request_id": updated.id, "status": updated.status}


def reject_team_leave(user, request_id):
    """Reject an employee leave request using existing permission rules."""
    try:
        request_id = int(request_id)
    except (TypeError, ValueError):
        return {"error": "Leave request id must be an integer."}
    leave_request = LeaveRequest.objects.filter(pk=request_id).select_related(
        "employee__employee_profile__department", "leave_type"
    ).first()
    if not leave_request:
        return {"error": "Leave request not found."}
    if user.role == User.Role.HOD:
        if leave_request.employee.role != User.Role.EMPLOYEE:
            return {"error": "An HOD can only reject employee leave requests."}
        department = getattr(getattr(leave_request.employee, "employee_profile", None), "department", None)
        if department is None or not is_hod_of(user, department):
            return {"error": "You are not the HOD for this employee's department."}
    elif user.role != User.Role.SUPER_ADMIN:
        return {"error": "You are not authorized to reject this leave request."}
    try:
        updated = reject_leave_request(leave_request, user)
    except LeaveError as exc:
        return {"error": exc.message, "code": exc.code}
    return {"success": True, "request_id": updated.id, "status": updated.status}


def cancel_my_leave(user, request_id):
    """Cancel only the authenticated user's leave request."""
    try:
        request_id = int(request_id)
    except (TypeError, ValueError):
        return {"error": "Leave request id must be an integer."}
    leave_request = LeaveRequest.objects.filter(pk=request_id, employee=user).select_related("leave_type").first()
    if not leave_request:
        return {"error": "Leave request not found or it does not belong to you."}
    try:
        updated = cancel_leave_request(leave_request, user)
    except LeaveError as exc:
        return {"error": exc.message, "code": exc.code}
    return {"success": True, "request_id": updated.id, "leave_type": updated.leave_type.name, "from_date": str(updated.from_date), "to_date": str(updated.to_date), "days": updated.days, "status": updated.status}


@transaction.atomic
def cancel_team_leaves(user, team_name=None, days=10, confirm=False, request_ids=None, employee_names=None):
    """HOD-only bulk cancellation scoped to one team and optional exact employees."""
    if user.role != User.Role.HOD:
        return {"error": "Only an HOD can cancel team employee leaves."}
    if confirm is not True:
        return {"error": "Explicit confirmation is required before cancelling team leave requests.", "requires_confirmation": True}
    try:
        days = max(1, min(int(days), 31))
    except (TypeError, ValueError):
        days = 10

    ids = []
    if request_ids:
        try:
            ids = sorted({int(v) for v in request_ids})
        except (TypeError, ValueError):
            return {"error": "request_ids must contain only integer leave request IDs."}
        team, error = _resolve_hod_team(user, team_name)
        if error:
            return error
        qs = LeaveRequest.objects.filter(
            id__in=ids,
            employee__role=User.Role.EMPLOYEE,
            employee__team_memberships__team=team,
            status__in=[LeaveRequest.Status.PENDING, LeaveRequest.Status.APPROVED],
        ).select_related("employee", "leave_type").distinct().order_by("from_date", "id")
    else:
        qs, error, team = _team_leave_queryset(user, team_name, days, employee_names)
        if error:
            return error
        qs = qs

    frozen = list(qs.select_for_update())
    if request_ids and len(frozen) != len(ids):
        return {"error": "One or more selected leave requests changed or are no longer eligible. No leave was cancelled. Please prepare the preview again.", "code": "REQUEST_SCOPE_CHANGED"}
    if not frozen:
        return {"success": True, "team": team.name, "days_checked": days, "count": 0, "results": []}

    # Preflight every request before any side effect so the bulk operation is
    # all-or-nothing. This prevents a single stale request from causing a
    # confusing partial cancellation.
    results = []
    for leave_request in frozen:
        try:
            updated = cancel_leave_request(leave_request, user)
        except LeaveError as exc:
            raise LeaveError(exc.code, f"Bulk cancellation stopped before completion: {exc.message}") from exc
        results.append({
            "id": updated.id,
            "employee_name": updated.employee.get_full_name() or updated.employee.username,
            "leave_type": updated.leave_type.name,
            "from_date": str(updated.from_date),
            "to_date": str(updated.to_date),
            "days": updated.days,
            "status": updated.status,
        })
    return {
        "success": True,
        "team": team.name,
        "days_checked": days,
        "count": len(results),
        "results": results,
    }


@transaction.atomic
def notify_team_members(user, message, team_name=None):
    """Send a work notification only to members of one explicitly scoped HOD team."""
    if user.role != User.Role.HOD:
        return {"error": "Only an HOD can notify team members."}
    text = str(message or "").strip()
    if not text:
        return {"error": "Notification message is required."}
    team, error = _resolve_hod_team(user, team_name)
    if error:
        return error
    from notifications.services import notify
    from notifications.models import Notification
    recipients = User.objects.filter(
        status=User.Status.ACTIVE,
        role=User.Role.EMPLOYEE,
        team_memberships__team=team,
    ).distinct()
    count=0
    for recipient in recipients:
        notify(recipient=recipient, verb=Notification.Verb.ANNOUNCEMENT, title=f"Message from {team.name} HOD", message=text)
        count += 1
    return {"success": True, "team": team.name, "recipients": count}


def _accessible_teams(user):
    from teams.models import Team, TeamMembership
    if user.role == User.Role.SUPER_ADMIN:
        return Team.objects.all()
    if user.role == User.Role.HOD:
        department_ids = user.hod_departments.values_list("id", flat=True)
        return Team.objects.filter(department_id__in=department_ids)
    return Team.objects.filter(memberships__employee=user)


def _parse_task_number(value):
    if value is None:
        return None
    text = str(value).strip().upper().replace("TASK-", "")
    try:
        return int(text)
    except ValueError:
        return None


def _resolve_accessible_employee_for_notification(user, recipient_name):
    from .report_tools import _resolve_employee
    return _resolve_employee(user, recipient_name)


def create_notification(user, message, recipient_name=None, title="AI notification"):
    """Create an immediate in-app notification within the caller's allowed scope.

    Scheduling is deliberately unsupported because Notification has no scheduled
    timestamp; callers requesting a future reminder are rejected before writes.
    """
    text = " ".join(str(message or "").strip().split())
    if not text:
        return {"error": "Notification message is required."}
    title = " ".join(str(title or "AI notification").strip().split())[:200] or "AI notification"
    target_name = str(recipient_name or "").strip()
    recipient = user
    if target_name:
        recipient, error = _resolve_accessible_employee_for_notification(user, target_name)
        if error:
            return {"error": error}
    from notifications.models import Notification
    from notifications.services import notify
    notification = notify(
        recipient=recipient,
        verb=Notification.Verb.ANNOUNCEMENT,
        title=title,
        message=text,
    )
    return {"success": True, "notification_id": notification.id, "recipient": recipient.get_full_name() or recipient.username, "title": notification.title}


def update_issue_status(user, issue_number, new_status):
    from workspace.models import Issue
    from workspace.services import transition_issue_status
    from .workspace_tools import _user_teams
    target = str(issue_number or "").strip().upper().replace("ISSUE-", "")
    try:
        number = int(target)
    except (TypeError, ValueError):
        return {"error": "Invalid issue number format."}
    requested = str(new_status or "").strip().upper()
    if requested not in {Issue.Status.IN_PROGRESS, Issue.Status.RESOLVED}:
        return {"error": "Issue status must be IN_PROGRESS or RESOLVED."}
    issues = Issue.objects.filter(number=number, conversation__team__in=_user_teams(user)).select_related("conversation__team")
    if issues.count() > 1:
        return {"error": "More than one accessible issue has that number. Please specify the team."}
    issue = issues.first()
    if issue is None:
        return {"error": "Issue not found or you do not have access to it."}
    try:
        updated = transition_issue_status(issue, requested, user)
    except WorkspaceError as exc:
        return {"error": exc.message, "code": exc.code}
    return {"success": True, "issue_number": updated.display_number, "status": updated.status}
