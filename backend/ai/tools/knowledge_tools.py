from accounts.models import User
from company.models import CompanyRule
from ai.knowledge import search_company_policy as _search_company_policy
from ai.models import KnowledgeChunk


def _focused_sentences(text, keywords, limit=5):
    """Return short, topic-specific statements from a retrieved policy chunk.

    PDF extraction often flattens tables into one long paragraph. Split on
    bullets/section markers as well as sentence punctuation so a focused query
    does not accidentally return unrelated company, salary, or role content.
    """
    import re

    compact = re.sub(r"\s+", " ", str(text or "").strip())
    if not compact:
        return []
    parts = re.split(
        r"(?=(?:•|-|\d+[.)]|[A-Z]{2,}\s*[-:]))",
        compact,
        flags=re.I,
    )
    if len(parts) <= 1:
        parts = re.split(r"(?<=[.!?])\s+", compact)
    keyword_set = {str(k).strip().lower() for k in keywords if str(k).strip()}
    ranked = []
    for index, part in enumerate(parts):
        sentence = part.strip(" \t\r\n-•")
        if not sentence:
            continue
        lower = sentence.lower()
        hits = sum(1 for keyword in keyword_set if re.search(r"\b" + re.escape(keyword) + r"\b", lower))
        if hits:
            ranked.append((hits, -index, sentence))
    ranked.sort(reverse=True)
    return [sentence for _, _, sentence in ranked[:limit]]


def _extract_section(text, heading, next_heading=None):
    """Extract one policy section from flattened PDF text."""
    import re
    compact = re.sub(r"\s+", " ", str(text or "").strip())
    if not compact:
        return ""
    start = re.search(re.escape(heading), compact, flags=re.I)
    if not start:
        return ""
    section = compact[start.end():]
    if next_heading:
        stop = re.search(re.escape(next_heading), section, flags=re.I)
        if stop:
            section = section[:stop.start()]
    return section.strip()


def _leave_policy_from_text(text):
    """Extract only the Leave Policy section and its leave-type rules."""
    import re
    section = _extract_section(text, "4. Leave Policy", "5.")
    if not section:
        return []

    statements = []
    intro_match = re.search(
        r"The leave policy applies to employees and HODs.*?(?=Leave type)",
        section,
        flags=re.I,
    )
    if intro_match:
        statements.append(re.sub(r"\s+", " ", intro_match.group(0)).strip())

    type_pattern = re.compile(
        r"(?P<label>(?:Casual Leave \(CL\)|Paid Leave \(PL\)|Sick Leave \(SL\)|Unpaid Leave \(UL\)))\s+"
        r"(?P<body>.*?)(?=(?:Casual Leave \(CL\)|Paid Leave \(PL\)|Sick Leave \(SL\)|Unpaid Leave \(UL\)|$))",
        re.I,
    )
    for match in type_pattern.finditer(section):
        label = re.sub(r"\s+", " ", match.group("label")).strip()
        body = re.sub(r"\s+", " ", match.group("body")).strip(" .")
        if body:
            statements.append(f"{label}: {body}")

    return statements


def _working_hours_from_text(text):
    """Extract only the Working Hours & Attendance Policy section."""
    import re
    section = _extract_section(text, "3. Working Hours & Attendance Policy", "4. Leave Policy")
    if not section:
        return []
    statements = []
    patterns = (
        (r"Standard working days\s+(.+?)(?=Standard working hours|Lunch / break|Weekly off|Attendance method|Late arrival|Early checkout|$)", "Standard working days"),
        (r"Standard working hours\s+(.+?)(?=Lunch / break|Weekly off|Attendance method|Late arrival|Early checkout|$)", "Standard working hours"),
        (r"Lunch / break\s+(.+?)(?=Weekly off|Attendance method|Late arrival|Early checkout|$)", "Lunch / break"),
        (r"Weekly off\s+(.+?)(?=Attendance method|Late arrival|Early checkout|$)", "Weekly off"),
        (r"Late arrival\s+(.+?)(?=Early checkout|$)", "Late arrival"),
        (r"Early checkout\s+(.+?)(?=Attendance hours shown|$)", "Early checkout"),
    )
    for pattern, label in patterns:
        m = re.search(pattern, section, flags=re.I)
        if m:
            value = re.sub(r"\s+", " ", m.group(1)).strip(" .")
            if value:
                statements.append(f"{label}: {value}")
    return statements

def _dedupe_lines(lines, limit=8):
    seen = set()
    result = []
    for line in lines:
        clean = " ".join(str(line or "").split()).strip()
        key = clean.lower()
        if clean and key not in seen:
            seen.add(key)
            result.append(clean)
        if len(result) >= limit:
            break
    return result


def search_company_policy(user, query):
    """Search only active Knowledge & Policy content with role-aware ranking."""
    role = getattr(user, "role", None)
    results = _search_company_policy(query, role=role, limit=5)
    return {"results": results}


def search_leave_policy(user):
    """Return focused leave-policy statements from indexed knowledge and company rules."""
    role = getattr(user, "role", None)
    rows = _search_company_policy("leave policy leave rules casual sick earned holiday", role=role, limit=10)
    statements = []
    for row in rows:
        category = str(row.get("category") or "").upper()
        # The knowledge document may be categorized as GENERAL while still
        # containing the authoritative Leave Policy section. Keep focused
        # retrieval based on the query instead of excluding that document.
        if category not in {"", "LEAVE", "GENERAL"}:
            continue
        focused = _leave_policy_from_text(row.get("text"))
        if focused:
            statements.extend(focused)
        elif category == "LEAVE":
            statements.extend(_focused_sentences(
                row.get("text"),
                {"leave", "leave policy", "casual", "sick", "earned", "paid", "holiday", "vacation", "days", "approval", "carry", "balance"},
                limit=5,
            ))

    rules = CompanyRule.objects.filter(category=CompanyRule.Category.LEAVE).order_by("title", "id")
    for rule in rules:
        statements.extend(_focused_sentences(
            rule.details,
            {"leave", "casual", "sick", "earned", "paid", "holiday", "vacation", "days", "approval", "carry", "balance"},
            limit=5,
        ))

    statements = _dedupe_lines(statements, limit=8)
    return {"statements": statements}


def search_working_hours_policy(user):
    """Return focused working-hours statements from company rules and indexed knowledge."""
    role = getattr(user, "role", None)
    statements = []

    rules = CompanyRule.objects.filter(
        category__in=[CompanyRule.Category.TIME, CompanyRule.Category.ATTENDANCE]
    ).order_by("category", "title", "id")
    for rule in rules:
        statements.extend(_focused_sentences(
            rule.details,
            {"working", "work", "hours", "hour", "shift", "schedule", "daily", "monthly", "office time", "timing"},
            limit=6,
        ))

    rows = _search_company_policy(
        "company working hours daily working hours shift timing monthly hours",
        role=role,
        limit=10,
    )
    for row in rows:
        category = str(row.get("category") or "").upper()
        if category not in {"ATTENDANCE", "GENERAL", "OVERTIME"}:
            continue
        focused = _working_hours_from_text(row.get("text"))
        if focused:
            statements.extend(focused)
        elif category == "ATTENDANCE":
            statements.extend(_focused_sentences(
                row.get("text"),
                {"working", "work", "hours", "hour", "shift", "schedule", "daily", "monthly", "office time", "timing"},
                limit=6,
            ))

    return {"statements": _dedupe_lines(statements, limit=8)}
