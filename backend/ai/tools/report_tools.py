"""Deterministic, permission-aware read/report adapters for the AI assistant.

These functions deliberately contain no writes. They aggregate authoritative
Django model data so Groq never has to invent or perform HR arithmetic.
"""
from __future__ import annotations

import calendar
import re
from datetime import date, datetime, timedelta
from decimal import Decimal

from django.db.models import Q
from django.utils import timezone

from accounts.models import User
from attendance.models import AttendanceDay
from company.models import Company, CompanyRule, Department, PayrollRule, is_hod_of
from leave.models import LeaveRequest
from payroll.models import Payslip
from teams.models import Team, TeamMembership
from workspace.models import Task, Issue


def _clean(value):
    return " ".join(str(value or "").strip().lower().split())


def _role(user):
    return str(getattr(user, "role", ""))


def _managed_departments(user):
    if _role(user) != User.Role.HOD:
        return Department.objects.none()
    ids = list(user.hod_departments.values_list("id", flat=True))
    legacy = getattr(user, "department_headed_id", None)
    if legacy:
        ids.append(legacy)
    return Department.objects.filter(id__in=set(ids)).distinct()


def _managed_teams(user):
    if _role(user) == User.Role.SUPER_ADMIN:
        return Team.objects.select_related("department").all()
    if _role(user) == User.Role.HOD:
        return Team.objects.select_related("department").filter(department__in=_managed_departments(user))
    return Team.objects.none()


def _resolve_team(user, team_name=None):
    qs = _managed_teams(user)
    target = _clean(team_name)
    if not target:
        teams = list(qs.order_by("name"))
        if len(teams) == 1:
            return teams[0], None
        if not teams:
            return None, "I couldn't find an accessible team."
        return None, "Please specify the team name because you have access to multiple teams."
    exact = list(qs.filter(name__iexact=str(team_name).strip()).order_by("id")[:6])
    if not exact:
        exact = [t for t in qs if _clean(t.name) == target][:6]
    if not exact:
        return None, f"I couldn't find an accessible team named '{team_name}'."
    if len(exact) > 1:
        return None, f"More than one accessible team matches '{team_name}'. Please specify the exact team name."
    return exact[0], None


def _resolve_employee(user, employee_name):
    target = _clean(employee_name)
    if not target:
        return None, "Employee name is required."
    if _role(user) == User.Role.EMPLOYEE:
        if target in {_clean(user.get_full_name()), _clean(user.username)}:
            return user, None
        return None, "You can only access your own employee data."

    qs = User.objects.filter(status=User.Status.ACTIVE, role=User.Role.EMPLOYEE).select_related("employee_profile__department")
    if _role(user) == User.Role.HOD:
        qs = qs.filter(employee_profile__department__in=_managed_departments(user))
    exact = qs.filter(username__iexact=str(employee_name).strip()).first()
    if exact:
        return exact, None
    candidates = list(qs.filter(Q(first_name__iexact=str(employee_name).strip()) | Q(last_name__iexact=str(employee_name).strip()))[:10])
    if not candidates:
        candidates = [u for u in qs if _clean(u.get_full_name()) == target or target in _clean(u.get_full_name())]
    if not candidates:
        return None, f"I couldn't find an accessible active employee named '{employee_name}'."
    if len(candidates) > 1:
        names = ", ".join(u.get_full_name() or u.username for u in candidates[:6])
        return None, f"More than one employee matches '{employee_name}': {names}. Please specify the username."
    return candidates[0], None


