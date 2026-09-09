from datetime import date as date_cls

from leave.models import LeaveRequest
from leave.services import create_leave_request as _create_leave_request, get_leave_balances, LeaveError


def get_my_leave_balance(user):
    """Return only the authenticated caller's leave balances.

    HOD and Employee are both normal User records in this application, so the
    underlying leave service intentionally receives the authenticated user
    directly. No role-specific filtering is applied here, and no user id can
    be supplied by the model.
    """
    return {"balances": get_leave_balances(user)}


def get_my_leave_history(user):
    requests = LeaveRequest.objects.filter(employee=user).order_by("-created_at")[:10]
    return {
        "requests": [
            {
                "leave_type": r.leave_type.name,
                "from_date": str(r.from_date),
                "to_date": str(r.to_date),
                "days": r.days,
                "status": r.status,
                "reason": r.reason,
            }
            for r in requests
        ]
    }


def create_leave_request(user, leave_type, from_date, to_date, reason):
    """
    leave_type: e.g. 'EL', 'CL', 'Paid Leave'
    from_date/to_date: 'YYYY-MM-DD' strings
    employee is always `user` (the real authenticated caller) - never an
    id argument the model could supply, so this can never act on someone
    else's behalf.
    The AI orchestrator invokes this tool only after its exact leave payload
    has been previewed and explicitly confirmed in the same conversation.
    """
    try:
        from_d = date_cls.fromisoformat(from_date)
        to_d = date_cls.fromisoformat(to_date)
    except (ValueError, TypeError):
        return {"error": "Dates must be in YYYY-MM-DD format."}

    try:
        request = _create_leave_request(user, leave_type, from_d, to_d, reason)
    except LeaveError as e:
        return {"error": e.message, "code": e.code}

    from accounts.models import User
    if user.role == User.Role.HOD:
        return {
            "success": True,
            "leave_type": request.leave_type.name,
            "from_date": str(request.from_date),
            "to_date": str(request.to_date),
            "days": request.days,
            "status": request.status,
            "sent_to_admin": True,
            "approval_recipient": "Super Admin",
        }

    department = user.employee_profile.department
    hod_name = ", ".join(department.hods.values_list("first_name", flat=True)) or (department.hod.get_full_name() if department.hod else "the department HOD")

    return {
        "success": True,
        "leave_type": request.leave_type.name,
        "from_date": str(request.from_date),
        "to_date": str(request.to_date),
        "days": request.days,
        "status": request.status,
        "sent_to_hod": hod_name,
        "sent_to_admin": False,
    }
