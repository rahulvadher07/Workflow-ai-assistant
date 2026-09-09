"""Declarative routing contract helpers.

The rule catalog is the source of truth for which router keys are declared.
Executable handler functions live in the AI orchestrator and are selected by
router-key naming convention; this module intentionally contains no duplicated
allow-list of business actions.
"""
from __future__ import annotations

import re

from .rule_engine import load_rules


def declared_deterministic_router_keys() -> frozenset[str]:
    """Return deterministic router keys declared by the JSON catalog."""
    return frozenset(
        str(rule.get("router_key"))
        for rule in load_rules().get("rules", [])
        if rule.get("execution_mode") == "DETERMINISTIC" and rule.get("router_key")
    )


def valid_router_key(value: str | None) -> bool:
    """Router keys are stable Python-style identifiers used for handler lookup."""
    return bool(value and re.fullmatch(r"[A-Z][A-Z0-9_]*", str(value)))