def resolve_date_range(value=None, start_date=None, end_date=None):
    """Return an inclusive (start, end) date range. Raises ValueError on ambiguity."""
    today = timezone.localdate()
    if start_date or end_date:
        if not (start_date and end_date):
            raise ValueError("Both start_date and end_date are required for a custom range.")
        start = _parse_date(start_date)
        end = _parse_date(end_date)
        if end < start:
            raise ValueError("The end date cannot be before the start date.")
        return start, end
    text = _clean(value) or "today"
    if text in {"today", "current day"}:
        return today, today
    if text == "yesterday":
        d = today - timedelta(days=1)
        return d, d
    if text == "tomorrow":
        d = today + timedelta(days=1)
        return d, d
    if text in {"this week", "current week"}:
        start = today - timedelta(days=today.weekday())
        return start, start + timedelta(days=6)
    if text == "last week":
        start = today - timedelta(days=today.weekday() + 7)
        return start, start + timedelta(days=6)
    if text == "next week":
        start = today - timedelta(days=today.weekday()) + timedelta(days=7)
        return start, start + timedelta(days=6)
    if text in {"this month", "current month"}:
        start = today.replace(day=1)
        return start, today.replace(day=calendar.monthrange(today.year, today.month)[1])
    if text == "last month":
        first = today.replace(day=1) - timedelta(days=1)
        start = first.replace(day=1)
        return start, first
    if text == "next month":
        first = today.replace(day=1) + timedelta(days=calendar.monthrange(today.year, today.month))
        return first, first.replace(day=calendar.monthrange(first.year, first.month)[1])
    if text == "current year":
        return date(today.year, 1, 1), date(today.year, 12, 31)
    m = re.fullmatch(r"last (\d+) days?", text)
    if m:
        days = int(m.group(1))
        if not 1 <= days <= 366:
            raise ValueError("Date range must be between 1 and 366 days.")
        return today - timedelta(days=days - 1), today
    m = re.fullmatch(r"next (\d+) days?", text)
    if m:
        days = int(m.group(1))
        if not 1 <= days <= 366:
            raise ValueError("Date range must be between 1 and 366 days.")
        return today, today + timedelta(days=days - 1)
    m = re.fullmatch(r"(\d{4})-(\d{1,2})", text)
    if m:
        y, mo = int(m.group(1)), int(m.group(2))
        if not 1 <= mo <= 12:
            raise ValueError("Invalid month.")
        return date(y, mo, 1), date(y, mo, calendar.monthrange(y, mo)[1])
    m = re.fullmatch(r"(?:from )?(.+?) to (.+)", text)
    if m:
        start, end = _parse_date(m.group(1)), _parse_date(m.group(2))
        if end < start:
            raise ValueError("The end date cannot be before the start date.")
        return start, end
    try:
        d = _parse_date(text)
    except ValueError:
        raise ValueError("I couldn't understand that date range. Use a date, month, or range such as '12/09/2026 to 16/09/2026'.")
    return d, d


def _parse_date(value):
    if isinstance(value, date):
        return value
    text = _clean(value)
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d", "%d %B %Y", "%d %b %Y", "%B %d %Y", "%b %d %Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            pass
    raise ValueError(f"Invalid date: {value}")


def _attendance_rows(employee, start, end):
    return list(AttendanceDay.objects.filter(employee=employee, date__range=(start, end)).order_by("date"))


def _attendance_summary(days, start, end):
    total_minutes = sum(int(d.total_minutes or 0) for d in days)
    overtime = sum(int(d.overtime_minutes or 0) for d in days)
    present = sum(d.status == AttendanceDay.Status.PRESENT for d in days)
    incomplete = sum(d.status == AttendanceDay.Status.INCOMPLETE for d in days)
    late = sum(bool(d.is_late) for d in days)
    absent = sum(d.status == AttendanceDay.Status.ABSENT for d in days)
    return {
        "start_date": str(start), "end_date": str(end), "calendar_days": (end - start).days + 1,
        "recorded_days": len(days), "present_days": present, "absent_days": absent,
        "incomplete_or_missed_punch_days": incomplete, "late_days": late,
        "attendance_percentage": round((present / (present + absent + incomplete)) * 100, 2) if (present + absent + incomplete) else 0.0,
        "total_working_minutes": total_minutes, "total_working_hours": round(total_minutes / 60, 2),
        "average_daily_working_hours": round((total_minutes / 60) / len(days), 2) if days else 0.0,
        "overtime_minutes": overtime, "overtime_hours": round(overtime / 60, 2),
        "first_punch": days[0].first_in.isoformat() if days and days[0].first_in else None,
        "last_punch": days[-1].last_out.isoformat() if days and days[-1].last_out else None,
        "early_checkout_days": None,
        "early_checkout_note": "Not available because the attendance model has no early-checkout field.",
    }


def get_my_attendance_report(user, date_range="today", start_date=None, end_date=None):
    try:
        start, end = resolve_date_range(date_range, start_date, end_date)
    except ValueError as exc:
        return {"error": str(exc)}
    return {"employee": user.get_full_name() or user.username, **_attendance_summary(_attendance_rows(user, start, end), start, end)}


