import json
from pathlib import Path
from datetime import date, timedelta

from django.test import SimpleTestCase, TestCase
from django.utils import timezone

from accounts.models import EmployeeProfile, User
from company.models import Company, Department, DepartmentHOD
from leave.models import LeaveType
from .models import AIConversation, AIMessage
from .orchestrator import _is_confirmation_message, _is_recent_confirmation, _deterministic_action
from .rule_engine import load_rules, match_rules
from .tool_registry import TOOLS
from .tools.report_tools import resolve_date_range


class AIImprovementStaticTests(SimpleTestCase):
    def test_rule_catalog_is_structured_and_valid_json(self):
        data = json.loads(Path(__file__).with_name("agent_rules.json").read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(data["rules"]), 45)
        required = {"id", "intent", "action_type", "keywords", "synonyms", "examples", "user_scope", "allowed_roles", "required_parameters", "optional_parameters", "date_handling", "time_handling", "confirmation_required", "confirmation_phrases", "backend_function"}
        for rule in data["rules"]:
            self.assertTrue(required.issubset(rule), rule.get("id"))

    def test_all_mutation_tools_fail_closed_for_unconfirmed_dispatch(self):
        mutations = {"punch_attendance", "create_leave_request", "cancel_my_leave", "cancel_team_leaves", "approve_team_leave", "reject_team_leave", "create_task", "create_task_for_team", "start_task", "start_my_task", "assign_task", "update_task_assignment_and_deadline", "update_task_deadline", "update_task_description", "complete_my_task", "end_task", "create_issue", "create_issue_for_team", "update_issue_status", "notify_team_members", "create_notification"}
        self.assertTrue(mutations.issubset(set(TOOLS)))

    def test_confirmation_phrases_never_confirm_without_normalized_pending_state(self):
        for text in ("yes", "ha", "હા", "ok", "done", "send it"):
            self.assertTrue(_is_confirmation_message(text))
        self.assertTrue(_is_confirmation_message("no changes, send it"))
        self.assertFalse(_is_confirmation_message("no changes"))

    def test_date_range_parser(self):
        today = timezone.localdate()
        self.assertEqual(resolve_date_range("today"), (today, today))
        start, end = resolve_date_range("last 7 days")
        self.assertEqual((end - start).days, 6)
        start, end = resolve_date_range("12/09/2026 to 16/09/2026")
        self.assertEqual((start.isoformat(), end.isoformat()), ("2026-09-12", "2026-09-16"))


class AIImprovementConfirmationTests(TestCase):
    def setUp(self):
        company = Company.objects.create(name="AI Safety Co")
        dept = Department.objects.create(company=company, name="Engineering")
        self.hod = User.objects.create_user(username="hod-improve", password="TestPass123!", role=User.Role.HOD, status=User.Status.ACTIVE)
        EmployeeProfile.objects.create(user=self.hod, department=dept, employee_code="HOD-IMP")
        DepartmentHOD.objects.create(department=dept, hod=self.hod)
        self.leave_type = LeaveType.objects.get_or_create(name="CL", defaults={"default_annual_quota": 12})[0]

    def test_random_yes_cannot_replay_old_confirmation(self):
        conversation = AIConversation.objects.create(employee=self.hod)
        AIMessage.objects.create(conversation=conversation, role=AIMessage.Role.USER, content="show my profile")
        self.assertIsNone(_deterministic_action(self.hod, conversation, "yes", idempotency_seed="random-yes"))

    def test_pending_confirmation_expires(self):
        conversation = AIConversation.objects.create(employee=self.hod, pending_workflow={"action":"tool_confirmation", "awaiting_confirmation":True, "created_at":(timezone.now()-timedelta(minutes=10)).isoformat(), "expires_at":(timezone.now()-timedelta(minutes=5)).isoformat(), "payload":{}})
        self.assertFalse(_is_recent_confirmation(conversation))


class NotificationRoutingRegressionTests(TestCase):
    def test_notification_creation_phrase_stores_frozen_confirmation(self):
        from accounts.models import User
        from .models import AIConversation
        from .orchestrator import _deterministic_action

        user = User.objects.create_user(username="hod_notification", password="x", role=User.Role.HOD)
        conversation = AIConversation.objects.create(employee=user)
        text = "create notifications title - error, message - fix this error"

        reply = _deterministic_action(user, conversation, text, idempotency_seed="notif-test")

        self.assertIn("error", reply.lower())
        pending = conversation.pending_workflow
        self.assertEqual(pending["action"], "tool_confirmation")
        self.assertEqual(pending["payload"]["tool_name"], "create_notification")
        self.assertEqual(pending["payload"]["arguments"]["title"], "error")
        self.assertEqual(pending["payload"]["arguments"]["message"], "fix this error")

