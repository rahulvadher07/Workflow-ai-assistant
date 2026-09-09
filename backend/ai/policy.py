"""Shared AI execution policy constants.

These are executable safety contracts, not business rules. Backend services stay
authoritative for permission and domain validation.
"""

MUTATION_TOOLS = frozenset({
    "punch_attendance", "create_leave_request", "cancel_my_leave", "cancel_team_leaves",
    "approve_team_leave", "reject_team_leave", "create_task", "create_task_for_team",
    "start_task", "start_my_task", "assign_task", "update_task_assignment_and_deadline",
    "update_task_deadline", "update_task_description", "complete_my_task", "end_task",
    "create_issue", "create_issue_for_team", "update_issue_status", "notify_team_members",
    "create_notification",
})
