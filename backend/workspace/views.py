from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from teams.models import Team, TeamMembership
from .models import Conversation, Issue, IssueMessage, Task
from .serializers import (
    ConversationSerializer,
    IssueSerializer,
    IssueCreateSerializer,
    IssueStatusUpdateSerializer,
    IssueMessageSerializer,
    TaskSerializer,
    TaskCreateSerializer,
)
from .services import (
    WorkspaceError,
    is_team_member,
    get_or_create_general_conversation,
    create_issue,
    post_message,
    transition_issue_status,
    create_task,
    start_task,
    end_task,
)


def _can_access_team(user, team):
    if user.role == User.Role.SUPER_ADMIN:
        return True
    if user.role == User.Role.HOD:
        from company.models import is_hod_of
        return is_hod_of(user, team.department)
    return is_team_member(user, team)


def _get_team_or_403(user, team_id):
    team = Team.objects.filter(pk=team_id).select_related("department").first()
    if team is None:
        return None, Response(
            {"error": {"code": "NOT_FOUND", "message": "Team not found."}}, status=status.HTTP_404_NOT_FOUND
        )
    if not _can_access_team(user, team):
        return None, Response(
            {"error": {"code": "FORBIDDEN", "message": "You do not have access to this team."}},
            status=status.HTTP_403_FORBIDDEN,
        )
    return team, None


def _get_conversation_or_403(user, conversation_id):
    conv = Conversation.objects.filter(pk=conversation_id).select_related("team", "team__department").first()
    if conv is None:
        return None, Response(
            {"error": {"code": "NOT_FOUND", "message": "Conversation not found."}}, status=status.HTTP_404_NOT_FOUND
        )
    if not _can_access_team(user, conv.team):
        return None, Response(
            {"error": {"code": "FORBIDDEN", "message": "You do not have access to this conversation."}},
            status=status.HTTP_403_FORBIDDEN,
        )
    return conv, None


