from datetime import date, timedelta
from django.test import TestCase
from django.utils import timezone

from accounts.models import EmployeeProfile, User
from company.models import Company, Department, DepartmentHOD
from leave.models import LeaveBalance, LeaveRequest, LeaveType

from .models import AIConversation, AIMessage
from .orchestrator import (
    _extract_task_number_from_text,
    _extract_assignee_name,
    _extract_deadline_datetime,

    _is_quota_exceeded,
    _is_recent_confirmation,
    _is_confirmation_message,
    _store_pending_confirmation,
    _deterministic_action,
)
from .tools.action_tools import cancel_my_leave, get_team_leave_schedule, cancel_team_leaves, notify_team_members
from .tools.workspace_tools import assign_task, update_task_deadline, create_issue_for_team, create_task_for_team, _parse_deadline
from workspace.models import Conversation, Task
from workspace.services import create_task as create_workspace_task
from teams.models import Team, TeamMembership


class AIAgentActionTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Agent Test Co")
        self.department = Department.objects.create(company=self.company, name="Engineering")
        self.hod = User.objects.create_user(
            username="hod-agent", password="TestPass123!", role=User.Role.HOD, status=User.Status.ACTIVE
        )
        EmployeeProfile.objects.create(user=self.hod, department=self.department, employee_code="HOD-01")
        DepartmentHOD.objects.create(department=self.department, hod=self.hod)
        self.employee = User.objects.create_user(
            username="employee-agent", password="TestPass123!", role=User.Role.EMPLOYEE, status=User.Status.ACTIVE
        )
        EmployeeProfile.objects.create(user=self.employee, department=self.department, employee_code="EMP-01")
        self.leave_type = LeaveType.objects.get_or_create(name="CL", defaults={"default_annual_quota": 12})[0]

    def test_task_number_parser_requires_task_keyword(self):
        self.assertEqual(_extract_task_number_from_text("task 07 done"), "07")
        self.assertEqual(_extract_task_number_from_text("task number 12 complete"), "12")
        self.assertIsNone(_extract_task_number_from_text("leave 10-09-2026"))


    def test_team_leave_schedule_does_not_cross_teams(self):
        other_team = Team.objects.create(department=self.department, name="Other")
        team = Team.objects.create(department=self.department, name="Alpha")
        TeamMembership.objects.create(team=team, employee=self.employee)
        leave_type = self.leave_type
        LeaveRequest.objects.create(employee=self.employee, leave_type=leave_type, from_date=date.today()+timedelta(days=1), to_date=date.today()+timedelta(days=1), reason="alpha")
        result = get_team_leave_schedule(self.hod, team_name="Other", days=10)
        self.assertEqual(result["requests"], [])


    def test_my_bulk_leave_cancel_does_not_require_team_name(self):
        from datetime import date, timedelta
        first = LeaveRequest.objects.create(
            employee=self.hod, leave_type=self.leave_type,
            from_date=date.today() + timedelta(days=2),
            to_date=date.today() + timedelta(days=2), reason="first",
            status=LeaveRequest.Status.PENDING,
        )
        second = LeaveRequest.objects.create(
            employee=self.hod, leave_type=self.leave_type,
            from_date=date.today() + timedelta(days=4),
            to_date=date.today() + timedelta(days=4), reason="second",
            status=LeaveRequest.Status.APPROVED,
        )
        conversation = AIConversation.objects.create(employee=self.hod)
        preview = _deterministic_action(self.hod, conversation, "cancel my all leaves", idempotency_seed="bulk-own-test")
        self.assertIn(str(first.id), preview)
        self.assertIn(str(second.id), preview)
        self.assertEqual(conversation.pending_workflow["action"], "cancel_my_leaves")
        self.assertNotIn("team name", preview.lower())


    def test_confirmation_aliases_cancel_exact_personal_leave_ids(self):
        confirmations = ("yes", "yes.", "ha", "હા", "ok", "okay", "done")
        for index, confirmation in enumerate(confirmations):
            conversation = AIConversation.objects.create(employee=self.hod)
            first = LeaveRequest.objects.create(
                employee=self.hod, leave_type=self.leave_type,
                from_date=date.today() + timedelta(days=2),
                to_date=date.today() + timedelta(days=2), reason=f"first-{index}",
                status=LeaveRequest.Status.PENDING,
            )
            second = LeaveRequest.objects.create(
                employee=self.hod, leave_type=self.leave_type,
                from_date=date.today() + timedelta(days=4),
                to_date=date.today() + timedelta(days=4), reason=f"second-{index}",
                status=LeaveRequest.Status.APPROVED,
            )
            preview_user = AIMessage.objects.create(conversation=conversation, role=AIMessage.Role.USER, content="cancel my all leaves")
            preview = _deterministic_action(self.hod, conversation, "cancel my all leaves", idempotency_seed=f"preview-{index}")
            preview_assistant = AIMessage.objects.create(conversation=conversation, role=AIMessage.Role.ASSISTANT, content=preview)
            pending = conversation.pending_workflow
            conversation.pending_workflow = {
                **pending,
                "preview_user_message_id": preview_user.id,
                "preview_assistant_message_id": preview_assistant.id,
            }
            conversation.save(update_fields=["pending_workflow"])

            AIMessage.objects.create(conversation=conversation, role=AIMessage.Role.USER, content=confirmation)
            result = _deterministic_action(self.hod, conversation, confirmation, idempotency_seed=f"confirm-{index}")
            self.assertIn("cancelled", result.lower())
            first.refresh_from_db()
            second.refresh_from_db()
            self.assertEqual(first.status, LeaveRequest.Status.CANCELLED)
            self.assertEqual(second.status, LeaveRequest.Status.CANCELLED)

    def test_confirmation_requires_immediate_previous_preview(self):
        conversation = AIConversation.objects.create(employee=self.hod)
        leave = LeaveRequest.objects.create(
            employee=self.hod, leave_type=self.leave_type,
            from_date=date.today() + timedelta(days=2),
            to_date=date.today() + timedelta(days=2), reason="pending",
            status=LeaveRequest.Status.PENDING,
        )
        preview_user = AIMessage.objects.create(conversation=conversation, role=AIMessage.Role.USER, content="cancel my all leaves")
        preview = _deterministic_action(self.hod, conversation, "cancel my all leaves", idempotency_seed="immediate-test")
        preview_assistant = AIMessage.objects.create(conversation=conversation, role=AIMessage.Role.ASSISTANT, content=preview)
        conversation.pending_workflow = {
            **conversation.pending_workflow,
            "preview_user_message_id": preview_user.id,
            "preview_assistant_message_id": preview_assistant.id,
        }
        conversation.save(update_fields=["pending_workflow"])
        # Any intervening user message invalidates the confirmation context.
        AIMessage.objects.create(conversation=conversation, role=AIMessage.Role.USER, content="show my profile")
        AIMessage.objects.create(conversation=conversation, role=AIMessage.Role.USER, content="yes")
        result = _deterministic_action(self.hod, conversation, "yes", idempotency_seed="stale-confirm")
        self.assertIsNone(result)
        leave.refresh_from_db()
        self.assertEqual(leave.status, LeaveRequest.Status.PENDING)

    def test_bulk_cancel_requires_exact_team_scope(self):
        team = Team.objects.create(department=self.department, name="Alpha")
        TeamMembership.objects.create(team=team, employee=self.employee)
        leave = LeaveRequest.objects.create(employee=self.employee, leave_type=self.leave_type, from_date=date.today()+timedelta(days=1), to_date=date.today()+timedelta(days=1), reason="planned")
        preview = cancel_team_leaves(self.hod, team_name="Alpha", days=10, confirm=False)
        self.assertTrue(preview["requires_confirmation"])
        result = cancel_team_leaves(self.hod, team_name="Alpha", request_ids=[leave.id], confirm=True)
        self.assertEqual(result["count"], 1)

    def test_notify_team_members_is_team_scoped(self):
        team = Team.objects.create(department=self.department, name="Alpha")
        other = User.objects.create_user(username="other-agent", password="TestPass123!", role=User.Role.EMPLOYEE, status=User.Status.ACTIVE)
        EmployeeProfile.objects.create(user=other, department=self.department, employee_code="EMP-02")
        TeamMembership.objects.create(team=team, employee=self.employee)
        from notifications.models import Notification
        result = notify_team_members(self.hod, "hello", team_name="Alpha")
        self.assertTrue(result["success"])
        self.assertEqual(result["recipients"], 1)
        self.assertTrue(Notification.objects.filter(recipient=self.employee, title="Message from Alpha HOD").exists())
        self.assertFalse(Notification.objects.filter(recipient=other, title="Message from Alpha HOD").exists())

    def test_natural_deadline_and_assignment_patterns(self):
        self.assertIsNotNone(_extract_deadline_datetime("move task 07 deadline to Friday 10 AM"))
        self.assertEqual(_extract_assignee_name("give task 07 to Rahul"), "Rahul")
        self.assertEqual(_extract_assignee_name("task 07 assign to Rahul"), "Rahul")
    def test_hod_team_leave_schedule_is_department_scoped(self):
        team = Team.objects.create(department=self.department, name="Alpha")
        TeamMembership.objects.create(team=team, employee=self.employee)
        LeaveRequest.objects.create(
            employee=self.employee,
            leave_type=self.leave_type,
            from_date=date.today() + timedelta(days=1),
            to_date=date.today() + timedelta(days=1),
            reason="personal",
        )
        result = get_team_leave_schedule(self.hod, days=10)
        self.assertEqual(len(result["requests"]), 1)
        self.assertEqual(result["requests"][0]["employee_username"], self.employee.username)

    def test_owner_can_cancel_pending_leave(self):
        leave = LeaveRequest.objects.create(
            employee=self.employee,
            leave_type=self.leave_type,
            from_date=date.today() + timedelta(days=2),
            to_date=date.today() + timedelta(days=2),
            reason="personal",
        )
        result = cancel_my_leave(self.employee, leave.id)
        self.assertTrue(result["success"])
        leave.refresh_from_db()
        self.assertEqual(leave.status, LeaveRequest.Status.CANCELLED)

    def test_approved_cancel_releases_used_days(self):
        balance = LeaveBalance.objects.create(employee=self.employee, leave_type=self.leave_type, total=12, used=1)
        leave = LeaveRequest.objects.create(
            employee=self.employee,
            leave_type=self.leave_type,
            from_date=date.today() + timedelta(days=2),
            to_date=date.today() + timedelta(days=2),
            reason="personal",
            status=LeaveRequest.Status.APPROVED,
        )
        result = cancel_my_leave(self.employee, leave.id)
        self.assertTrue(result["success"])
        balance.refresh_from_db()
        self.assertEqual(balance.used, 0)

    def test_confirmation_is_time_limited(self):
        conversation = AIConversation.objects.create(employee=self.hod)
        _store_pending_confirmation(conversation, "cancel_team_leaves", {"days": 10})
        self.assertTrue(_is_recent_confirmation(conversation))

    def test_quota_error_detection(self):
        exc = Exception("429 quota exceeded: generate_content_free_tier_requests")
        self.assertTrue(_is_quota_exceeded(exc))

    def test_hod_bulk_cancel_requires_confirmation(self):
        LeaveRequest.objects.create(
            employee=self.employee,
            leave_type=self.leave_type,
            from_date=date.today() + timedelta(days=1),
            to_date=date.today() + timedelta(days=1),
            reason="planned",
        )
        from .tools.action_tools import cancel_team_leaves
        preview = cancel_team_leaves(self.hod, days=10, confirm=False)
        self.assertTrue(preview["requires_confirmation"])
        leave = LeaveRequest.objects.get(employee=self.employee)
        self.assertEqual(leave.status, LeaveRequest.Status.PENDING)

    def test_hod_bulk_cancel_and_notify_employees(self):
        from notifications.models import Notification
        team = Team.objects.create(department=self.department, name="Alpha")
        TeamMembership.objects.create(team=team, employee=self.employee)
        LeaveRequest.objects.create(
            employee=self.employee,
            leave_type=self.leave_type,
            from_date=date.today() + timedelta(days=1),
            to_date=date.today() + timedelta(days=1),
            reason="planned",
        )
        from .tools.action_tools import cancel_team_leaves
        result = cancel_team_leaves(self.hod, days=10, confirm=True)
        self.assertEqual(result["count"], 1)
        leave = LeaveRequest.objects.get(employee=self.employee)
        self.assertEqual(leave.status, LeaveRequest.Status.CANCELLED)
        self.assertTrue(Notification.objects.filter(recipient=self.employee, title="Leave request cancelled").exists())

    def test_assign_task_by_exact_name_checks_team_membership(self):
        team = Team.objects.create(department=self.department, name="Alpha")
        TeamMembership.objects.create(team=team, employee=self.hod)
        TeamMembership.objects.create(team=team, employee=self.employee)
        conv = Conversation.objects.create(team=team, kind=Conversation.Kind.TASK, title="Test", created_by=self.hod)
        task = create_workspace_task(team, conv, creator=self.hod, description="Login issue")
        result = assign_task(self.hod, task.display_number, self.employee.username)
        self.assertTrue(result["success"])
        task.refresh_from_db()
        self.assertEqual(task.assignee_id, self.employee.id)

    def test_employee_cannot_reassign_other_users_task(self):
        team = Team.objects.create(department=self.department, name="Beta")
        TeamMembership.objects.create(team=team, employee=self.hod)
        TeamMembership.objects.create(team=team, employee=self.employee)
        conv = Conversation.objects.create(team=team, kind=Conversation.Kind.TASK, title="Test", created_by=self.hod)
        task = create_workspace_task(team, conv, creator=self.hod, description="Task")
        result = assign_task(self.employee, task.display_number, self.employee.username)
        self.assertEqual(result.get("code"), "FORBIDDEN")

    def test_update_task_deadline(self):
        team = Team.objects.create(department=self.department, name="Gamma")
        TeamMembership.objects.create(team=team, employee=self.hod)
        conv = Conversation.objects.create(team=team, kind=Conversation.Kind.TASK, title="Test", created_by=self.hod)
        task = create_workspace_task(team, conv, creator=self.hod, description="Task")
        from django.utils import timezone
        dt = timezone.now() + timedelta(days=3)
        result = update_task_deadline(self.hod, task.display_number, dt.isoformat())
        self.assertTrue(result["success"])
        task.refresh_from_db()
        self.assertIsNotNone(task.deadline)

    def test_create_issue_for_team_respects_hod_department_scope(self):
        team = Team.objects.create(department=self.department, name="Alpha Team")
        result = create_issue_for_team(self.hod, "Alpha Team", "Broken login", "Broken login")
        self.assertTrue(result["success"])
        self.assertEqual(result["team"], team.name)
    def test_hod_can_create_task_for_managed_team_without_membership(self):
        team = Team.objects.create(department=self.department, name="Ops")
        result = create_task_for_team(self.hod, "Ops", "Fix dashboard", deadline="tomorrow 10 AM")
        self.assertTrue(result["success"])
        self.assertEqual(result["team"], "Ops")

    def test_task_number_ambiguity_is_rejected(self):
        team_a = Team.objects.create(department=self.department, name="Alpha")
        team_b = Team.objects.create(department=self.department, name="Beta")
        for team in (team_a, team_b):
            TeamMembership.objects.create(team=team, employee=self.employee)
            conv = Conversation.objects.create(team=team, kind=Conversation.Kind.TASK, title="Test", created_by=self.employee)
            create_workspace_task(team, conv, creator=self.employee, description="Task")
        result = assign_task(self.hod, "TASK-1", self.employee.username)
        self.assertIn("multiple accessible teams", result.get("error", ""))

    def test_deadline_parser_supports_dayparts(self):
        parsed = _parse_deadline("next Friday morning")
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed.hour, 9)



    def test_combined_task_assignment_and_deadline_is_atomic(self):
        from .tools.workspace_tools import update_task_assignment_and_deadline
        team = Team.objects.create(department=self.department, name="Delta")
        TeamMembership.objects.create(team=team, employee=self.hod)
        TeamMembership.objects.create(team=team, employee=self.employee)
        conv = Conversation.objects.create(team=team, kind=Conversation.Kind.TASK, title="Test", created_by=self.hod)
        task = create_workspace_task(team, conv, creator=self.hod, description="Task")
        result = update_task_assignment_and_deadline(self.hod, task.display_number, self.employee.username, "next Friday 10 AM")
        self.assertTrue(result["success"])
        task.refresh_from_db()
        self.assertEqual(task.assignee_id, self.employee.id)
        self.assertIsNotNone(task.deadline)

    def test_combined_task_assignment_rejects_outsider_without_partial_update(self):
        from .tools.workspace_tools import update_task_assignment_and_deadline
        team = Team.objects.create(department=self.department, name="Epsilon")
        TeamMembership.objects.create(team=team, employee=self.hod)
        outsider = User.objects.create_user(username="outsider", password="TestPass123!", role=User.Role.EMPLOYEE, status=User.Status.ACTIVE)
        EmployeeProfile.objects.create(user=outsider, department=self.department, employee_code="EMP-OUT")
        conv = Conversation.objects.create(team=team, kind=Conversation.Kind.TASK, title="Test", created_by=self.hod)
        task = create_workspace_task(team, conv, creator=self.hod, description="Task")
        result = update_task_assignment_and_deadline(self.hod, task.display_number, outsider.username, "next Friday 10 AM")
        self.assertIn("active team member", result.get("error", ""))
        task.refresh_from_db()
        self.assertIsNone(task.assignee_id)
        self.assertIsNone(task.deadline)

    def test_deadline_parser_supports_natural_ranges(self):
        friday = _parse_deadline("this Friday afternoon")
        self.assertIsNotNone(friday)
        self.assertEqual(friday.hour, 15)
        monday = _parse_deadline("next Monday after lunch")
        self.assertIsNotNone(monday)
        self.assertEqual(monday.hour, 14)

    def test_name_assignment_uses_full_name_not_only_username(self):
        team = Team.objects.create(department=self.department, name="FullName")
        self.employee.first_name = "Rahul"
        self.employee.last_name = "Patel"
        self.employee.save(update_fields=["first_name", "last_name"])
        TeamMembership.objects.create(team=team, employee=self.hod)
        TeamMembership.objects.create(team=team, employee=self.employee)
        conv = Conversation.objects.create(team=team, kind=Conversation.Kind.TASK, title="Test", created_by=self.hod)
        task = create_workspace_task(team, conv, creator=self.hod, description="Task")
        result = assign_task(self.hod, task.display_number, "Rahul Patel")
        self.assertTrue(result["success"])
        task.refresh_from_db()
        self.assertEqual(task.assignee_id, self.employee.id)

    def test_combined_action_assignee_extraction(self):
        self.assertEqual(_extract_assignee_name("Move task 07 to Rahul from Monday"), "Rahul")
        self.assertEqual(_extract_assignee_name("Assign task 07 to Rahul and change deadline to Friday"), "Rahul")


    def test_deadline_parser_extra_relative_forms(self):
        self.assertIsNotNone(_parse_deadline("in 2 days"))
        self.assertIsNotNone(_parse_deadline("next week"))
        self.assertIsNotNone(_parse_deadline("end of this month"))

    def test_notify_team_members_is_transactional(self):
        from notifications.models import NotificationOutbox
        team = Team.objects.create(department=self.department, name="NotifyAtomic")
        TeamMembership.objects.create(team=team, employee=self.employee)
        result = notify_team_members(self.hod, "atomic", team_name="NotifyAtomic")
        self.assertTrue(result["success"])
        self.assertEqual(NotificationOutbox.objects.count(), 1)


class ConfirmationWorkflowRegressionTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Confirmation Test Co")
        self.department = Department.objects.create(company=self.company, name="Engineering")
        self.hod = User.objects.create_user(username="confirmation-hod", password="TestPass123!", role=User.Role.HOD, status=User.Status.ACTIVE)
        EmployeeProfile.objects.create(user=self.hod, department=self.department, employee_code="HOD-C")
        DepartmentHOD.objects.create(department=self.department, hod=self.hod)
        self.employee = User.objects.create_user(username="confirmation-employee", password="TestPass123!", role=User.Role.EMPLOYEE, status=User.Status.ACTIVE)
        EmployeeProfile.objects.create(user=self.employee, department=self.department, employee_code="EMP-C")
        self.leave_type = LeaveType.objects.get_or_create(name="CL", defaults={"default_annual_quota": 12})[0]

    def test_recent_confirmation_requires_true_flag(self):
        conversation = AIConversation.objects.create(employee=self.hod)
        _store_pending_confirmation(
            conversation,
            "tool_confirmation",
            {"tool_name": "start_my_task", "arguments": {"task_number": "TASK-1"}},
        )
        self.assertTrue(_is_recent_confirmation(conversation))
        conversation.pending_workflow = {**conversation.pending_workflow, "awaiting_confirmation": False}
        conversation.save(update_fields=["pending_workflow"])
        self.assertFalse(_is_recent_confirmation(conversation))

    def test_affirmative_variants_are_recognized(self):
        for text in (
            "yes", "ha", "haa", "હા", "ok", "okay", "done", "confirm",
            "submit", "send it", "send to the admin", "no changes, send it",
            "no changes, send to admin", "yes, submit to admin"
        ):
            self.assertTrue(_is_confirmation_message(text), text)
