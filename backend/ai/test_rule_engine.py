from django.test import SimpleTestCase

from .rule_engine import best_rule, match_rules


class AgentRuleEngineTests(SimpleTestCase):
    def assertRule(self, text, expected_id):
        match = best_rule(text)
        self.assertIsNotNone(match, text)
        self.assertEqual(match["rule"]["id"], expected_id, text)

    def test_leave_cancel_rule(self):
        self.assertRule("Please cancel my leave for 12-09-2026", "LEAVE_CANCEL")

    def test_my_bulk_leave_cancel_rule(self):
        self.assertRule("cancel my all leaves", "MY_BULK_LEAVE_CANCEL")
        self.assertRule("cancel all my leave requests", "MY_BULK_LEAVE_CANCEL")

    def test_hod_team_cancel_rule(self):
        self.assertRule("cancel all team leaves", "HOD_BULK_CANCEL")
        self.assertRule("cancel leaves for team Alpha", "HOD_BULK_CANCEL")

    def test_hod_named_employee_cancel_rule(self):
        self.assertRule("cancel Rahul leaves", "HOD_EMPLOYEE_LEAVE_CANCEL")
        self.assertRule("cancel all leave for Rahul", "HOD_EMPLOYEE_LEAVE_CANCEL")

    def test_scope_specific_leave_rules_beat_generic_rules(self):
        self.assertEqual(best_rule("cancel my all leaves")["rule"]["scope"], "SELF_BULK")
        self.assertEqual(best_rule("cancel team leaves")["rule"]["scope"], "HOD_TEAM_BULK")
        self.assertEqual(best_rule("cancel Rahul leaves")["rule"]["scope"], "HOD_EMPLOYEE_BULK")

    def test_punch_rules(self):
        self.assertRule("punch in", "PUNCH_IN")
        self.assertRule("clock out", "PUNCH_OUT")

    def test_attendance_rule(self):
        self.assertRule("show my attendance today", "ATTENDANCE_VIEW")
        self.assertRule("show attendance summary for this month", "ATTENDANCE_SUMMARY")

    def test_leave_apply_rule(self):
        self.assertRule("I want to apply for leave next Monday", "LEAVE_APPLY")

    def test_task_rules(self):
        self.assertRule("start task 07", "TASK_START")
        self.assertRule("complete task 07", "TASK_COMPLETE")
        self.assertRule("assign task 07 to Rahul", "TASK_ASSIGN")
        self.assertRule("change task 07 deadline to Friday", "TASK_DEADLINE")

    def test_issue_and_policy_rules(self):
        self.assertRule("report a bug in the website", "ISSUE_CREATE")
        self.assertRule("find similar issue", "ISSUE_SEARCH")
        self.assertRule("what is the leave policy", "POLICY_SEARCH")

    def test_match_returns_multiple_candidates_for_debugging(self):
        matches = match_rules("cancel all team leaves")
        self.assertTrue(matches)
        self.assertEqual(matches[0]["rule"]["id"], "HOD_BULK_CANCEL")