class TeamConversationListView(APIView):
    """List all conversations (general + issue chats) for a team."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, team_id):
        team, err = _get_team_or_403(request.user, team_id)
        if err:
            return err
        get_or_create_general_conversation(team, created_by=team.created_by)
        convs = Conversation.objects.filter(team=team).select_related("issue", "task").order_by("-created_at")
        return Response(ConversationSerializer(convs, many=True).data)


class ConversationMessageListView(APIView):
    """GET: list messages. POST: send a message."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, conversation_id):
        conv, err = _get_conversation_or_403(request.user, conversation_id)
        if err:
            return err
        messages = IssueMessage.objects.filter(conversation=conv).select_related("sender")
        return Response(IssueMessageSerializer(messages, many=True).data)

    def post(self, request, conversation_id):
        conv, err = _get_conversation_or_403(request.user, conversation_id)
        if err:
            return err
        text = request.data.get("text", "").strip()
        if not text:
            return Response(
                {"error": {"code": "VALIDATION_ERROR", "message": "Message text is required."}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        message = post_message(conv, request.user, text)
        # Real-time broadcast to WebSocket group happens via the consumer
        # when clients send through the WS connection; REST POST here
        # covers non-WS clients and still persists correctly.
        _broadcast_to_conversation(conv.id, IssueMessageSerializer(message).data)
        return Response(IssueMessageSerializer(message).data, status=status.HTTP_201_CREATED)


class IssueListCreateView(APIView):
    """GET: list issues for a team. POST: create a new issue (+ its conversation)."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, team_id):
        team, err = _get_team_or_403(request.user, team_id)
        if err:
            return err
        issues = Issue.objects.filter(conversation__team=team).order_by("-created_at")
        return Response(IssueSerializer(issues, many=True).data)

    def post(self, request, team_id):
        team, err = _get_team_or_403(request.user, team_id)
        if err:
            return err
        serializer = IssueCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        issue = create_issue(
            team,
            created_by=request.user,
            title=serializer.validated_data["title"],
            description=serializer.validated_data.get("description", ""),
        )
        return Response(IssueSerializer(issue).data, status=status.HTTP_201_CREATED)


class IssueStatusView(APIView):
    """PATCH: transition an issue's status (OPEN->IN_PROGRESS->RESOLVED)."""

    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, issue_id):
        issue = Issue.objects.filter(pk=issue_id).select_related(
            "conversation__team__department"
        ).first()
        if issue is None:
            return Response(
                {"error": {"code": "NOT_FOUND", "message": "Issue not found."}}, status=status.HTTP_404_NOT_FOUND
            )
        if not _can_access_team(request.user, issue.conversation.team):
            return Response(
                {"error": {"code": "FORBIDDEN", "message": "You do not have access to this issue."}},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = IssueStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            updated = transition_issue_status(issue, serializer.validated_data["status"], request.user)
        except WorkspaceError as e:
            http_status = status.HTTP_403_FORBIDDEN if e.code == "FORBIDDEN" else status.HTTP_400_BAD_REQUEST
            return Response({"error": {"code": e.code, "message": e.message}}, status=http_status)

        return Response(IssueSerializer(updated).data)


class TaskCreateView(APIView):
    """POST: create a task on a conversation (must not already have one)."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, conversation_id):
        conv, err = _get_conversation_or_403(request.user, conversation_id)
        if err:
            return err

        serializer = TaskCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            task = create_task(
                conv.team,
                conv,
                creator=request.user,
                description=serializer.validated_data["description"],
                assignee=serializer.validated_data.get("assignee"),
                deadline=serializer.validated_data.get("deadline"),
            )
        except WorkspaceError as e:
            return Response({"error": {"code": e.code, "message": e.message}}, status=status.HTTP_400_BAD_REQUEST)

        return Response(TaskSerializer(task).data, status=status.HTTP_201_CREATED)


class TaskStartView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, task_id):
        task = Task.objects.filter(pk=task_id).select_related("conversation__team__department").first()
        if task is None:
            return Response(
                {"error": {"code": "NOT_FOUND", "message": "Task not found."}}, status=status.HTTP_404_NOT_FOUND
            )
        if not _can_access_team(request.user, task.conversation.team):
            return Response(
                {"error": {"code": "FORBIDDEN", "message": "You do not have access to this task."}},
                status=status.HTTP_403_FORBIDDEN,
            )
        try:
            updated = start_task(task, request.user)
        except WorkspaceError as e:
            http_status = status.HTTP_403_FORBIDDEN if e.code == "FORBIDDEN" else status.HTTP_400_BAD_REQUEST
            return Response({"error": {"code": e.code, "message": e.message}}, status=http_status)
        return Response(TaskSerializer(updated).data)


class TaskEndView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, task_id):
        task = Task.objects.filter(pk=task_id).select_related("conversation__team__department").first()
        if task is None:
            return Response(
                {"error": {"code": "NOT_FOUND", "message": "Task not found."}}, status=status.HTTP_404_NOT_FOUND
            )
        if not _can_access_team(request.user, task.conversation.team):
            return Response(
                {"error": {"code": "FORBIDDEN", "message": "You do not have access to this task."}},
                status=status.HTTP_403_FORBIDDEN,
            )
        try:
            updated = end_task(task, request.user)
        except WorkspaceError as e:
            http_status = status.HTTP_403_FORBIDDEN if e.code == "FORBIDDEN" else status.HTTP_400_BAD_REQUEST
            return Response({"error": {"code": e.code, "message": e.message}}, status=http_status)
        return Response(TaskSerializer(updated).data)


def _broadcast_to_conversation(conversation_id, message_data):
    """Push a new message to the WebSocket group for this conversation,
    if Channels is configured. No-op safe if channel layer isn't available."""
    try:
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync

        channel_layer = get_channel_layer()
        if channel_layer is None:
            return
        async_to_sync(channel_layer.group_send)(
            f"conversation_{conversation_id}",
            {"type": "chat.message", "message": message_data},
        )
    except Exception:
        # Real-time push is a nice-to-have on top of the REST persistence;
        # never let a broadcast failure break message creation.
        pass