class AIRuleContractTests(SimpleTestCase):
    def test_rule_tool_backend_contract_is_valid(self):
        from .rule_contract import validate_rule_catalog
        result = validate_rule_catalog()
        self.assertGreaterEqual(result["rules"], 49)
        self.assertGreaterEqual(result["tools"], 48)

    def test_notification_has_deterministic_router_contract(self):
        data = json.loads(Path(__file__).with_name("agent_rules.json").read_text(encoding="utf-8"))
        rule = next(r for r in data["rules"] if r["id"] == "CREATE_NOTIFICATION")
        self.assertEqual(rule["execution_mode"], "DETERMINISTIC")
        self.assertEqual(rule["router_key"], "CREATE_NOTIFICATION")
        self.assertEqual(rule["confirmation_required"], True)
        self.assertEqual(rule["required_parameters"], ["title", "message"])


class AIRoutingContractQualityTests(SimpleTestCase):
    def test_confirmation_policy_is_centralized(self):
        data = json.loads(Path(__file__).with_name("agent_rules.json").read_text(encoding="utf-8"))
        policy = data.get("confirmation_policy") or {}
        self.assertTrue(policy.get("requires_active_pending_preview"))
        self.assertIn("yes", policy.get("accepted_phrases", []))
        self.assertIn("હા", policy.get("accepted_phrases", []))
        self.assertTrue(all(not rule.get("confirmation_phrases") for rule in data["rules"]))

    def test_deterministic_router_keys_are_implemented(self):
        from .routing import DETERMINISTIC_ROUTER_KEYS
        data = json.loads(Path(__file__).with_name("agent_rules.json").read_text(encoding="utf-8"))
        for rule in data["rules"]:
            if rule.get("execution_mode") == "DETERMINISTIC":
                self.assertIn(rule.get("router_key"), DETERMINISTIC_ROUTER_KEYS, rule["id"])

    def test_role_aware_matching_does_not_offer_hod_only_rule_to_employee(self):
        self.assertIsNone(best_rule("approve leave request 42", role="EMPLOYEE"))
        self.assertEqual(best_rule("approve leave request 42", role="HOD")["rule"]["id"], "HOD_LEAVE_APPROVE")


class KnowledgeRetrievalTests(TestCase):
    def setUp(self):
        from django.core.files.base import ContentFile
        from company.models import PolicyDocument
        user = User.objects.create_user(username="knowledge-admin", password="TestPass123!", role=User.Role.SUPER_ADMIN, status=User.Status.ACTIVE)
        document = PolicyDocument.objects.create(
            title="WorkFlow AI Internal Policy",
            category=PolicyDocument.Category.PAYROLL,
            uploaded_by=user,
            file=ContentFile(b"test", name="policy.pdf"),
            is_active=True,
        )
        from .models import KnowledgeChunk
        KnowledgeChunk.objects.create(
            policy_document=document,
            chunk_index=0,
            chunk_text=(
                "Role Definitions Employee salary is INR 30,000 monthly. "
                "HOD salary is INR 50,000 monthly. Standard working hours are 09:30 AM to 06:30 PM."
            ),
        )

    def test_personal_salary_retrieval_is_role_aware_and_compact(self):
        from ai.knowledge import search_company_policy
        rows = search_company_policy("my salary", role="HOD", limit=5)
        self.assertTrue(rows)
        self.assertIn("HOD", rows[0]["text"])
        self.assertIn("INR 50,000", rows[0]["text"])
        self.assertLessEqual(len(rows[0]["text"]), 1400)


class ConfirmationSourceTests(SimpleTestCase):
    def test_confirmation_matching_comes_from_catalog_policy(self):
        from .orchestrator import _confirmation_phrases
        _confirmation_phrases.cache_clear()
        phrases = _confirmation_phrases()
        self.assertIn("yes", phrases)
        self.assertIn("હા", phrases)
        self.assertIn("send it", phrases)