def get_employee_attendance_report(user, employee_name, date_range="today", start_date=None, end_date=None):
    employee, error = _resolve_employee(user, employee_name)
    if error: return {"error": error}
    try: start, end = resolve_date_range(date_range, start_date, end_date)
    except ValueError as exc: return {"error": str(exc)}
    return {"employee": employee.get_full_name() or employee.username, **_attendance_summary(_attendance_rows(employee, start, end), start, end)}


def get_team_attendance_report(user, team_name, date_range="today", start_date=None, end_date=None):
    team, error = _resolve_team(user, team_name)
    if error: return {"error": error}
    try: start, end = resolve_date_range(date_range, start_date, end_date)
    except ValueError as exc: return {"error": str(exc)}
    members = User.objects.filter(status=User.Status.ACTIVE, team_memberships__team=team).distinct()
    rows = []
    for employee in members.order_by("first_name", "last_name", "username"):
        rows.append({"employee": employee.get_full_name() or employee.username, **_attendance_summary(_attendance_rows(employee, start, end), start, end)})
    return {"team": team.name, "start_date": str(start), "end_date": str(end), "members": rows}


def _leave_summary(qs, start=None, end=None):
    rows = list(qs.select_related("leave_type", "employee").order_by("from_date", "id"))
    return {
        "count": len(rows),
        "total_days": sum(r.days for r in rows),
        "pending": sum(r.status == LeaveRequest.Status.PENDING for r in rows),
        "approved": sum(r.status == LeaveRequest.Status.APPROVED for r in rows),
        "rejected": sum(r.status == LeaveRequest.Status.REJECTED for r in rows),
        "cancelled": sum(r.status == LeaveRequest.Status.CANCELLED for r in rows),
        "requests": [{"id": r.id, "employee": r.employee.get_full_name() or r.employee.username, "leave_type": r.leave_type.name, "from_date": str(r.from_date), "to_date": str(r.to_date), "days": r.days, "status": r.status} for r in rows],
    }


def get_my_leave_report(user, date_range="this month", start_date=None, end_date=None):
    try: start, end = resolve_date_range(date_range, start_date, end_date)
    except ValueError as exc: return {"error": str(exc)}
    qs = LeaveRequest.objects.filter(employee=user, from_date__lte=end, to_date__gte=start)
    return {"employee": user.get_full_name() or user.username, "start_date": str(start), "end_date": str(end), **_leave_summary(qs)}


def get_employee_leave_report(user, employee_name, date_range="this month", start_date=None, end_date=None):
    employee, error = _resolve_employee(user, employee_name)
    if error: return {"error": error}
    try: start, end = resolve_date_range(date_range, start_date, end_date)
    except ValueError as exc: return {"error": str(exc)}
    qs = LeaveRequest.objects.filter(employee=employee, from_date__lte=end, to_date__gte=start)
    return {"employee": employee.get_full_name() or employee.username, "start_date": str(start), "end_date": str(end), **_leave_summary(qs)}


def get_team_leave_report(user, team_name, date_range="this month", start_date=None, end_date=None):
    team, error = _resolve_team(user, team_name)
    if error: return {"error": error}
    try: start, end = resolve_date_range(date_range, start_date, end_date)
    except ValueError as exc: return {"error": str(exc)}
    qs = LeaveRequest.objects.filter(employee__team_memberships__team=team, from_date__lte=end, to_date__gte=start).distinct()
    return {"team": team.name, "start_date": str(start), "end_date": str(end), **_leave_summary(qs)}


def _task_queryset_for_user(user):
    return Task.objects.filter(Q(creator=user) | Q(assignee=user)).select_related("conversation__team", "creator", "assignee").distinct()


def get_my_task_report(user, date_range="this week", start_date=None, end_date=None, status=None, overdue_only=False):
    try: start, end = resolve_date_range(date_range, start_date, end_date)
    except ValueError as exc: return {"error": str(exc)}
    qs = _task_queryset_for_user(user)
    if status:
        qs = qs.filter(status=str(status).upper())
    if overdue_only:
        now = timezone.now()
        qs = qs.filter(deadline__lt=now).exclude(status=Task.Status.COMPLETED)
    else:
        qs = qs.filter(deadline__date__range=(start, end))
    rows = list(qs.order_by("deadline", "id"))
    return {"start_date": str(start), "end_date": str(end), "count": len(rows), "completed": sum(r.status == Task.Status.COMPLETED for r in rows), "pending": sum(r.status != Task.Status.COMPLETED for r in rows), "overdue": sum(bool(r.deadline and r.deadline < timezone.now() and r.status != Task.Status.COMPLETED) for r in rows), "tasks": [{"task_number": r.display_number, "description": r.description, "status": r.status, "deadline": r.deadline.isoformat() if r.deadline else None, "team": r.conversation.team.name} for r in rows]}


