import re
from pathlib import Path


def _extract_assignee_name(text):
    raw = " ".join((text or "").strip().split())
    patterns = (
        r"\b(?:assign|move|give|put)\s+(?:task\s*(?:number)?\s*[-#:]?\s*\d{1,4})\s+(?:to|under|with)\s+(.+?)(?=\s+(?:and|with)\s+(?:set|change|update|make|move)\b|\s+(?:from|until|deadline|due)\b|$)",
    )
    for pattern in patterns:
        m = re.search(pattern, raw, flags=re.I)
        if m:
            return m.group(1).strip(" .,:;-\"") or None
    return None


def test_compound_task_assignment_phrase():
    assert _extract_assignee_name("Move Task 07 to Rahul and make deadline Monday") == "Rahul"


def test_project_has_clean_cache_free_package():
    root = Path(__file__).resolve().parents[2]
    assert not list(root.rglob("__pycache__"))
