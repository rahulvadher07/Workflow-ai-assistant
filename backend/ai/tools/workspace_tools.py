from django.db import transaction
from django.db.models import Q
from teams.models import Team, TeamMembership
from datetime import datetime, timedelta, time as time_cls
import re
from accounts.models import User
from workspace.models import Conversation, Issue, Task
from workspace.services import (
    WorkspaceError,
    create_issue as _create_issue,
    create_task as _create_task,
    start_task as _start_task,
    end_task as _end_task,
    assign_task as _assign_task,
    update_task_deadline as _update_task_deadline,
    find_similar_issues,
)


def _parse_number(value):
    """Parse a display number like 'TASK-012', 'ISSUE-007', or a bare '7'/'12'
    into its underlying per-team sequence integer. Returns None when the value
    cannot be parsed as a non-negative integer.
    """
    if value is None:
        return None
    text = str(value).strip().upper()
    text = re.sub(r"^(TASK|ISSUE)[-#:]?\s*", "", text)
    if not text.isdigit():
        return None
    return int(text)


def _can_access_team(user, team):
    if user.role == User.Role.SUPER_ADMIN:
        return True
    if user.role == User.Role.HOD:
        from company.models import is_hod_of
        return is_hod_of(user, team.department)
    return TeamMembership.objects.filter(team=team, employee=user).exists()


def _user_teams(user):
    if user.role == User.Role.SUPER_ADMIN:
        return Team.objects.all()
    if user.role == User.Role.HOD:
        from company.models import is_hod_of
        department_ids = user.hod_departments.values_list("id", flat=True)
        legacy_department_id = getattr(user, "department_headed_id", None)
        qs = Team.objects.filter(department_id__in=department_ids)
        if legacy_department_id:
            qs = qs | Team.objects.filter(department_id=legacy_department_id)
        return qs.distinct()
    return Team.objects.filter(memberships__employee=user)


def get_my_tasks(user):
    tasks = Task.objects.filter(creator=user) | Task.objects.filter(assignee=user)
    tasks = tasks.distinct().order_by("-created_at")[:10]
    return {
        "tasks": [
            {
                "task_number": t.display_number,
                "description": t.description,
                "status": t.status,
                "deadline": t.deadline.isoformat() if t.deadline else None,
            }
            for t in tasks
        ]
    }


def get_my_issues(user):
    team_ids = _user_teams(user).values_list("id", flat=True)
    issues = Issue.objects.filter(conversation__team_id__in=team_ids).order_by("-created_at")[:10]
    return {
        "issues": [
            {"issue_number": i.display_number, "title": i.title, "status": i.status}
            for i in issues
        ]
    }


def get_issue_details(user, issue_number):
    """issue_number: e.g. 'ISSUE-007' or '7'."""
    number = _parse_number(issue_number)
    if number is None:
        return {"error": "Invalid issue number format."}

    team_ids = _user_teams(user).values_list("id", flat=True)
    issue = Issue.objects.filter(conversation__team_id__in=team_ids, number=number).first()
    if issue is None:
        return {"error": "Issue not found or you do not have access to it."}

    return {
        "issue_number": issue.display_number,
        "title": issue.title,
        "description": issue.description,
        "status": issue.status,
        "lead": issue.lead.get_full_name() if issue.lead else None,
    }


def search_previous_issues(user, team_id, query):
    """
    team_id must correspond to a team the user actually belongs to -
    validated here, never trusted blindly from the model's argument.
    """
    team = Team.objects.select_related("department").filter(pk=team_id).first()
    if team is None or not _can_access_team(user, team):
        return {"error": "You do not have access to that team."}

    similar = find_similar_issues(team, query)
    return {
        "matches": [
            {"issue_number": i.display_number, "title": i.title, "status": i.status}
            for i in similar
        ]
    }


def create_task(user, team_id, description, assignee_username=None, deadline=None):
    team = Team.objects.filter(pk=team_id).first()
    if team is None or not _can_access_team(user, team):
        return {"error": "You do not have access to that team."}

    assignee = None
    if assignee_username:
        assignee, assignee_error = _resolve_team_member(team, assignee_username)
        if assignee_error:
            return {"error": assignee_error}

    parsed_deadline = _parse_deadline(deadline) if deadline else None
    if deadline and parsed_deadline is None:
        return {"error": "Deadline could not be understood. Use a date like 2026-09-12 or a phrase like next Friday 10 AM."}

    # AI-created tasks always get their own fresh conversation - the
    # general conversation may already have (or later get) a task, and
    # the one-task-per-conversation rule must hold, so never reuse it.
    conversation = Conversation.objects.create(
        team=team, kind=Conversation.Kind.TASK, title=f"Task: {description[:50]}", created_by=user
    )

    try:
        task = _create_task(team, conversation, creator=user, description=description, assignee=assignee, deadline=parsed_deadline)
    except WorkspaceError as e:
        return {"error": e.message, "code": e.code}

    return {
        "success": True,
        "team": team.name,
        "task_number": task.display_number,
        "description": task.description,
        "assignee": assignee.get_full_name() if assignee else None,
        "status": task.status,
    }



