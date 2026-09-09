from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils import timezone
from datetime import timedelta

from accounts.models import User
from .models import Notification
from .serializers import NotificationSerializer
from .daily_brief import build_daily_brief


class NotificationListView(APIView):
    """GET: own notifications only, newest first."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        cutoff = timezone.now() - timedelta(days=7)
        Notification.objects.filter(created_at__lt=cutoff).delete()
        qs = Notification.objects.filter(recipient=request.user, created_at__gte=cutoff)
        return Response(NotificationSerializer(qs, many=True).data)


class NotificationUnreadCountView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        cutoff = timezone.now() - timedelta(days=7)
        count = Notification.objects.filter(recipient=request.user, created_at__gte=cutoff, is_read=False).count()
        return Response({"unread_count": count})


class NotificationMarkReadView(APIView):
    """PATCH: mark a single own notification as read."""

    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, pk):
        notification = Notification.objects.filter(pk=pk, recipient=request.user).first()
        if notification is None:
            return Response(
                {"error": {"code": "NOT_FOUND", "message": "Notification not found."}},
                status=status.HTTP_404_NOT_FOUND,
            )
        notification.is_read = True
        notification.save(update_fields=["is_read"])
        return Response(NotificationSerializer(notification).data)


class NotificationMarkAllReadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        updated = Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
        return Response({"marked_read": updated})


class CreateNotificationView(APIView):
    """Admin broadcasts to all active employees/HODs; HOD broadcasts to team members."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        if user.role not in (User.Role.SUPER_ADMIN, User.Role.HOD):
            return Response({"error": {"code": "FORBIDDEN", "message": "Only Admin or HOD can create notifications."}}, status=status.HTTP_403_FORBIDDEN)
        title = str(request.data.get("title", "")).strip()
        message = str(request.data.get("message", "")).strip()
        if not title:
            return Response({"error": {"code": "VALIDATION_ERROR", "message": "Title is required."}}, status=status.HTTP_400_BAD_REQUEST)

        if user.role == User.Role.SUPER_ADMIN:
            recipients = User.objects.filter(status=User.Status.ACTIVE, role__in=[User.Role.EMPLOYEE, User.Role.HOD])
        else:
            from company.models import Department
            from teams.models import TeamMembership
            team_ids = TeamMembership.objects.filter(
                team__department__in=user.hod_departments.all()
            ).values_list("team_id", flat=True)
            legacy_department_ids = Department.objects.filter(hod=user).values_list("id", flat=True)
            team_ids = list(team_ids) + list(
                TeamMembership.objects.filter(team__department_id__in=legacy_department_ids).values_list("team_id", flat=True)
            )
            recipients = User.objects.filter(
                status=User.Status.ACTIVE, team_memberships__team_id__in=team_ids
            ).distinct()

        # Materialize recipient IDs before adding the creator so we never
        # combine distinct and non-distinct QuerySets with the ``|`` operator.
        recipient_ids = set(recipients.values_list("pk", flat=True))
        recipient_ids.add(user.pk)
        recipients = User.objects.filter(pk__in=recipient_ids)

        created = 0
        from django.db import transaction
        from .services import notify
        with transaction.atomic():
            for recipient in recipients: 
                notify(recipient=recipient, verb=Notification.Verb.ANNOUNCEMENT, title=title, message=message)
                created += 1
        return Response({"message": "Notification sent successfully.", "recipients": created}, status=status.HTTP_201_CREATED)


class HODDailyBriefView(APIView):
    """GET: on-demand view of the calling HOD's own daily brief data."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if request.user.role != User.Role.HOD:
            return Response(
                {"error": {"code": "FORBIDDEN", "message": "Only an HOD can view a daily brief."}},
                status=status.HTTP_403_FORBIDDEN,
            )
        brief = build_daily_brief(request.user)
        if brief is None:
            return Response(
                {"error": {"code": "FORBIDDEN", "message": "You are not assigned as HOD of any department."}},
                status=status.HTTP_403_FORBIDDEN,
            )
        return Response(brief)
