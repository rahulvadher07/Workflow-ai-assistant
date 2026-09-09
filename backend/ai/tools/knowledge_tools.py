from accounts.models import User
from ai.knowledge import search_company_policy as _search_company_policy


def search_company_policy(user, query):
    """Search only active Knowledge & Policy content with role-aware ranking."""
    role = getattr(user, "role", None)
    results = _search_company_policy(query, role=role, limit=5)
    return {"results": results}