def get_team_task_report(user, team_name, date_range="this week", start_date=None, end_date=None, overdue_only=False):
    team, error = _resolve_team(user, team_name)
    if error: return {"error": error}
    try: start, end = resolve_date_range(date_range, start_date, end_date)
    except ValueError as exc: return {"error": str(exc)}
    qs = Task.objects.filter(conversation__team=team).select_related("conversation__team", "creator", "assignee")
    if overdue_only:
        qs = qs.filter(deadline__lt=timezone.now()).exclude(status=Task.Status.COMPLETED)
    else:
        qs = qs.filter(deadline__date__range=(start, end))
    rows = list(qs.order_by("deadline", "id"))
    return {"team": team.name, "start_date": str(start), "end_date": str(end), "count": len(rows), "completed": sum(r.status == Task.Status.COMPLETED for r in rows), "pending": sum(r.status != Task.Status.COMPLETED for r in rows), "overdue": sum(bool(r.deadline and r.deadline < timezone.now() and r.status != Task.Status.COMPLETED) for r in rows), "tasks": [{"task_number": r.display_number, "description": r.description, "status": r.status, "deadline": r.deadline.isoformat() if r.deadline else None, "assignee": (r.assignee.get_full_name() or r.assignee.username) if r.assignee else None} for r in rows]}


def get_team_members(user, team_name):
    team, error = _resolve_team(user, team_name)
    if error: return {"error": error}
    members = User.objects.filter(status=User.Status.ACTIVE, team_memberships__team=team).distinct().order_by("first_name", "last_name", "username")
    return {"team": team.name, "member_count": members.count(), "members": [{"name": m.get_full_name() or m.username, "username": m.username, "role": m.role} for m in members]}


def get_current_user_team_members(user):
    """List active members of the authenticated user's own team(s)."""
    memberships = TeamMembership.objects.filter(employee=user).select_related("team").order_by("team__name", "team__id")
    teams = [membership.team for membership in memberships]
    # HODs may not have an explicit membership row, so use their managed teams
    # only when that is the user's own operational scope.
    if not teams and _role(user) == User.Role.HOD:
        teams = list(_managed_teams(user).order_by("name", "id"))

    if not teams:
        return {"teams": [], "member_count": 0, "members": []}

    unique_teams = []
    seen_team_ids = set()
    for team in teams:
        if team.id not in seen_team_ids:
            seen_team_ids.add(team.id)
            unique_teams.append(team)

    members = User.objects.filter(
        status=User.Status.ACTIVE,
        team_memberships__team__in=unique_teams,
    ).distinct().order_by("first_name", "last_name", "username")

    team_payload = []
    for team in unique_teams:
        team_members = members.filter(team_memberships__team=team).distinct()
        team_payload.append({
            "team": team.name,
            "members": [
                {"name": member.get_full_name() or member.username, "username": member.username, "role": member.role}
                for member in team_members
            ],
        })

    return {
        "teams": team_payload,
        "member_count": sum(len(item["members"]) for item in team_payload),
        "members": [member for item in team_payload for member in item["members"]],
    }


def get_team_details(user, team_name):
    team, error = _resolve_team(user, team_name)
    if error: return {"error": error}
    return {"team": team.name, "team_id": team.id, "department": team.department.name, "member_count": TeamMembership.objects.filter(team=team, employee__status=User.Status.ACTIVE).count()}


def get_employee_details(user, employee_name):
    employee, error = _resolve_employee(user, employee_name)
    if error: return {"error": error}
    profile = getattr(employee, "employee_profile", None)
    teams = list(Team.objects.filter(memberships__employee=employee).values_list("name", flat=True).distinct())
    return {"name": employee.get_full_name() or employee.username, "username": employee.username, "role": employee.role, "status": employee.status, "department": profile.department.name if profile else None, "employee_code": profile.employee_code if profile else None, "phone": profile.phone if profile and profile.phone else None, "email": employee.email or None, "teams": teams}


