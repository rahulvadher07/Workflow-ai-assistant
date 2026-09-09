"""Low-overhead AI observability helpers.

Logs never contain secrets, full prompts, or tool arguments. They provide a
stable event/incident shape for local debugging and production log shipping.
"""
from __future__ import annotations

import functools
import logging
import time
import uuid

from django.conf import settings

logger = logging.getLogger("workflow_ai.ai")


def new_incident_id(prefix: str = "AI") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10].upper()}"


def _enabled() -> bool:
    return bool(getattr(settings, "AI_OBSERVABILITY_ENABLED", True))


def log_event(event: str, **fields):
    if not _enabled():
        return
    safe_fields = {k: v for k, v in fields.items() if v is not None}
    logger.info("[AI %s] %s", event, " ".join(f"{k}={safe_fields[k]}" for k in sorted(safe_fields)))


def observe_ai_turn(func):
    """Log timing/outcome for an AI turn without changing its result."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if not _enabled():
            return func(*args, **kwargs)
        started = time.perf_counter()
        try:
            result = func(*args, **kwargs)
        except Exception as exc:
            duration_ms = round((time.perf_counter() - started) * 1000, 1)
            conversation = args[1] if len(args) > 1 else kwargs.get("conversation")
            user = args[0] if args else kwargs.get("user")
            log_event(
                "TURN_ERROR",
                duration_ms=duration_ms,
                user_id=getattr(user, "id", None),
                conversation_id=getattr(conversation, "id", None),
                exception=exc.__class__.__name__,
            )
            raise
        duration_ms = round((time.perf_counter() - started) * 1000, 1)
        conversation = args[1] if len(args) > 1 else kwargs.get("conversation")
        user = args[0] if args else kwargs.get("user")
        log_event(
            "TURN_COMPLETE",
            duration_ms=duration_ms,
            user_id=getattr(user, "id", None),
            conversation_id=getattr(conversation, "id", None),
        )
        return result
    return wrapper
