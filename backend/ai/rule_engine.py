"""Data-driven intent/routing catalog used before and alongside Groq tool calling.

The catalog is routing guidance only. Existing Django tools/services remain the
source of truth for permissions, validation, business rules, and database writes.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

RULES_PATH = Path(__file__).with_name("agent_rules.json")


@lru_cache(maxsize=1)
def load_rules() -> dict:
    """Load and normalize the rule catalog.

    Older project versions stored a bare list while the rule engine expected a
    mapping with a ``rules`` key. Accept both forms so a malformed/legacy local
    catalog cannot crash every AI request.
    """
    with RULES_PATH.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if isinstance(data, list):
        data = {"version": "legacy", "rules": data, "global_rules": []}
    if not isinstance(data, dict) or not isinstance(data.get("rules"), list):
        raise ValueError("AI rule catalog must contain a 'rules' array.")
    return data


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def _keyword_hit(text: str, keyword: str) -> bool:
    keyword = normalize(keyword)
    if not keyword:
        return False
    if " " in keyword or "-" in keyword or "'" in keyword or "’" in keyword:
        return keyword in text
    return re.search(r"\b" + re.escape(keyword) + r"\b", text) is not None


def _constraint_hit(text: str, value: str) -> bool:
    """Match a required/excluded marker, tolerating a simple English plural."""
    value = normalize(value)
    if _keyword_hit(text, value):
        return True
    if " " not in value and "-" not in value and not value.endswith("s"):
        return _keyword_hit(text, value + "s")
    return False


def _trigger_hit(text: str, trigger: str) -> bool:
    trigger = normalize(trigger)
    if not trigger:
        return False
    return trigger in text


def match_rules(text: str, limit: int = 5, role: str | None = None) -> list[dict]:
    """Return the strongest routing rules for a user message.

    Exact trigger phrases receive the largest boost. Rules may also declare
    ``required_words`` and ``exclude_words`` to keep overlapping intents (for
    example personal leave vs team leave) separated.
    """
    normalized = normalize(text)
    if not normalized:
        return []

    scored = []
    action_words = re.findall(
        r"\b(?:cancel|punch|clock|apply|request|take|withdraw|approve|reject|create|assign|start|begin|resume|complete|finish|end|notify|report|raise|change|update|set|show|get|list|search)\b",
        normalized,
    )

    for rule in load_rules().get("rules", []):
        allowed_roles = rule.get("allowed_roles") or []
        if role and allowed_roles and str(role) not in {str(value) for value in allowed_roles}:
            continue
        required_words = [normalize(w) for w in rule.get("required_words", []) if normalize(w)]
        if required_words and not all(_constraint_hit(normalized, w) for w in required_words):
            continue
        exclude_words = [normalize(w) for w in rule.get("exclude_words", []) if normalize(w)]
        if any(_constraint_hit(normalized, w) for w in exclude_words):
            continue

        trigger_hits = [t for t in rule.get("triggers", []) if _trigger_hit(normalized, t)]
        keyword_hits = [kw for kw in (rule.get("keywords", []) + rule.get("synonyms", [])) if _keyword_hit(normalized, kw)]
        example_hits = [example for example in rule.get("examples", []) if _trigger_hit(normalized, example)]
        regex_hits = []
        for pattern in rule.get("regex_patterns", []):
            try:
                if re.search(pattern, normalized, flags=re.I):
                    regex_hits.append(pattern)
            except re.error:
                continue
        if not trigger_hits and not keyword_hits and not regex_hits:
            continue

        score = int(rule.get("priority", 0))
        score += sum(24 + min(10, len(normalize(t).split()) * 2) for t in trigger_hits)
        score += sum(4 + min(8, len(normalize(k).split()) * 2) for k in keyword_hits)
        score += sum(10 + min(10, len(normalize(e).split()) * 2) for e in example_hits)
        score += 18 * len(regex_hits)
        # Explicit scope words make the catalog materially safer than generic
        # keyword overlap. Never let a generic notification/leave rule outrank
        # an explicitly scoped team or employee rule.
        scope = str(rule.get("user_scope", rule.get("scope", ""))).upper()
        if re.search(r"\b(my|mine|me)\b", normalized) and scope in {"PERSONAL", "SELF_ONLY", "SELF_BULK", "PERSONAL_OR_SPECIFIC"}:
            score += 15
        if re.search(r"\b(team|my team|team\'s)\b", normalized) and scope in {"TEAM", "HOD_TEAM", "HOD_TEAM_BULK", "ACCESSIBLE_TEAM"}:
            score += 22
        if re.search(r"\b(employee|member|user)\b|[A-Za-z][A-Za-z .'-]+['’]s\b", normalized) and scope in {"SPECIFIC_EMPLOYEE", "HOD_EMPLOYEE_BULK", "PERSONAL_OR_SPECIFIC"}:
            score += 16
        if re.search(r"\b(company|organization|department)\b", normalized) and scope == "COMPANY_WIDE":
            score += 20
        if action_words and rule.get("category", "").endswith("_action"):
            score += 3
        scope_bonus = {
            "HOD_EMPLOYEE_BULK": 30, "SPECIFIC_EMPLOYEE": 28, "PERSONAL_OR_SPECIFIC": 24,
            "HOD_TEAM_BULK": 26, "HOD_TEAM": 24, "TEAM": 22, "ACCESSIBLE_TEAM": 22,
            "SELF_BULK": 24, "PERSONAL": 18, "SELF_ONLY": 18, "COMPANY_WIDE": 14,
        }
        score += scope_bonus.get(scope, 0) if re.search(r"\b(my|mine|me|team|employee|company|organization)\b|['’]s\b", normalized) else 0
        if rule.get("confirmation") == "REQUIRED" and any(w in normalized for w in ("all", "every", "bulk", "team")):
            score += 2

        matched = []
        for value in trigger_hits + keyword_hits + example_hits + regex_hits:
            if value not in matched:
                matched.append(value)
        scored.append((score, len(matched), rule, matched))

    scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return [
        {"rule": rule, "matched_keywords": hits, "score": score}
        for score, _, rule, hits in scored[:limit]
    ]


def best_rule(text: str, role: str | None = None) -> dict | None:
    matches = match_rules(text, limit=2, role=role)
    if not matches:
        return None
    # Only treat a result as deterministic when it clearly dominates the next
    # candidate. This avoids accidental scope/action hijacking on overlapping phrases.
    if len(matches) > 1 and matches[0]["score"] < matches[1]["score"] + 4:
        return {**matches[0], "ambiguous": True, "alternatives": [m["rule"].get("id") for m in matches[1:2]]}
    return {**matches[0], "ambiguous": False, "alternatives": []}


def build_action_plan(text: str, role: str | None = None) -> dict | None:
    """Return a compact canonical action plan from the server-side rule catalog.

    This is intentionally side-effect free. It gives the orchestrator one stable
    structure for intent/action/scope/tool selection before Groq is considered.
    """
    matched = best_rule(text, role=role)
    if not matched:
        return None
    rule = matched["rule"]
    return {
        "rule_id": rule.get("id"),
        "intent": rule.get("intent"),
        "action": rule.get("action", rule.get("intent")),
        "action_type": rule.get("action_type"),
        "scope": rule.get("user_scope", rule.get("scope")),
        "roles": list(rule.get("allowed_roles") or []),
        "required_parameters": list(rule.get("required_parameters", rule.get("required", [])) or []),
        "optional_parameters": list(rule.get("optional_parameters") or []),
        "tool": rule.get("tool"),
        "backend_function": rule.get("backend_function"),
        "confirmation_required": bool(rule.get("confirmation_required")),
        "execution_mode": rule.get("execution_mode", "GROQ_TOOL"),
        "router_key": rule.get("router_key"),
        "ambiguous": bool(matched.get("ambiguous")),
        "matched_keywords": list(matched.get("matched_keywords") or []),
    }


def build_rule_context(text: str, role: str | None = None) -> str:
    """Build compact rule guidance for the current Groq turn."""
    matches = match_rules(text, role=role)
    if not matches:
        return "No high-confidence rule matched. Use the available tools carefully and ask a short clarification when required data is missing."

    lines = ["SERVER-SIDE RULE CATALOG MATCH (routing guidance; Django tools remain authoritative):"]
    data = load_rules()
    confirmation_policy = data.get("confirmation_policy") or {}
    if confirmation_policy:
        lines.append(
            "- GLOBAL CONFIRMATION POLICY: confirmation is server-side only. A phrase can confirm only a live, unexpired "
            "pending preview belonging to the authenticated user and immediately preceding this turn. Use the exact frozen "
            "tool and arguments; never reinterpret confirmation with an LLM. Accepted forms are defined centrally in "
            "confirmation_policy and are not action instructions by themselves."
        )
    globals_ = data.get("global_rules", [])
    for item in globals_[:7]:
        lines.append(f"- GLOBAL: {item}")
    for item in matches:
        rule = item["rule"]
        required = ", ".join(rule.get("required_parameters", rule.get("required", []))) or "none"
        optional = ", ".join(rule.get("optional_parameters", [])) or "none"
        scope = rule.get("user_scope", rule.get("scope", "unspecified"))
        confirmation = rule.get("confirmation_required", rule.get("confirmation", "none"))
        action = rule.get("action", rule.get("intent", ""))
        action_type = rule.get("action_type", "")
        route_mode = rule.get("execution_mode", "GROQ_TOOL")
        steps = " -> ".join(rule.get("steps", [])[:6])
        lines.append(
            f"- RULE {rule.get('id')}: type={action_type}; mode={route_mode}; tool={rule.get('tool')}; "
            f"scope={scope}; required={required}; optional={optional}; confirmation={confirmation}; "
            f"matched={', '.join(item['matched_keywords'])}; action={action}"
        )
        if steps:
            lines.append(f"  steps: {steps}")
        forbidden = rule.get("forbidden") or []
        if forbidden:
            lines.append(f"  forbidden: {'; '.join(forbidden[:5])}")
    return "\n".join(lines)


def is_action_rule(item: dict | None) -> bool:
    return bool(item and str(item["rule"].get("category", "")).endswith("_action"))