def _find_accessible_task(user, task_number, team_name=None):
    return _find_task(user, task_number, team_name=team_name)


def create_task_for_team(user, team_name, description, assignee_name=None, deadline=None):
    """Create a task using a team name, with the same access rules as create_task."""
    target = " ".join(str(team_name or "").strip().lower().split())
    if not target:
        return {"error": "Team name is required."}
    teams = list(_user_teams(user).filter(name__iexact=str(team_name).strip()).order_by("id")[:6])
    if not teams:
        teams = [t for t in _user_teams(user) if " ".join(t.name.lower().split()) == target][:6]
    if not teams:
        return {"error": f"I could not find an accessible team named '{team_name}'."}
    if len(teams) > 1:
        return {"error": f"More than one accessible team matches '{team_name}'. Please specify the exact team name."}
    team = teams[0]
    return create_task(
        user,
        team.id,
        description,
        assignee_username=assignee_name,
        deadline=deadline,
    )


def _resolve_team_member(team, name):
    """Resolve one active team member by username, full name, or unique partial name."""
    target = " ".join(str(name or "").strip().lower().split())
    if not target:
        return None, "Assignee name is required."
    members = User.objects.filter(
        status=User.Status.ACTIVE,
        team_memberships__team=team,
    ).distinct()
    exact_username = members.filter(username__iexact=target).first()
    if exact_username:
        return exact_username, None
    candidates = list(
        members.filter(
            Q(first_name__iexact=target) | Q(last_name__iexact=target)
        ).order_by("username")[:10]
    )
    if not candidates:
        candidates = [
            u for u in members
            if " ".join(u.get_full_name().lower().split()) == target
        ][:10]
    if not candidates:
        candidates = [
            u for u in members
            if target in " ".join(u.get_full_name().lower().split())
            or target in u.username.lower()
        ][:10]
    if not candidates:
        return None, f"I could not find an active team member named '{name}'."
    if len(candidates) > 1:
        names = ", ".join(f"{u.get_full_name() or u.username} (@{u.username})" for u in candidates)
        return None, f"More than one team member matches '{name}': {names}. Please specify the username."
    return candidates[0], None


def assign_task(user, task_number, assignee_name, team_name=None):
    """Assign an accessible task to one unambiguous active member of its team."""
    task, find_error = _find_accessible_task(user, task_number, team_name=team_name)
    if task is None:
        return {"error": find_error}
    assignee, assignee_error = _resolve_team_member(task.conversation.team, assignee_name)
    if assignee_error:
        return {"error": assignee_error}

    try:
        updated = _assign_task(task, user, assignee)
    except WorkspaceError as exc:
        return {"error": exc.message, "code": exc.code}
    return {
        "success": True,
        "task_number": updated.display_number,
        "team": task.conversation.team.name,
        "assignee": assignee.get_full_name() or assignee.username,
        "assignee_username": assignee.username,
        "deadline": updated.deadline.isoformat() if updated.deadline else None,
    }


@transaction.atomic
def update_task_assignment_and_deadline(user, task_number, assignee_name, deadline, team_name=None):
    """Atomically assign a task and update its deadline as one user-requested action."""
    task, find_error = _find_accessible_task(user, task_number, team_name=team_name)
    if task is None:
        return {"error": find_error}
    parsed = _parse_deadline(deadline)
    if parsed is None:
        return {"error": "Deadline could not be understood. Use a date like 2026-09-12 or a phrase like next Friday 10 AM."}
    assignee, assignee_error = _resolve_team_member(task.conversation.team, assignee_name)
    if assignee_error:
        return {"error": assignee_error}
    try:
        updated = _assign_task(task, user, assignee)
        updated = _update_task_deadline(updated, user, parsed)
    except WorkspaceError:
        raise
    return {
        "success": True,
        "task_number": updated.display_number,
        "team": task.conversation.team.name,
        "assignee": assignee.get_full_name() or assignee.username,
        "assignee_username": assignee.username,
        "deadline": updated.deadline.isoformat() if updated.deadline else None,
    }


