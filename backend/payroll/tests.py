from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from accounts.models import User
from attendance.models import AttendanceDay
from company.models import Company, PayrollRule
from .models import EmployeeSalary
from .services import calculate_payslip_data


class PayrollCalculationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="payroll-user",
            password="StrongPass123!",
            status=User.Status.ACTIVE,
        )
        company = Company.get_solo()
        company.standard_shift_minutes = 600
        company.save()
        rule = PayrollRule.get_solo()
        rule.overtime_multiplier = Decimal("1.50")
        rule.pf_percent = Decimal("12.00")
        rule.save()
        EmployeeSalary.objects.create(
            employee=self.user,
            basic_monthly_salary=Decimal("60000.00"),
            allowances=Decimal("5000.00"),
        )

    def test_overtime_uses_company_shift_length(self):
        month = timezone.localdate().replace(day=15)
        AttendanceDay.objects.create(
            employee=self.user,
            date=month,
            status=AttendanceDay.Status.PRESENT,
            total_minutes=620,
            overtime_minutes=20,
            punch_count=2,
        )

        data = calculate_payslip_data(self.user, month.year, month.month)
        expected = (
            Decimal("60000.00")
            / Decimal(data["working_days"] * 600)
            * Decimal("20")
            * Decimal("1.50")
        ).quantize(Decimal("0.01"))
        self.assertEqual(data["overtime_amount"], expected)

    def test_payroll_values_are_deterministic_and_rounded(self):
        month = timezone.localdate().replace(day=20)
        data1 = calculate_payslip_data(self.user, month.year, month.month)
        data2 = calculate_payslip_data(self.user, month.year, month.month)
        self.assertEqual(data1, data2)
        self.assertEqual(data1["basic_salary"], Decimal("60000.00"))
        self.assertEqual(data1["gross_salary"], Decimal("65000.00"))
