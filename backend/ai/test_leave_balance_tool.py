from django.test import TestCase

from accounts.models import User
from leave.models import LeaveBalance, LeaveType

from .tools.leave_tools import get_my_leave_balance
from .orchestrator import _format_leave_balance_response, _is_own_leave_balance_request


class LeaveBalanceAITests(TestCase):
    def test_employee_real_leave_balance_is_returned(self):
        user = User.objects.create_user(username="employee-leave", password="TestPass123!")
        leave_type = LeaveType.objects.get_or_create(name="CL", defaults={"default_annual_quota": 12})[0]
        LeaveBalance.objects.create(employee=user, leave_type=leave_type, total=12, used=0)

        result = get_my_leave_balance(user)

        self.assertEqual(result["balances"], [
            {"leave_type": "CL", "total": 12, "used": 0, "remaining": 12}
        ])
        self.assertIn("CL: 12 total, 0 used, 12 remaining", _format_leave_balance_response(result))

    def test_hod_real_leave_balance_is_returned(self):
        user = User.objects.create_user(
            username="hod-leave", password="TestPass123!", role=User.Role.HOD, status=User.Status.ACTIVE
        )
        leave_type = LeaveType.objects.get_or_create(name="CL", defaults={"default_annual_quota": 12})[0]
        LeaveBalance.objects.create(employee=user, leave_type=leave_type, total=12, used=0)

        result = get_my_leave_balance(user)

        self.assertEqual(result["balances"][0]["remaining"], 12)
        self.assertIn("CL: 12 total, 0 used, 12 remaining", _format_leave_balance_response(result))


    def test_hod_gets_default_leave_type_when_no_personal_balance_row_exists(self):
        user = User.objects.create_user(
            username="hod-default-leave", password="TestPass123!", role=User.Role.HOD, status=User.Status.ACTIVE
        )
        leave_type = LeaveType.objects.get_or_create(name="CL", defaults={"default_annual_quota": 12})[0]

        result = get_my_leave_balance(user)

        self.assertEqual(result["balances"], [
            {"leave_type": "CL", "total": 12, "used": 0, "remaining": 12}
        ])

    def test_employee_gets_default_leave_type_when_no_personal_balance_row_exists(self):
        user = User.objects.create_user(
            username="employee-default-leave", password="TestPass123!", role=User.Role.EMPLOYEE, status=User.Status.ACTIVE
        )
        LeaveType.objects.get_or_create(name="CL", defaults={"default_annual_quota": 12})[0]

        result = get_my_leave_balance(user)

        self.assertEqual(result["balances"], [
            {"leave_type": "CL", "total": 12, "used": 0, "remaining": 12}
        ])

    def test_balance_intent_detection(self):
        self.assertTrue(_is_own_leave_balance_request("get my leave balance"))
        self.assertTrue(_is_own_leave_balance_request("Show my leave balance"))
        self.assertTrue(_is_own_leave_balance_request("how many leave days do I have"))
        self.assertFalse(_is_own_leave_balance_request("what is the leave balance policy?"))


class LeaveCreationReliabilityTests(TestCase):
    def test_complete_hod_leave_fields_are_supported_by_parser(self):
        from accounts.models import User, EmployeeProfile
        from company.models import Company, Department, DepartmentHOD
        from leave.models import LeaveType
        from .models import AIConversation
        from .orchestrator import _extract_leave_request_fields

        company = Company.objects.create(name="Test Co")
        department = Department.objects.create(company=company, name="IT")
        user = User.objects.create_user(username="hod-parser", password="TestPass123!", role=User.Role.HOD, status=User.Status.ACTIVE)
        EmployeeProfile.objects.create(user=user, department=department, employee_code="HOD-PARSER")
        DepartmentHOD.objects.create(department=department, hod=user)
        LeaveType.objects.get_or_create(name="CL", defaults={"default_annual_quota": 12})[0]
        conversation = AIConversation.objects.create(employee=user)

        result = _extract_leave_request_fields(
            conversation,
            "i want leave for date 10-09-2026, CL, reason : Dadi mari gay",
        )
        self.assertEqual(result["leave_type"], "CL")
        self.assertEqual(result["from_date"], "2026-09-10")
        self.assertEqual(result["to_date"], "2026-09-10")
        self.assertEqual(result["reason"], "Dadi mari gay")
