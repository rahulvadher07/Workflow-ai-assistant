"""Server-originated, user-scoped realtime data-change events.

This is transport only: it never changes business logic or API contracts. Domain
code signals that a persisted change occurred and the frontend decides which
mounted resource consumers need to refresh.
"""
from __future__ import annotations

import logging
from collections.abc import Iterable

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings

logger = logging.getLogger("workflow_ai.realtime")


def _normalise_user_ids(user_ids: Iterable[int] | None) -> list[int]:
    return sorted({int(value) for value in (user_ids or []) if value is not None})


def publish_user_data_change(user_ids, resource: str, *, action: str = "updated", entity_id=None, source: str = "backend"):
    """Publish a small invalidation event after a successful database commit."""
    ids = _normalise_user_ids(user_ids)
    if not ids or not resource:
        return 0
    channel_layer = get_channel_layer()
    if channel_layer is None:
        return 0
    event = {
        "type": "data.change",
        "change": {
            "resource": str(resource),
            "action": str(action),
            "entity_id": entity_id,
            "source": str(source),
        },
    }
    sent = 0
    for user_id in ids:
        try:
            async_to_sync(channel_layer.group_send)(f"user_{user_id}_data_changes", event)
            sent += 1
        except Exception:
            logger.exception(
                "[REALTIME DATA ERROR] action=publish resource=%s user_id=%s",
                resource,
                user_id,
            )
    return sent


def schedule_user_data_change(user_ids, resource: str, *, action: str = "updated", entity_id=None, source: str = "backend"):
    """Schedule publication only after the current DB transaction commits."""
    from django.db import transaction

    ids = _normalise_user_ids(user_ids)
    if not ids or not resource:
        return
    transaction.on_commit(
        lambda ids=ids, resource=resource, action=action, entity_id=entity_id, source=source:
        publish_user_data_change(ids, resource, action=action, entity_id=entity_id, source=source)
    )


def related_user_ids(instance) -> list[int]:
    """Resolve a conservative set of users affected by important domain rows."""
    app = instance._meta.app_label
    model = instance.__class__.__name__
    ids: set[int] = set()

    def add(*values):
        for value in values:
            if value:
                try:
                    ids.add(int(value))
                except (TypeError, ValueError):
                    pass

    direct_fields = (
        "employee_id", "recipient_id", "user_id", "created_by_id", "creator_id", "assignee_id",
        "lead_id", "sender_id", "uploaded_by_id", "updated_by_id", "approved_by_id", "cancelled_by_id",
        "hod_id",
    )
    for field in direct_fields:
        add(getattr(instance, field, None))

    # Team-scoped models notify active members and department HODs.
    team_id = getattr(instance, "team_id", None)
    conversation_id = getattr(instance, "conversation_id", None)
    if conversation_id:
        try:
            team_id = team_id or instance.conversation.team_id
        except Exception:
            pass
    if team_id:
        try:
            from teams.models import TeamMembership
            memberships = TeamMembership.objects.filter(team_id=team_id).values_list("employee_id", flat=True)
            add(*memberships)
        except Exception:
            logger.exception("[REALTIME DATA ERROR] action=resolve_team_members team_id=%s", team_id)
        try:
            from teams.models import Team
            from company.models import department_hod_queryset
            team = Team.objects.select_related("department").filter(pk=team_id).first()
            if team:
                add(*department_hod_queryset(team.department).values_list("id", flat=True))
        except Exception:
            logger.exception("[REALTIME DATA ERROR] action=resolve_team_hods team_id=%s", team_id)

    department_id = getattr(instance, "department_id", None)
    if department_id:
        try:
            from accounts.models import User
            from company.models import department_hod_queryset, Department
            department = Department.objects.filter(pk=department_id).first()
            if department:
                add(*department_hod_queryset(department).values_list("id", flat=True))
                add(*User.objects.filter(employee_profile__department_id=department_id, status=User.Status.ACTIVE).values_list("id", flat=True))
        except Exception:
            logger.exception("[REALTIME DATA ERROR] action=resolve_department_users department_id=%s", department_id)

    employee_id = getattr(instance, "employee_id", None)
    if employee_id:
        try:
            from accounts.models import User
            from company.models import department_hod_queryset
            employee = User.objects.select_related("employee_profile__department").filter(pk=employee_id).first()
            if employee and getattr(employee, "employee_profile", None):
                add(*department_hod_queryset(employee.employee_profile.department).values_list("id", flat=True))
                if str(getattr(employee, "role", "")) == "HOD":
                    add(*User.objects.filter(role=User.Role.SUPER_ADMIN, status=User.Status.ACTIVE).values_list("id", flat=True))
        except Exception:
            logger.exception("[REALTIME DATA ERROR] action=resolve_employee_users employee_id=%s", employee_id)

    if model in {"PolicyDocument", "CompanyRule", "Company", "Department", "PayrollRule"}:
        try:
            from accounts.models import User
            cap = int(getattr(settings, "REALTIME_COMPANY_BROADCAST_MAX_USERS", 2000))
            user_ids = list(User.objects.filter(status=User.Status.ACTIVE).values_list("id", flat=True)[:cap])
            add(*user_ids)
        except Exception:
            logger.exception("[REALTIME DATA ERROR] action=resolve_company_users model=%s", model)

    return sorted(ids)