def get_team_issue_report(user, team_name, status=None):
    team, error = _resolve_team(user, team_name)
    if error: return {"error": error}
    qs = Issue.objects.filter(conversation__team=team).select_related("conversation__team")
    if status: qs = qs.filter(status=str(status).upper())
    rows = list(qs.order_by("-created_at")[:100])
    return {"team": team.name, "count": len(rows), "open": sum(r.status == Issue.Status.OPEN for r in rows), "in_progress": sum(r.status == Issue.Status.IN_PROGRESS for r in rows), "resolved": sum(r.status == Issue.Status.RESOLVED for r in rows), "issues": [{"issue_number": r.display_number, "title": r.title, "status": r.status} for r in rows]}


def get_company_info(user):
    company = Company.get_solo()
    rule = PayrollRule.get_solo()
    return {"name": company.name, "shift_start_time": company.shift_start_time.isoformat(), "standard_shift_minutes": company.standard_shift_minutes, "standard_break_minutes": company.standard_break_minutes, "overtime_multiplier": str(rule.overtime_multiplier), "late_threshold_minutes": rule.late_threshold_minutes}


def list_departments(user):
    departments = Department.objects.all().order_by("name") if _role(user) == User.Role.SUPER_ADMIN else (_managed_departments(user) if _role(user) == User.Role.HOD else Department.objects.filter(id=getattr(getattr(user, "employee_profile", None), "department_id", None)))
    return {"departments": [{"name": d.name, "teams": list(d.teams.order_by("name").values_list("name", flat=True))} for d in departments]}


def _payroll_allowed(user, employee):
    if employee.id == user.id: return True
    if _role(user) == User.Role.SUPER_ADMIN: return True
    return _role(user) == User.Role.HOD and is_hod_of(user, employee.employee_profile.department)


def get_my_payroll_summary(user, date_range="this month"):
    try: start, end = resolve_date_range(date_range)
    except ValueError as exc: return {"error": str(exc)}
    periods = Payslip.objects.filter(employee=user, period__year__gte=start.year, period__year__lte=end.year)
    if _role(user) == User.Role.EMPLOYEE:
        periods = periods.filter(status=Payslip.Status.HOD_APPROVED)
    periods = periods.filter(
        Q(period__year__gt=start.year) | Q(period__year__gte=start.year, period__month__gte=start.month)
    ).filter(
        Q(period__year__lt=end.year) | Q(period__year__lte=end.year, period__month__lte=end.month)
    ).select_related("period").order_by("-period__year", "-period__month")
    return {"employee": user.get_full_name() or user.username, "payslips": [{"period": f"{p.period.year}-{p.period.month:02d}", "status": p.status, "gross_salary": str(p.gross_salary), "deductions": str(p.pf_deduction + p.other_deductions), "net_salary": str(p.net_salary), "worked_hours": round(p.total_worked_minutes / 60, 2), "overtime_hours": round(p.overtime_minutes / 60, 2)} for p in periods]}


def get_team_payroll_summary(user, team_name, date_range="this month"):
    team, error = _resolve_team(user, team_name)
    if error:
        return {"error": error}
    if _role(user) == User.Role.EMPLOYEE:
        return {"error": "Employees cannot access team payroll data."}
    try:
        start, end = resolve_date_range(date_range)
    except ValueError as exc:
        return {"error": str(exc)}
    employees = User.objects.filter(status=User.Status.ACTIVE, team_memberships__team=team).distinct()
    payslips = Payslip.objects.filter(
        employee__in=employees,
        period__year__gte=start.year,
        period__year__lte=end.year,
    ).filter(
        Q(period__year__gt=start.year) | Q(period__year__gte=start.year, period__month__gte=start.month)
    ).filter(
        Q(period__year__lt=end.year) | Q(period__year__lte=end.year, period__month__lte=end.month)
    ).select_related("employee", "period").order_by("-period__year", "-period__month")
    return {"team": team.name, "payslips": [{"employee": p.employee.get_full_name() or p.employee.username, "period": f"{p.period.year}-{p.period.month:02d}", "status": p.status, "gross_salary": str(p.gross_salary), "net_salary": str(p.net_salary), "overtime_hours": round(p.overtime_minutes / 60, 2)} for p in payslips]}
