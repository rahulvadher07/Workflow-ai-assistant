"""
Workspace business logic: conversation/issue/task creation and state
transitions. All permission checks here assume the caller has already
been verified as a team member/HOD by the view layer, except where a
specific role check is the actual point of the function (e.g. issue
resolution authority, task end authority).
"""

from django.db import transaction
from django.utils import timezone

from teams.models import TeamMembership, Team
from .models import Conversation, Issue, IssueMessage, Task


class WorkspaceError(Exception):
    def __init__(self, code, message):
        self.code = code
        self.message = message
        super().__init__(message)


def is_team_member(user, team):
    return TeamMembership.objects.filter(team=team, employee=user).exists()


def get_or_create_general_conversation(team, created_by):
    conv, _ = Conversation.objects.get_or_create(
        team=team,
        kind=Conversation.Kind.TEAM_GENERAL,
        defaults={"title": f"{team.name} - General", "created_by": created_by},
    )
    return conv


@transaction.atomic
def create_issue(team, created_by, title, description=""):
    team = Team.objects.select_for_update().get(pk=team.pk)
    conversation = Conversation.objects.create(
        team=team, kind=Conversation.Kind.ISSUE, title=title, created_by=created_by
    )
    number = Issue.next_number_for_team(team)
    issue = Issue.objects.create(
        conversation=conversation,
        number=number,
        title=title,
        description=description,
        lead=created_by,
        created_by=created_by,
    )
    return issue


def post_message(conversation, sender, text):
    return IssueMessage.objects.create(conversation=conversation, sender=sender, text=text)


@transaction.atomic
def transition_issue_status(issue, new_status, actor):
    """
    OPEN -> IN_PROGRESS: any team member.
    IN_PROGRESS -> RESOLVED: only the issue lead or the department HOD.
    No other transitions allowed (no skipping OPEN->RESOLVED, no re-opening).
    """
    issue = Issue.objects.select_for_update().get(pk=issue.pk)

    valid_transitions = {
        Issue.Status.OPEN: [Issue.Status.IN_PROGRESS],
        Issue.Status.IN_PROGRESS: [Issue.Status.RESOLVED],
    }

    if new_status not in valid_transitions.get(issue.status, []):
        code = "ISSUE_ALREADY_RESOLVED" if issue.status == Issue.Status.RESOLVED else "VALIDATION_ERROR"
        raise WorkspaceError(code, f"Cannot move issue from {issue.status} to {new_status}.")

    if new_status == Issue.Status.RESOLVED:
        from company.models import is_hod_of
        if actor.id != issue.lead_id and not is_hod_of(actor, issue.conversation.team.department):
            raise WorkspaceError(
                "FORBIDDEN", "Only the issue lead or department HOD can resolve this issue."
            )
        issue.resolved_at = timezone.now()

    issue.status = new_status
    issue.save(update_fields=["status", "resolved_at"] if new_status == Issue.Status.RESOLVED else ["status"])
    return issue


@transaction.atomic
def create_task(team, conversation, creator, description, assignee=None, deadline=None):
    """Create one task on a conversation, validating the assignee server-side."""
    # Lock the conversation before the OneToOne pre-check so two concurrent
    # requests cannot both pass the check and turn the second request into a
    # raw IntegrityError/500 response.
    conversation = Conversation.objects.select_for_update().select_related("team").get(pk=conversation.pk)
    team = Team.objects.select_for_update().get(pk=team.pk)
    if conversation.team_id != team.pk:
        raise WorkspaceError("VALIDATION_ERROR", "The conversation does not belong to this team.")

    if hasattr(conversation, "task"):
        raise WorkspaceError(
            "DUPLICATE_REQUEST", "This conversation already has a task. Create a new conversation for a new task."
        )

    if assignee is not None:
        from accounts.models import User
        if assignee.status != User.Status.ACTIVE or not assignee.is_active:
            raise WorkspaceError("VALIDATION_ERROR", "The selected assignee is inactive.")
        if assignee.role != User.Role.EMPLOYEE:
            raise WorkspaceError("VALIDATION_ERROR", "Tasks can only be assigned to active employees.")
        if not TeamMembership.objects.filter(team=team, employee=assignee).exists():
            raise WorkspaceError("VALIDATION_ERROR", "The selected assignee is not a member of this team.")
    number = Task.next_number_for_team(team)
    task = Task.objects.create(
        conversation=conversation,
        number=number,
        creator=creator,
        assignee=assignee,
        description=description,
        deadline=deadline,
    )

    if assignee and assignee.id != creator.id:
        from notifications.services import notify
        from notifications.models import Notification
        notify(
            recipient=assignee,
            verb=Notification.Verb.TASK_ASSIGNED,
            title=f"{task.display_number} assigned to you",
            message=description[:150],
            related_object=task,
        )

    return task


