"""
HOD Daily Brief - plain Python/template aggregation of structured
backend data. Deliberately no LLM call (per architecture.md and
this Part's explicit instruction: AI is not the source of truth here).
"""

from datetime import timedelta

from django.db.models import Q
from django.utils import timezone

from attendance.models import AttendanceDay
from leave.models import LeaveRequest
from workspace.models import Issue, Task


def build_daily_brief(hod):
    """
    Returns structured data scoped strictly to `hod`'s own department -
    never includes other departments' employees or data.
    """
    department = getattr(getattr(hod, "employee_profile", None), "department", None)
    from company.models import is_hod_of
    if department is None or not is_hod_of(hod, department):
        return None

    today = timezone.localdate()
    now = timezone.now()
    team_ids = list(department.teams.values_list("id", flat=True))

    pending_issues = Issue.objects.filter(
        conversation__team_id__in=team_ids, status__in=[Issue.Status.OPEN, Issue.Status.IN_PROGRESS]
    ).select_related("conversation__team")

    escalated_issues = pending_issues.filter(escalated_at__isnull=False)

    attendance_problems = AttendanceDay.objects.filter(
        employee__employee_profile__department=department, date=today
    ).filter(Q(is_late=True) | Q(status=AttendanceDay.Status.INCOMPLETE)).select_related("employee")

    todays_leaves = LeaveRequest.objects.filter(
        employee__employee_profile__department=department,
        status=LeaveRequest.Status.APPROVED,
        from_date__lte=today,
        to_date__gte=today,
    ).select_related("employee", "leave_type")

    overdue_tasks = Task.objects.filter(
        conversation__team_id__in=team_ids, deadline__lt=now
    ).exclude(status=Task.Status.COMPLETED).select_related("conversation__team")

    resolved_yesterday_count = Issue.objects.filter(
        conversation__team_id__in=team_ids,
        status=Issue.Status.RESOLVED,
        resolved_at__date=today - timedelta(days=1),
    ).count()

    return {
        "department": department.name,
        "date": str(today),
        "pending_issues": [
            {"issue_number": i.display_number, "title": i.title, "team": i.conversation.team.name}
            for i in pending_issues
        ],
        "escalated_issues": [
            {"issue_number": i.display_number, "title": i.title} for i in escalated_issues
        ],
        "attendance_problems": [
            {
                "employee": a.employee.get_full_name() or a.employee.username,
                "issue": "Late" if a.is_late else "Incomplete Punch",
            }
            for a in attendance_problems
        ],
        "todays_leaves": [
            {"employee": l.employee.get_full_name() or l.employee.username, "leave_type": l.leave_type.name}
            for l in todays_leaves
        ],
        "overdue_tasks": [
            {"task_number": t.display_number, "description": t.description, "team": t.conversation.team.name}
            for t in overdue_tasks
        ],
        "resolved_yesterday_count": resolved_yesterday_count,
    }


def format_brief_text(brief):
    """Plain-text template matching architecture.md's example shape."""
    if brief is None:
        return ""

    lines = ["Good Morning \U0001F44B", "", f"{brief['department']} Daily Brief", ""]
    lines.append(f"\U0001F534 {len(brief['pending_issues'])} pending issues")
    lines.append(f"\u26A0\uFE0F {len(brief['escalated_issues'])} escalated issue(s)")
    lines.append(f"\U0001F552 {len(brief['attendance_problems'])} attendance problem(s)")
    lines.append(f"\U0001F3D6\uFE0F {len(brief['todays_leaves'])} employee(s) on leave today")
    lines.append(f"\u23F0 {len(brief['overdue_tasks'])} overdue task(s)")
    lines.append(f"\U0001F7E2 {brief['resolved_yesterday_count']} issue(s) resolved yesterday")
    return "\n".join(lines)
