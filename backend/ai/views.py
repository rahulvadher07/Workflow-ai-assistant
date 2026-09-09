from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils import timezone
from datetime import timedelta
import logging
import uuid

from .models import AIConversation
from .serializers import AIConversationSerializer, AIChatRequestSerializer
from .orchestrator import send_message, GroqQuotaExceeded, GroqToolValidationError, GroqRateLimited

logger = logging.getLogger(__name__)


class AIChatView(APIView):
    """
    POST: send a message to the AI agent. If conversation_id is omitted,
    starts a new conversation for the current user. Continues an
    existing conversation (with its stored message history as context)
    if conversation_id is provided and belongs to the caller.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        # Remove conversations exactly after 24 hours before processing a new turn.
        cutoff = timezone.now() - timedelta(hours=24)
        AIConversation.objects.filter(started_at__lt=cutoff).delete()

        serializer = AIChatRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        conversation_id = serializer.validated_data.get("conversation_id")
        message = serializer.validated_data["message"]

        if conversation_id:
            conversation = AIConversation.objects.filter(pk=conversation_id, employee=request.user).first()
            if conversation is None:
                return Response(
                    {"error": {"code": "NOT_FOUND", "message": "Conversation not found."}},
                    status=status.HTTP_404_NOT_FOUND,
                )
        else:
            conversation = AIConversation.objects.create(employee=request.user)

        try:
            reply = send_message(request.user, conversation, message)
        except GroqToolValidationError as e:
            incident_id = uuid.uuid4().hex[:10]
            logger.error(
                "AI_TOOL_FAILURE [incident=%s] tool=%s reason=%s details=%s",
                incident_id, getattr(e, "tool_name", None) or "unknown", str(e), getattr(e, "details", {}),
                exc_info=True,
            )
            return Response(
                {"error": {"code": "AI_TOOL_VALIDATION_ERROR", "message": str(e), "incident_id": incident_id}},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except GroqRateLimited as e:
            incident_id = uuid.uuid4().hex[:10]
            logger.warning("AI rate limited [incident=%s]: %s", incident_id, e)
            return Response(
                {"error": {"code": "AI_RATE_LIMITED", "message": str(e), "incident_id": incident_id}},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
        except GroqQuotaExceeded as e:
            logger.warning("Groq quota reached: %s", e)
            return Response(
                {"error": {"code": "AI_QUOTA_EXCEEDED", "message": str(e)}},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
        except RuntimeError as e:
            incident_id = uuid.uuid4().hex[:10]
            logger.exception("AI configuration/runtime error [incident=%s]", incident_id)
            return Response(
                {"error": {"code": "AI_RUNTIME_ERROR", "message": "I couldn't complete that request right now. Please try again.", "incident_id": incident_id}},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except Exception:
            incident_id = uuid.uuid4().hex[:10]
            logger.exception("AI chat request failed [incident=%s]", incident_id)
            return Response(
                {"error": {"code": "AI_SERVICE_UNAVAILABLE", "message": "The AI service is temporarily unavailable. Please try again.", "incident_id": incident_id}},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response({"conversation_id": conversation.id, "reply": reply})


class AIConversationDetailView(APIView):
    """Fetch full history of one of the caller's own AI conversations."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        cutoff = timezone.now() - timedelta(hours=24)
        AIConversation.objects.filter(started_at__lt=cutoff).delete()
        conversation = AIConversation.objects.filter(pk=pk, employee=request.user).first()
        if conversation is None:
            return Response(
                {"error": {"code": "NOT_FOUND", "message": "Conversation not found."}},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(AIConversationSerializer(conversation).data)


class TeamChatAIBoundaryView(APIView):
    """
    Backend boundary for the Team Workspace to send a message to the AI
    for duplicate-issue evaluation (architecture.md AI duplicate
    detection flow). This is the integration point Part 5's
    find_similar_issues() plugs into with an actual Groq similarity
    judgment. Not wired into the WebSocket chat flow itself in this
    Part - that integration is explicitly deferred.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        from teams.models import Team, TeamMembership
        from .duplicate_detection import evaluate_possible_duplicate

        team_id = request.data.get("team_id")
        text = request.data.get("text", "").strip()

        if not team_id or not text:
            return Response(
                {"error": {"code": "VALIDATION_ERROR", "message": "team_id and text are required."}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        team = Team.objects.filter(pk=team_id).select_related("department").first()
        from accounts.models import User
        from company.models import is_hod_of
        has_access = (
            team is not None and (
                request.user.role == User.Role.SUPER_ADMIN
                or (request.user.role == User.Role.HOD and is_hod_of(request.user, team.department))
                or TeamMembership.objects.filter(team=team, employee=request.user).exists()
            )
        )
        if not has_access:
            return Response(
                {"error": {"code": "FORBIDDEN", "message": "You do not have access to this team."}},
                status=status.HTTP_403_FORBIDDEN,
            )

        result = evaluate_possible_duplicate(team, text)
        return Response(result)