def _can_manage_task(actor, task):
    from company.models import is_hod_of
    return actor.id == task.creator_id or is_hod_of(actor, task.conversation.team.department)


@transaction.atomic
def start_task(task, actor):
    """Move one task from PENDING to IN_PROGRESS when the actor is authorized.

    A completed/already-started task is rejected; creator/HOD/assignee access is
    enforced by the existing service and the start timestamp is server-generated.
    """
    task = Task.objects.select_for_update().get(pk=task.pk)
    if task.status != Task.Status.PENDING:
        raise WorkspaceError("TASK_ALREADY_COMPLETED" if task.status == Task.Status.COMPLETED else "VALIDATION_ERROR",
                              f"Task is already {task.status}.")
    if not _can_manage_task(actor, task) and actor.id != task.assignee_id:
        raise WorkspaceError("FORBIDDEN", "You are not authorized to start this task.")

    task.status = Task.Status.IN_PROGRESS
    task.started_at = timezone.now()
    task.save(update_fields=["status", "started_at"])
    return task


@transaction.atomic
def end_task(task, actor):
    """Move one IN_PROGRESS task to COMPLETED using existing permissions only.

    The backend rejects tasks that are not in progress and never trusts an AI-
    supplied status value.
    """
    task = Task.objects.select_for_update().get(pk=task.pk)
    if task.status != Task.Status.IN_PROGRESS:
        raise WorkspaceError(
            "TASK_ALREADY_COMPLETED" if task.status == Task.Status.COMPLETED else "VALIDATION_ERROR",
            f"Task is not in progress (current status: {task.status}).",
        )
    if not _can_manage_task(actor, task):
        raise WorkspaceError(
            "FORBIDDEN", "Only the task creator or department HOD can end this task."
        )

    task.status = Task.Status.COMPLETED
    task.completed_at = timezone.now()
    task.save(update_fields=["status", "completed_at"])
    return task


# --- AI duplicate-detection integration boundary (Part 5 scope: stub only) ---

@transaction.atomic
def assign_task(task, actor, assignee):
    """Assign exactly one accessible task to exactly one active team member.

    Existing creator/HOD authorization and team-membership checks remain final;
    reassignment sends the existing assignment notification.
    """
    """Assign a task to a member of its team; actor must be creator or HOD."""
    task = Task.objects.select_for_update().select_related("conversation__team", "assignee").get(pk=task.pk)
    if not _can_manage_task(actor, task):
        raise WorkspaceError("FORBIDDEN", "Only the task creator or department HOD can assign this task.")
    team = task.conversation.team
    if not is_team_member(assignee, team):
        raise WorkspaceError("VALIDATION_ERROR", "The selected person is not a member of this team.")
    if assignee.is_active is False:
        raise WorkspaceError("VALIDATION_ERROR", "The selected person is inactive.")
    if task.assignee_id == assignee.id:
        return task

    task.assignee = assignee
    task.save(update_fields=["assignee"])

    from notifications.services import notify
    from notifications.models import Notification
    notify(
        recipient=assignee,
        verb=Notification.Verb.TASK_ASSIGNED,
        title=f"{task.display_number} assigned to you",
        message=task.description[:150],
        related_object=task,
    )
    return task


@transaction.atomic
def update_task_deadline(task, actor, deadline):
    """Update one non-completed task deadline through the existing service.

    The AI may parse natural language, but the backend enforces authorization and
    refuses deadline changes for completed tasks.
    """
    """Change a task deadline; only creator or department HOD may do so."""
    task = Task.objects.select_for_update().select_related("conversation__team").get(pk=task.pk)
    if not _can_manage_task(actor, task):
        raise WorkspaceError("FORBIDDEN", "Only the task creator or department HOD can change this task deadline.")
    if task.status == Task.Status.COMPLETED:
        raise WorkspaceError("VALIDATION_ERROR", "A completed task cannot have its deadline changed.")
    task.deadline = deadline
    task.save(update_fields=["deadline"])
    return task


def find_similar_issues(team, text):
    """
    Boundary function for AI duplicate-issue detection. Currently
    performs a plain substring/icontains search over this team's issue
    titles as the candidate-retrieval step (architecture.md section 12);
    the AI part (ai/duplicate_detection.py) sends these candidates to
    Groq for the actual similarity judgment.

    Deliberately does NOT exclude RESOLVED issues - a resolved issue is
    exactly the kind of match duplicate detection needs to surface (see
    architecture.md's own example: "ISSUE-007 - Login API Error,
    Status: RESOLVED"). The future Postgres migration will replace the
    icontains search with SearchVector/pg_trgm, per architecture.md;
    this function signature is the integration point it builds on.
    """
    return list(
        Issue.objects.filter(conversation__team=team, title__icontains=text[:50])
        .order_by("-created_at")[:5]
    )