def update_task_deadline(user, task_number, deadline, team_name=None):
    """Change an accessible non-completed task deadline."""
    task, find_error = _find_accessible_task(user, task_number, team_name=team_name)
    if task is None:
        return {"error": find_error}
    parsed = _parse_deadline(deadline)
    if parsed is None:
        return {"error": "Deadline could not be understood. Use a date like 2026-09-12 or a phrase like next Friday 10 AM."}
    try:
        updated = _update_task_deadline(task, user, parsed)
    except WorkspaceError as exc:
        return {"error": exc.message, "code": exc.code}
    return {
        "success": True,
        "task_number": updated.display_number,
        "deadline": updated.deadline.isoformat() if updated.deadline else None,
    }


def create_issue_for_team(user, team_name, title, description=""):
    """Create an issue in an accessible team selected by name."""
    target = " ".join(str(team_name or "").strip().lower().split())
    if not target:
        return {"error": "Team name is required."}
    teams = list(_user_teams(user).filter(name__iexact=team_name.strip()).order_by("id")[:6])
    if len(teams) == 0:
        teams = [t for t in _user_teams(user) if " ".join(t.name.lower().split()) == target][:6]
    if not teams:
        return {"error": f"I could not find an accessible team named '{team_name}'."}
    if len(teams) > 1:
        return {"error": f"More than one accessible team matches '{team_name}'. Please specify the exact team name."}
    team=teams[0]
    try:
        issue = _create_issue(team, created_by=user, title=title, description=description)
    except WorkspaceError as exc:
        return {"error": exc.message, "code": exc.code}
    return {"success": True, "issue_number": issue.display_number, "team": team.name, "title": issue.title, "status": issue.status}

def start_task(user, task_number):
    task, find_error = _find_task(user, task_number)
    if task is None:
        return {"error": find_error}
    try:
        updated = _start_task(task, user)
    except WorkspaceError as e:
        return {"error": e.message, "code": e.code}
    return {"success": True, "task_number": updated.display_number, "status": updated.status}


def end_task(user, task_number):
    task, find_error = _find_task(user, task_number)
    if task is None:
        return {"error": find_error}
    try:
        updated = _end_task(task, user)
    except WorkspaceError as e:
        return {"error": e.message, "code": e.code}
    return {"success": True, "task_number": updated.display_number, "status": updated.status}


def create_issue(user, team_id, title, description=""):
    team = Team.objects.select_related("department").filter(pk=team_id).first()
    if team is None or not _can_access_team(user, team):
        return {"error": "You do not have access to that team."}
    issue = _create_issue(team, created_by=user, title=title, description=description)
    return {"success": True, "issue_number": issue.display_number, "title": issue.title, "status": issue.status}


