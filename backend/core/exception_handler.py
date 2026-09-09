from rest_framework.views import exception_handler as drf_exception_handler
from rest_framework.response import Response


def _unwrap(value):
    """DRF often wraps a single scalar in a one-item list of ErrorDetail
    when it passes through nested ValidationError handling. Reduce back
    down to a plain string regardless of whether that wrapping happened."""
    if isinstance(value, list) and len(value) == 1:
        value = value[0]
    return str(value)


def custom_exception_handler(exc, context):
    """
    Wraps DRF's default exception handling into a consistent envelope:
    { "error": { "code": "...", "message": "..." } }

    If the raised exception already carries a `code` via
    APIException.default_code / detail.code, that is used; otherwise
    falls back to a generic code derived from the HTTP status.
    """
    response = drf_exception_handler(exc, context)

    if response is None:
        return None

    detail = response.data

    code = getattr(exc, "default_code", None) or "ERROR"
    message = None

    STATUS_CODE_MAP = {
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
        409: "CONFLICT",
        429: "THROTTLED",
    }

    if isinstance(detail, dict):
        # Prefer an explicit code/message pair if the view raised it that way,
        # e.g. raise serializers.ValidationError({"code": "X", "message": "Y"})
        # DRF wraps each dict value in a list of ErrorDetail, so unwrap that
        # single-item list back down to a plain string.
        if "code" in detail and "message" in detail:
            code = _unwrap(detail["code"])
            message = _unwrap(detail["message"])
        elif set(detail.keys()) == {"detail"}:
            # Generic DRF exceptions (PermissionDenied, NotAuthenticated,
            # NotFound, etc.) land here as {"detail": "..."} - classify by
            # HTTP status rather than mislabeling as a validation error.
            message = _unwrap(detail["detail"])
            code = STATUS_CODE_MAP.get(response.status_code, "ERROR")
        else:
            # Field validation errors - flatten into a single message
            parts = []
            for field, errs in detail.items():
                if isinstance(errs, list):
                    parts.append(f"{field}: {'; '.join(str(e) for e in errs)}")
                else:
                    parts.append(f"{field}: {errs}")
            message = " | ".join(parts)
            code = "VALIDATION_ERROR"
    elif isinstance(detail, list):
        message = "; ".join(str(e) for e in detail)
    else:
        message = str(detail)

    response.data = {"error": {"code": code, "message": message}}
    return response
