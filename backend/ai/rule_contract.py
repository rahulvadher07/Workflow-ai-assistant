"""Validation helpers for the AI rule -> tool -> backend contract.

The JSON catalog remains the routing-policy source of truth. Runtime execution
still happens through the existing tool registry and Django services.
"""
from __future__ import annotations

import importlib
from functools import lru_cache

from .rule_engine import load_rules
from .routing import valid_router_key
from .policy import MUTATION_TOOLS

REQUIRED_RULE_FIELDS = {
    "id", "intent", "action_type", "keywords", "synonyms", "examples",
    "user_scope", "allowed_roles", "required_parameters", "optional_parameters",
    "date_handling", "time_handling", "confirmation_required", "backend_function",
    "tool",
}
VALID_SCOPES = {
    "PERSONAL", "SELF_ONLY", "CONTEXTUAL", "SPECIFIC_EMPLOYEE", "PERSONAL_OR_SPECIFIC",
    "TEAM", "COMPANY_WIDE", "SPECIFIC_TASK", "SPECIFIC_ISSUE", "SELF_BULK",
    "HOD_TEAM_BULK", "HOD_EMPLOYEE_BULK", "HOD_TEAM", "ACCESSIBLE_TEAM", "unspecified",
}
VALID_ACTION_TYPES = {"READ", "READ_ONLY", "CREATE", "UPDATE", "DELETE", "CREATE_UPDATE", "REPORT", "MUTATION"}


@lru_cache(maxsize=1)
def validate_rule_catalog() -> dict:
    """Validate rule structure and the rule -> tool -> backend contract."""
    data = load_rules()
    rules = data["rules"]
    from .tool_registry import TOOLS

    seen_ids = set()
    issues = []
    confirmation_policy = data.get("confirmation_policy") or {}
    if not isinstance(confirmation_policy, dict) or not confirmation_policy.get("accepted_phrases"):
        issues.append("missing top-level confirmation_policy.accepted_phrases")
    for rule in rules:
        rule_id = rule.get("id")
        if not rule_id:
            issues.append("rule missing id")
            continue
        if rule_id in seen_ids:
            issues.append(f"duplicate rule id: {rule_id}")
        seen_ids.add(rule_id)

        missing = sorted(REQUIRED_RULE_FIELDS - set(rule))
        if missing:
            issues.append(f"{rule_id}: missing fields {', '.join(missing)}")
        if rule.get("user_scope") not in VALID_SCOPES:
            issues.append(f"{rule_id}: invalid user_scope={rule.get('user_scope')!r}")
        if rule.get("action_type") not in VALID_ACTION_TYPES:
            issues.append(f"{rule_id}: invalid action_type={rule.get('action_type')!r}")

        if rule.get("execution_mode") == "DETERMINISTIC":
            router_key = rule.get("router_key")
            if not valid_router_key(router_key):
                issues.append(f"{rule_id}: invalid deterministic router_key={router_key!r}")
            else:
                from . import orchestrator as orchestrator_module
                if not callable(getattr(orchestrator_module, f"_route_{router_key}", None)):
                    issues.append(f"{rule_id}: no executable handler for deterministic router_key={router_key!r}")

        tool_name = rule.get("tool")
        if tool_name and tool_name not in TOOLS:
            issues.append(f"{rule_id}: unknown tool {tool_name}")
            continue

        required = list(rule.get("required_parameters") or rule.get("required") or [])
        optional = list(rule.get("optional_parameters") or [])
        if set(required) & set(optional):
            issues.append(f"{rule_id}: parameter listed as both required and optional")

        if tool_name in TOOLS:
            properties = set((TOOLS[tool_name].get("parameters") or {}).get("properties", {}))
            for name in required + optional:
                # Semantic pseudo-parameters describe routing state, not JSON tool args.
                if name in {"confirmation", "request_id_or_unique_leave_match", "optional_date", "optional_month"}:
                    continue
                if name not in properties:
                    issues.append(f"{rule_id}: parameter {name} not present in tool schema {tool_name}")

        backend = str(rule.get("backend_function") or "").strip()
        if not backend or "." not in backend:
            # A tool alias is acceptable for older rules, but make the exception explicit.
            if backend != tool_name:
                issues.append(f"{rule_id}: backend_function must be module.function or tool alias")

        confirmation_required = rule.get("confirmation_required")
        if tool_name in MUTATION_TOOLS and confirmation_required is not True:
            issues.append(f"{rule_id}: mutation tool {tool_name} must require confirmation")
        global_confirmation = data.get("confirmation_policy") or {}
        has_global_confirmation = bool(global_confirmation.get("accepted_phrases")) and global_confirmation.get("requires_active_pending_preview") is True
        if confirmation_required is True and not (has_global_confirmation or rule.get("confirmation_phrases") or (rule.get("confirmation") or {}).get("accepted_phrases")):
            issues.append(f"{rule_id}: confirmation required but no global or rule confirmation policy is configured")

    if issues:
        raise ValueError("AI rule catalog contract validation failed: " + " | ".join(issues))
    return {"rules": len(rules), "tools": len(TOOLS), "issues": []}


def clear_rule_validation_cache():
    validate_rule_catalog.cache_clear()


def backend_callable(path: str):
    """Resolve a dotted backend function path for diagnostics/tests only."""
    if not path or "." not in path:
        return None
    module_name, attr = path.rsplit(".", 1)
    try:
        return getattr(importlib.import_module(module_name), attr)
    except (ImportError, AttributeError):
        return None


def validate_tool_arguments(tool_name: str, arguments: dict) -> tuple[bool, str | None]:
    """Perform lightweight JSON-schema validation before any tool reaches Django."""
    from .tool_registry import TOOLS
    spec = TOOLS.get(tool_name)
    if not spec:
        return False, f"Unknown tool '{tool_name}'."
    if not isinstance(arguments, dict):
        return False, "Tool arguments must be a JSON object."
    schema = spec.get("parameters") or {}
    properties = schema.get("properties") or {}
    required = schema.get("required") or []
    missing = [name for name in required if name not in arguments or arguments.get(name) is None]
    if missing:
        return False, "Missing required parameter(s): " + ", ".join(missing)
    extras = sorted(set(arguments) - set(properties))
    if extras and schema.get("additionalProperties") is False:
        return False, "Unexpected parameter(s): " + ", ".join(extras)
    for name, value in arguments.items():
        if value is None or name not in properties:
            continue
        prop = properties[name] or {}
        expected = prop.get("type")
        if expected == "string" and not isinstance(value, str):
            return False, f"Parameter '{name}' must be a string."
        if expected == "integer" and (not isinstance(value, int) or isinstance(value, bool)):
            return False, f"Parameter '{name}' must be an integer."
        if expected == "boolean" and not isinstance(value, bool):
            return False, f"Parameter '{name}' must be a boolean."
        if expected == "array" and not isinstance(value, list):
            return False, f"Parameter '{name}' must be an array."
        if prop.get("enum") and value not in prop["enum"]:
            return False, f"Parameter '{name}' must be one of: {', '.join(map(str, prop['enum']))}."
    return True, None