def _parse_deadline(value):
    """Parse ISO dates and common human deadlines into an aware local datetime.

    Supported examples include: tomorrow, next Friday, this Friday morning,
    Friday 10 AM, end of this week, and next Monday after lunch.
    """
    if value is None:
        return None
    from django.utils import timezone

    text = " ".join(str(value).strip().lower().split())
    if not text:
        return None
    today = timezone.localdate()

    # Handle common explicit month-name formats before relative parsing.
    for fmt in ("%B %d %Y", "%b %d %Y", "%d %B %Y", "%d %b %Y", "%B %d", "%b %d"):
        try:
            parsed_date = datetime.strptime(text, fmt)
            if fmt in ("%B %d", "%b %d"):
                parsed_date = parsed_date.replace(year=today.year)
            aware = timezone.make_aware(parsed_date.replace(hour=17, minute=0, second=0, microsecond=0))
            return aware if aware >= timezone.now() else None
        except ValueError:
            pass

    for candidate in (text.replace("z", "+00:00"), text):
        try:
            parsed = datetime.fromisoformat(candidate)
            if parsed.tzinfo is None:
                parsed = timezone.make_aware(parsed)
            return parsed if parsed >= timezone.now() else None
        except ValueError:
            pass

    base = None
    if re.search(r"\btomorrow\b", text):
        base = today + timedelta(days=1)
    elif re.search(r"\btoday\b", text):
        base = today
    elif re.search(r"\bend of (?:this|the) week\b", text):
        base = today + timedelta(days=6 - today.weekday())
    else:
        weekdays = {"monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3, "friday": 4, "saturday": 5, "sunday": 6}
        for name, idx in weekdays.items():
            if not re.search(r"\b" + name + r"\b", text):
                continue
            is_next = bool(re.search(r"\bnext\s+" + name + r"\b", text))
            is_this = bool(re.search(r"\bthis\s+" + name + r"\b", text))
            delta = (idx - today.weekday()) % 7
            if is_next:
                delta = delta + 7 if delta == 0 else delta + 7
            elif is_this:
                delta = delta
            elif delta == 0:
                delta = 7
            base = today + timedelta(days=delta)
            break

    if base is None:
        m_in = re.search(r"\bin\s+(\d+)\s+days?\b", text)
        if m_in:
            base = today + timedelta(days=int(m_in.group(1)))
    if base is None and re.search(r"\bnext\s+week\b", text):
        days_to_monday = (7 - today.weekday()) % 7 or 7
        base = today + timedelta(days=days_to_monday)
    if base is None and re.search(r"\bend of (?:this|the) month\b", text):
        import calendar
        base = today.replace(day=calendar.monthrange(today.year, today.month)[1])
    if base is None:
        match = re.search(r"\b(\d{1,2})[-/](\d{1,2})[-/](\d{4})\b", text)
        if match:
            try:
                base = date_cls(int(match.group(3)), int(match.group(2)), int(match.group(1)))
            except ValueError:
                return None
        else:
            match = re.search(r"\b(\d{4})[-/](\d{1,2})[-/](\d{1,2})\b", text)
            if match:
                try:
                    base = date_cls(int(match.group(1)), int(match.group(2)), int(match.group(3)))
                except ValueError:
                    return None

    if base is None:
        return None

    if re.search(r"\b(?:eod|end of day|close of business)\b", text):
        hour, minute = 17, 0
        time_match = None
    elif re.search(r"\bmidnight\b", text):
        hour, minute = 0, 0
        time_match = None
    elif re.search(r"\bnoon\b", text):
        hour, minute = 12, 0
        time_match = None
    else:
        time_match = re.search(r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b", text)
    if time_match:
        hour = int(time_match.group(1))
        minute = int(time_match.group(2) or 0)
        meridiem = time_match.group(3)
        if not 1 <= hour <= 12 or minute > 59:
            return None
        if meridiem == "pm" and hour != 12:
            hour += 12
        elif meridiem == "am" and hour == 12:
            hour = 0
    elif re.search(r"\b(?:after lunch|post lunch)\b", text):
        hour, minute = 14, 0
    elif re.search(r"\bbefore lunch\b", text):
        hour, minute = 12, 0
    else:
        dayparts = {"early morning": 8, "morning": 9, "late morning": 11, "afternoon": 15, "evening": 18, "night": 20}
        hour, minute = 17, 0
        for part, part_hour in sorted(dayparts.items(), key=lambda item: -len(item[0])):
            if re.search(r"\b" + re.escape(part) + r"\b", text):
                hour = part_hour
                break

    parsed = timezone.make_aware(datetime.combine(base, time_cls(hour, minute)))
    if parsed < timezone.now():
        return None
    return parsed


def _find_task(user, task_number, team_name=None):
    number = _parse_number(task_number)
    if number is None:
        return None, "Invalid task number format."
    teams_qs = _user_teams(user)
    if team_name:
        target = " ".join(str(team_name).lower().split())
        teams = list(teams_qs.filter(name__iexact=str(team_name).strip()).order_by("id")[:6])
        if not teams:
            teams = [t for t in teams_qs if " ".join(t.name.lower().split()) == target][:6]
        if not teams:
            return None, f"I could not find an accessible team named '{team_name}'."
        if len(teams) > 1:
            return None, f"More than one accessible team matches '{team_name}'."
        teams_qs = Team.objects.filter(pk=teams[0].pk)
    tasks = list(Task.objects.filter(conversation__team_id__in=teams_qs.values_list("id", flat=True), number=number).select_related("conversation__team", "creator", "assignee")[:3])
    if not tasks:
        return None, "Task not found or you do not have access to it."
    if len(tasks) > 1:
        names = ", ".join(t.conversation.team.name for t in tasks)
        return None, f"Task {tasks[0].display_number} exists in multiple accessible teams ({names}). Please specify the team name."
    return tasks[0], None


def update_task_description(user, task_number, description, team_name=None):
    task, find_error = _find_accessible_task(user, task_number, team_name=team_name)
    if task is None:
        return {"error": find_error}
    from workspace.services import update_task_description as _update_task_description
    try:
        updated = _update_task_description(task, user, description)
    except WorkspaceError as exc:
        return {"error": exc.message, "code": exc.code}
    return {"success": True, "task_number": updated.display_number, "description": updated.description, "status": updated.status}
