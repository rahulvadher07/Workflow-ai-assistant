import json
import logging
import hashlib
import uuid
from django.db import transaction, IntegrityError, DatabaseError
from django.utils import timezone
from datetime import timedelta
"""
Central tool registry the orchestrator dispatches to. Each entry maps a
Model function-call name to (python_function, tool_schema). Every
python_function's first parameter is always `user` - bound server-side
by the orchestrator to the real authenticated caller, never taken from
model-supplied arguments. This is the single place new tools get registered.
"""

from .tools import profile_tools, attendance_tools, leave_tools, workspace_tools, knowledge_tools, action_tools, report_tools
from .policy import MUTATION_TOOLS

logger = logging.getLogger(__name__)

TOOLS = {
    "get_my_profile": {
        "fn": profile_tools.get_my_profile,
        "description": "Get the current user's own profile (name, role, department).",
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
    "get_my_attendance": {
        "fn": attendance_tools.get_my_attendance,
        "description": "Get the current user's attendance for a specific date (defaults to today): punch times, hours worked, late status.",
        "parameters": {
            "type": "object",
            "properties": {"date_str": {"type": "string", "description": "Date in YYYY-MM-DD format, optional."}},
            "required": [],
        },
    },
    "get_my_attendance_summary": {
        "fn": attendance_tools.get_my_attendance_summary,
        "description": "Get the current user's monthly attendance summary (present days, late days, total hours, overtime).",
        "parameters": {
            "type": "object",
            "properties": {"month_str": {"type": "string", "description": "Month in YYYY-MM format, optional, defaults to current month."}},
            "required": [],
        },
    },
    "get_my_leave_balance": {
        "fn": leave_tools.get_my_leave_balance,
        "description": "Get the current user's leave balances by leave type (total/used/remaining).",
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
    "get_my_leave_history": {
        "fn": leave_tools.get_my_leave_history,
        "description": "Get the current user's recent leave requests and their status.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
    "punch_attendance": {
        "fn": action_tools.punch_attendance,
        "description": "Punch attendance now for the authenticated user. The backend decides whether this punch is IN or OUT. If the user explicitly asks for IN or OUT and it does not match the next valid punch, do not record it.",
        "parameters": {
            "type": "object",
            "properties": {"requested_type": {"type": "string", "description": "Optional IN or OUT. Omit when the user simply says punch in/out attendance."}},
            "required": [],
        },
    },
    "create_leave_request": {
        "fn": leave_tools.create_leave_request,
        "description": "Create a leave request for the current user. Employee requests go to their department HOD; HOD requests go to Super Admin for approval. Only call this once reason, from_date, to_date and leave_type are all known.",
        "parameters": {
            "type": "object",
            "properties": {
                "leave_type": {"type": "string", "description": "e.g. EL, CL, Paid Leave"},
                "from_date": {"type": "string", "description": "YYYY-MM-DD"},
                "to_date": {"type": "string", "description": "YYYY-MM-DD"},
                "reason": {"type": "string"},
            },
            "required": ["leave_type", "from_date", "to_date", "reason"],
        },
    },
    "get_my_tasks": {
        "fn": workspace_tools.get_my_tasks,
        "description": "Get the current user's tasks (created by or assigned to them).",
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
    "get_my_issues": {
        "fn": workspace_tools.get_my_issues,
        "description": "Get issues from teams the current user belongs to.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
    "get_issue_details": {
        "fn": workspace_tools.get_issue_details,
        "description": "Get full details of a specific issue by its number (e.g. ISSUE-007).",
        "parameters": {
            "type": "object",
            "properties": {"issue_number": {"type": "string"}},
            "required": ["issue_number"],
        },
    },
    "search_previous_issues": {
        "fn": workspace_tools.search_previous_issues,
        "description": "Search a team's previous issues for similarity to a new problem description, to help detect duplicates.",
        "parameters": {
            "type": "object",
            "properties": {
                "team_id": {"type": "integer"},
                "query": {"type": "string", "description": "Description of the new problem."},
            },
            "required": ["team_id", "query"],
        },
    },
    "create_issue": {
        "fn": workspace_tools.create_issue,
        "description": "Create a new issue in a team, with its own dedicated conversation.",
        "parameters": {
            "type": "object",
            "properties": {
                "team_id": {"type": "integer"},
                "title": {"type": "string"},
                "description": {"type": "string"},
            },
            "required": ["team_id", "title"],
        },
    },
    "create_issue_for_team": {
        "fn": workspace_tools.create_issue_for_team,
        "description": "Create an issue in an accessible team by its exact or unambiguous name. Use when the user names the team rather than providing a team id.",
        "parameters": {
            "type": "object",
            "properties": {
                "team_name": {"type": "string"},
                "title": {"type": "string"},
                "description": {"type": "string"},
            },
            "required": ["team_name", "title"],
        },
    },
    "create_task": {
        "fn": workspace_tools.create_task,
        "description": "Create a new task in a team, optionally assigned to a member. The caller must have access to the team; HODs may create tasks in teams they manage.",
        "parameters": {
            "type": "object",
            "properties": {
                "team_id": {"type": "integer"},
                "description": {"type": "string"},
                "assignee_username": {"type": "string"},
                "deadline": {"type": "string", "description": "ISO datetime, optional."},
            },
            "required": ["team_id", "description"],
        },
    },
    "create_task_for_team": {
        "fn": workspace_tools.create_task_for_team,
        "description": "Create a new task in an accessible team by its exact or unambiguous team name. HODs may create tasks in teams they manage; employees may create tasks in teams they belong to.",
        "parameters": {"type": "object", "properties": {"team_name": {"type": "string"}, "description": {"type": "string"}, "assignee_name": {"type": "string"}, "deadline": {"type": "string"}}, "required": ["team_name", "description"]},
    },
    "start_task": {
        "fn": workspace_tools.start_task,
        "description": "Start a task the current user has access to, by its task number (e.g. TASK-012).",
        "parameters": {"type": "object", "properties": {"task_number": {"type": "string"}}, "required": ["task_number"]},
    },
    "start_my_task": {
        "fn": action_tools.start_my_task,
        "description": "Start a task the current user can access, by task number. Use for explicit start-task commands.",
        "parameters": {"type": "object", "properties": {"task_number": {"type": "string"}}, "required": ["task_number"]},
    },
    "assign_task": {
        "fn": workspace_tools.assign_task,
        "description": "Assign an accessible task to a specific active member of its team. Only the task creator or department HOD can assign it. Resolve the named person unambiguously before execution.",
        "parameters": {"type": "object", "properties": {"task_number": {"type": "string"}, "assignee_name": {"type": "string"}, "team_name": {"type": "string", "description": "Optional team name when the task number is ambiguous across teams."}}, "required": ["task_number", "assignee_name"]},
    },
    "update_task_assignment_and_deadline": {
        "fn": workspace_tools.update_task_assignment_and_deadline,
        "description": "Atomically assign an accessible task to one active team member and change its deadline as one combined action. Only the task creator or department HOD can perform these changes. Use when the user asks to assign a task and change its deadline in the same request.",
        "parameters": {"type": "object", "properties": {"task_number": {"type": "string"}, "assignee_name": {"type": "string"}, "deadline": {"type": "string"}, "team_name": {"type": "string"}}, "required": ["task_number", "assignee_name", "deadline"]},
    },
    "update_task_deadline": {
        "fn": workspace_tools.update_task_deadline,
        "description": "Change the deadline of an accessible non-completed task. Only the task creator or department HOD can do this. Deadline may be an ISO date/datetime or natural language such as tomorrow 10 AM or next Friday morning.",
        "parameters": {"type": "object", "properties": {"task_number": {"type": "string"}, "deadline": {"type": "string", "description": "ISO datetime or natural language such as tomorrow 10 AM or next Friday morning."}, "team_name": {"type": "string", "description": "Optional team name when the task number is ambiguous across teams."}}, "required": ["task_number", "deadline"]},
    },
    "complete_my_task": {
        "fn": action_tools.complete_my_task,
        "description": "Complete a task ONLY when the authenticated user is the task creator. Use when the user says a task they created/their own task should be done or completed. Never assume ownership; the tool verifies creator_id.",
        "parameters": {"type": "object", "properties": {"task_number": {"type": "string"}}, "required": ["task_number"]},
    },
    "get_team_leave_schedule": {
        "fn": action_tools.get_team_leave_schedule,
        "description": "For an HOD, show upcoming employee leave requests for ONE explicitly named team in the HOD's department. If the HOD manages multiple teams, the team name is required.",
        "parameters": {"type": "object", "properties": {"team_name": {"type": "string", "description": "Exact or unambiguous team name."}, "days": {"type": "integer", "description": "Number of upcoming days, default 10, maximum 31."}}, "required": ["team_name"]},
    },
    "approve_team_leave": {
        "fn": action_tools.approve_team_leave,
        "description": "Approve an employee leave request the authenticated HOD is authorized to approve, or an HOD leave request when the authenticated user is Super Admin. Requires the leave request id.",
        "parameters": {"type": "object", "properties": {"request_id": {"type": "integer"}}, "required": ["request_id"]},
    },
    "reject_team_leave": {
        "fn": action_tools.reject_team_leave,
        "description": "Reject an employee leave request the authenticated HOD is authorized to reject, or an HOD leave request when the authenticated user is Super Admin. Requires the leave request id.",
        "parameters": {"type": "object", "properties": {"request_id": {"type": "integer"}}, "required": ["request_id"]},
    },
    "cancel_my_leave": {
        "fn": action_tools.cancel_my_leave,
        "description": "Cancel one of the authenticated user's own leave requests by request id.",
        "parameters": {"type": "object", "properties": {"request_id": {"type": "integer"}}, "required": ["request_id"]},
    },
    "cancel_team_leaves": {
        "fn": action_tools.cancel_team_leaves,
        "description": "For an HOD, cancel upcoming employee leave requests inside one managed team. The scope may be the whole explicitly named team or one explicitly named employee inside that team; use request_ids from the matched preview whenever possible. Requires explicit confirmation=true immediately before execution.",
        "parameters": {"type": "object", "properties": {"team_name": {"type": "string"}, "days": {"type": "integer"}, "employee_names": {"type": "array", "items": {"type": "string"}}, "request_ids": {"type": "array", "items": {"type": "integer"}}, "confirm": {"type": "boolean"}}, "required": ["team_name", "confirm"]},
    },
    "notify_team_members": {
        "fn": action_tools.notify_team_members,
        "description": "For an HOD, send a work notification ONLY to active employees in one explicitly named team managed by that HOD.",
        "parameters": {"type": "object", "properties": {"team_name": {"type": "string"}, "message": {"type": "string"}}, "required": ["team_name", "message"]},
    },
    "end_task": {
        "fn": workspace_tools.end_task,
        "description": "End/complete a task by its task number. Only the task creator or department HOD can do this.",
        "parameters": {"type": "object", "properties": {"task_number": {"type": "string"}}, "required": ["task_number"]},
    },
    "search_company_policy": {
        "fn": knowledge_tools.search_company_policy,
        "description": "Search company policy documents (leave policy, attendance policy, etc.) for an answer to a policy question.",
        "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
    },
    "get_my_attendance_report": {"fn": report_tools.get_my_attendance_report, "description": "Deterministic attendance and working-hours report for the authenticated user over a date/range.", "parameters": {"type": "object", "properties": {"date_range": {"type": "string"}, "start_date": {"type": "string"}, "end_date": {"type": "string"}}, "required": []}},
    "get_employee_attendance_report": {"fn": report_tools.get_employee_attendance_report, "description": "Attendance/working-hours report for one authorized employee.", "parameters": {"type": "object", "properties": {"employee_name": {"type": "string"}, "date_range": {"type": "string"}, "start_date": {"type": "string"}, "end_date": {"type": "string"}}, "required": ["employee_name"]}},
    "get_team_attendance_report": {"fn": report_tools.get_team_attendance_report, "description": "Attendance/working-hours report for one HOD/Super Admin accessible team.", "parameters": {"type": "object", "properties": {"team_name": {"type": "string"}, "date_range": {"type": "string"}, "start_date": {"type": "string"}, "end_date": {"type": "string"}}, "required": ["team_name"]}},
    "get_my_leave_report": {"fn": report_tools.get_my_leave_report, "description": "Deterministic leave report for the authenticated user.", "parameters": {"type": "object", "properties": {"date_range": {"type": "string"}, "start_date": {"type": "string"}, "end_date": {"type": "string"}}, "required": []}},
    "get_employee_leave_report": {"fn": report_tools.get_employee_leave_report, "description": "Leave report for one authorized employee.", "parameters": {"type": "object", "properties": {"employee_name": {"type": "string"}, "date_range": {"type": "string"}, "start_date": {"type": "string"}, "end_date": {"type": "string"}}, "required": ["employee_name"]}},
    "get_team_leave_report": {"fn": report_tools.get_team_leave_report, "description": "Leave report for one accessible team.", "parameters": {"type": "object", "properties": {"team_name": {"type": "string"}, "date_range": {"type": "string"}, "start_date": {"type": "string"}, "end_date": {"type": "string"}}, "required": ["team_name"]}},
    "get_my_task_report": {"fn": report_tools.get_my_task_report, "description": "Deterministic task report for the authenticated user.", "parameters": {"type": "object", "properties": {"date_range": {"type": "string"}, "start_date": {"type": "string"}, "end_date": {"type": "string"}, "status": {"type": "string"}, "overdue_only": {"type": "boolean"}}, "required": []}},
    "get_team_task_report": {"fn": report_tools.get_team_task_report, "description": "Deterministic task report for one accessible team.", "parameters": {"type": "object", "properties": {"team_name": {"type": "string"}, "date_range": {"type": "string"}, "start_date": {"type": "string"}, "end_date": {"type": "string"}, "overdue_only": {"type": "boolean"}}, "required": ["team_name"]}},
    "get_team_members": {"fn": report_tools.get_team_members, "description": "List active members of one accessible team.", "parameters": {"type": "object", "properties": {"team_name": {"type": "string"}}, "required": ["team_name"]}},
    "get_team_details": {"fn": report_tools.get_team_details, "description": "Read one accessible team's basic details.", "parameters": {"type": "object", "properties": {"team_name": {"type": "string"}}, "required": ["team_name"]}},
    "get_employee_details": {"fn": report_tools.get_employee_details, "description": "Read non-secret details for one authorized employee.", "parameters": {"type": "object", "properties": {"employee_name": {"type": "string"}}, "required": ["employee_name"]}},
    "get_team_issue_report": {"fn": report_tools.get_team_issue_report, "description": "List/summarize issues for one accessible team.", "parameters": {"type": "object", "properties": {"team_name": {"type": "string"}, "status": {"type": "string"}}, "required": ["team_name"]}},
    "get_company_info": {"fn": report_tools.get_company_info, "description": "Read authoritative company working-hour settings.", "parameters": {"type": "object", "properties": {}, "required": []}},
    "list_departments": {"fn": report_tools.list_departments, "description": "List departments and teams visible to the authenticated caller.", "parameters": {"type": "object", "properties": {}, "required": []}},
    "get_my_payroll_summary": {"fn": report_tools.get_my_payroll_summary, "description": "Read the authenticated user's authoritative payslip/payroll values.", "parameters": {"type": "object", "properties": {"date_range": {"type": "string"}}, "required": []}},
    "get_team_payroll_summary": {"fn": report_tools.get_team_payroll_summary, "description": "Read authoritative team payslip values for HOD/Super Admin.", "parameters": {"type": "object", "properties": {"team_name": {"type": "string"}, "date_range": {"type": "string"}}, "required": ["team_name"]}},
    "update_task_description": {"fn": workspace_tools.update_task_description, "description": "Update an accessible non-completed task description; backend enforces ownership/role/status.", "parameters": {"type": "object", "properties": {"task_number": {"type": "string"}, "description": {"type": "string"}, "team_name": {"type": "string"}}, "required": ["task_number", "description"]}},
    "update_issue_status": {"fn": action_tools.update_issue_status, "description": "Change an accessible issue to IN_PROGRESS or RESOLVED using existing backend transition rules.", "parameters": {"type": "object", "properties": {"issue_number": {"type": "string"}, "new_status": {"type": "string", "enum": ["IN_PROGRESS", "RESOLVED"]}}, "required": ["issue_number", "new_status"]}},
    "create_notification": {"fn": action_tools.create_notification, "description": "Create an immediate in-app notification for yourself or an authorized employee. Future scheduling is unsupported.", "parameters": {"type": "object", "properties": {"message": {"type": "string"}, "recipient_name": {"type": "string"}, "title": {"type": "string"}}, "required": ["message"]}},

}


def get_tool_declarations():
    """Return tool declarations in the standard function-calling shape."""
    declarations = []
    for name, spec in TOOLS.items():
        declarations.append(
            {
                "name": name,
                "description": spec["description"],
                "parameters": {**spec["parameters"], "additionalProperties": False},
            }
        )
    return declarations


def dispatch_tool(name, user, arguments, idempotency_key=None, conversation=None, confirmed=False):
    """
    Executes a tool by name with the real authenticated `user` bound as
    the first argument. `arguments` come from the model and are passed as
    remaining kwargs only - `user`/scope is never taken from them.
    """
    spec = TOOLS.get(name)
    if spec is None:
        return {"error": f"Unknown tool '{name}'."}

    # Confirmation boundary: mutation tools may only run when the orchestrator
    # has explicitly confirmed a frozen pending workflow. Special team bulk
    # cancellation still performs its own pending-workflow validation below.
    if name in MUTATION_TOOLS and not confirmed:
        return {
            "requires_confirmation": True,
            "error": "This action requires an explicit confirmation preview before execution.",
            "code": "CONFIRMATION_REQUIRED",
        }

    # Defensively strip any scope-like keys the model might have tried
    # to inject (e.g. 'user', 'user_id', 'employee_id' as an override) -
    # tools that need a *target* employee validate it via team membership
    # inside the tool itself, never via a raw id override of the caller.
    safe_args = {k: v for k, v in arguments.items() if k not in ("user", "user_id")}

    # Validate every tool call at the dispatch boundary, including read-only
    # calls. This protects Django tools from malformed/null model arguments
    # regardless of whether the caller is Groq or a deterministic route.
    try:
        from .rule_contract import validate_tool_arguments
        valid, validation_error = validate_tool_arguments(name, safe_args)
    except Exception as exc:
        incident_id = uuid.uuid4().hex[:10]
        logger.exception("[AI ACTION ERROR] incident=%s action=tool_schema_validation tool=%s user_id=%s role=%s reason=validator_failure exception=%s", incident_id, name, getattr(user, "id", None), getattr(user, "role", None), type(exc).__name__)
        return {"error": "I couldn't validate that action safely. Please try again.", "code": "TOOL_SCHEMA_VALIDATION_ERROR", "incident_id": incident_id}
    if not valid:
        incident_id = uuid.uuid4().hex[:10]
        logger.warning("[AI ACTION ERROR] incident=%s action=tool_schema_validation tool=%s user_id=%s role=%s reason=%s backend_function=%s", incident_id, name, getattr(user, "id", None), getattr(user, "role", None), validation_error, getattr(spec.get("fn"), "__name__", str(spec.get("fn"))))
        return {"error": "I couldn't process that action because some details were invalid.", "code": "INVALID_TOOL_ARGUMENTS", "incident_id": incident_id}

    # The model cannot self-authorize a destructive bulk action by simply
    # supplying confirm=true. A confirmation must come from the server-side
    # pending preview created by the deterministic confirmation flow, and the
    # confirmed scope must exactly match that preview.
    if name == "cancel_team_leaves" and safe_args.get("confirm") is True:
        pending = conversation.pending_workflow if conversation is not None else None
        valid_confirmation = False
        if isinstance(pending, dict) and pending.get("action") == "cancel_team_leaves":
            try:
                expires_at = timezone.datetime.fromisoformat(pending.get("expires_at", ""))
                if timezone.is_naive(expires_at):
                    expires_at = timezone.make_aware(expires_at)
                pending_payload = pending.get("payload") or {}
                requested_ids = sorted({int(v) for v in (safe_args.get("request_ids") or [])})
                pending_ids = sorted({int(v) for v in (pending_payload.get("request_ids") or [])})
                valid_confirmation = (
                    timezone.now() <= expires_at
                    and bool(pending_ids)
                    and "team_name" in safe_args
                    and "team_name" in pending_payload
                    and " ".join(str(safe_args["team_name"]).lower().split()) == " ".join(str(pending_payload["team_name"]).lower().split())
                    and requested_ids == pending_ids
                    and (safe_args.get("days") is None or int(safe_args["days"]) == int(pending_payload.get("days", safe_args["days"])))
                )
            except (TypeError, ValueError, OverflowError):
                valid_confirmation = False
        if not valid_confirmation:
            return {
                "error": "Explicit confirmation is required for this bulk cancellation. Preview the exact requests first, then confirm that preview.",
                "code": "CONFIRMATION_REQUIRED",
            }

    def execute_once():
        return spec["fn"](user, **safe_args)

    if idempotency_key:
        from .models import AIActionExecution
        key = str(idempotency_key)[:128]
        with transaction.atomic():
            existing = AIActionExecution.objects.select_for_update().filter(key=key).first()
            if existing:
                if existing.status == AIActionExecution.Status.PROCESSING:
                    # Recover only an abandoned lease. A live action normally
                    # completes well before this window; this avoids permanently
                    # wedging a key after a crashed worker/process.
                    if existing.updated_at and existing.updated_at < timezone.now() - timedelta(minutes=10):
                        existing.status = AIActionExecution.Status.FAILED
                        existing.result = {"error": "Previous action execution expired before completion.", "code": "ACTION_EXPIRED"}
                        existing.save(update_fields=["status", "result", "updated_at"])
                    else:
                        return {"error": "This action is already being processed. Please wait for the current action to finish.", "code": "ACTION_IN_PROGRESS"}
                return existing.result or {"error": "The previous action result is unavailable.", "code": "ACTION_RESULT_UNAVAILABLE"}
            try:
                execution = AIActionExecution.objects.create(
                    key=key, conversation=conversation, tool_name=name, status=AIActionExecution.Status.PROCESSING
                )
            except IntegrityError:
                existing = AIActionExecution.objects.select_for_update().filter(key=key).first()
                if existing:
                    return existing.result or {"error": "The previous action result is unavailable.", "code": "ACTION_RESULT_UNAVAILABLE"}
                raise
            try:
                result = execute_once()
                execution.result = result if isinstance(result, dict) else {"result": result}
                execution.status = AIActionExecution.Status.SUCCEEDED if not (isinstance(result, dict) and result.get("error")) else AIActionExecution.Status.FAILED
                execution.save(update_fields=["status", "result", "updated_at"])
                return execution.result
            except TypeError as e:
                result = {"error": f"Invalid arguments for tool '{name}'.", "code": "INVALID_TOOL_ARGUMENTS", "details": str(e)}
                execution.status = AIActionExecution.Status.FAILED
                execution.result = result
                execution.save(update_fields=["status", "result", "updated_at"])
                return result
            except Exception as e:
                from leave.services import LeaveError
                from workspace.services import WorkspaceError
                # Use module-level logger; do not shadow the imported logging module.
                incident_id = uuid.uuid4().hex[:10]
                backend_function = getattr(spec.get("fn"), "__name__", str(spec.get("fn")))
                if isinstance(e, (LeaveError, WorkspaceError)):
                    reason = getattr(e, "message", str(e))
                    logger.warning("[AI ACTION ERROR] incident=%s action=%s intent=%s tool=%s user_id=%s role=%s reason=%s backend_function=%s exception=%s", incident_id, name, "mutation", name, getattr(user, "id", None), getattr(user, "role", None), reason, backend_function, type(e).__name__)
                    result = {"error": reason, "code": getattr(e, "code", "VALIDATION_ERROR"), "incident_id": incident_id}
                else:
                    logger.exception("[AI ACTION ERROR] incident=%s action=%s intent=%s tool=%s user_id=%s role=%s reason=unhandled_exception backend_function=%s exception=%s", incident_id, name, "mutation", name, getattr(user, "id", None), getattr(user, "role", None), backend_function, type(e).__name__)
                    if isinstance(e, IntegrityError):
                        result = {"error": "This action could not be completed because the data changed or conflicted. Please refresh and try again.", "code": "TOOL_CONFLICT"}
                    elif isinstance(e, DatabaseError):
                        result = {"error": "The operation could not be completed because the database is temporarily unavailable.", "code": "TOOL_DATABASE_ERROR"}
                    else:
                        result = {"error": f"Tool '{name}' could not complete the action. Please try again.", "code": "TOOL_EXECUTION_ERROR"}
                execution.status = AIActionExecution.Status.FAILED
                execution.result = result
                execution.save(update_fields=["status", "result", "updated_at"])
                return result

    try:
        return execute_once()
    except TypeError as e:
        incident_id = uuid.uuid4().hex[:10]
        logger.warning("[AI ACTION ERROR] incident=%s action=%s intent=%s tool=%s user_id=%s role=%s reason=invalid_arguments backend_function=%s exception=%s details=%s", incident_id, name, "tool_dispatch", name, getattr(user, "id", None), getattr(user, "role", None), getattr(spec.get("fn"), "__name__", str(spec.get("fn"))), type(e).__name__, e)
        return {"error": f"I couldn't process that action because some details were invalid. Reference: {incident_id}.", "code": "INVALID_TOOL_ARGUMENTS", "incident_id": incident_id}
    except Exception as e:
        from django.db import DatabaseError, IntegrityError
        from leave.services import LeaveError
        from workspace.services import WorkspaceError
        incident_id = uuid.uuid4().hex[:10]
        backend_function = getattr(spec.get("fn"), "__name__", str(spec.get("fn")))
        if isinstance(e, (LeaveError, WorkspaceError)):
            logger.warning("[AI ACTION ERROR] incident=%s action=%s intent=%s tool=%s user_id=%s role=%s reason=%s backend_function=%s exception=%s", incident_id, name, "mutation", name, getattr(user, "id", None), getattr(user, "role", None), getattr(e, "message", str(e)), backend_function, type(e).__name__)
            return {"error": getattr(e, "message", str(e)), "code": getattr(e, "code", "VALIDATION_ERROR"), "incident_id": incident_id}
        logger.exception("[AI ACTION ERROR] incident=%s action=%s intent=%s tool=%s user_id=%s role=%s reason=unhandled_exception backend_function=%s exception=%s", incident_id, name, "mutation", name, getattr(user, "id", None), getattr(user, "role", None), backend_function, type(e).__name__)
        if isinstance(e, IntegrityError):
            code = "TOOL_CONFLICT"
            message = "This action could not be completed because the data changed or conflicted. Please refresh and try again."
        elif isinstance(e, DatabaseError):
            code = "TOOL_DATABASE_ERROR"
            message = "The operation could not be completed because the database is temporarily unavailable."
        else:
            code = "TOOL_EXECUTION_ERROR"
            message = f"Tool '{name}' could not complete the action. Please try again."
        return {"error": "I couldn't complete that action right now. Please try again.", "code": code, "incident_id": incident_id}
