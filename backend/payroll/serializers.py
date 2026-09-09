from rest_framework import serializers
from accounts.models import User
from .models import EmployeeSalary, PayrollPeriod, Payslip


class EmployeeSalarySerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()

    class Meta:
        model = EmployeeSalary
        fields = ["id", "employee", "employee_name", "basic_monthly_salary", "allowances", "updated_by", "updated_at"]
        read_only_fields = ["id", "employee", "employee_name", "updated_by", "updated_at"]

    def validate_basic_monthly_salary(self, value):
        if value < 0:
            raise serializers.ValidationError("Basic monthly salary cannot be negative.")
        return value

    def validate_allowances(self, value):
        if value < 0:
            raise serializers.ValidationError("Allowances cannot be negative.")
        return value

    def get_employee_name(self, obj):
        return obj.employee.get_full_name() or obj.employee.username


class PayrollPeriodSerializer(serializers.ModelSerializer):
    class Meta:
        model = PayrollPeriod
        fields = ["id", "year", "month", "status", "generated_at"]
        read_only_fields = fields


class PayslipSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()
    period_label = serializers.SerializerMethodField()
    pdf_url = serializers.SerializerMethodField()

    class Meta:
        model = Payslip
        fields = [
            "id", "employee", "employee_name", "period", "period_label",
            "working_days", "present_days", "leave_days", "late_days",
            "total_worked_minutes", "overtime_minutes",
            "basic_salary", "allowances", "overtime_amount", "gross_salary",
            "pf_deduction", "other_deductions", "net_salary",
            "status", "approved_by", "approved_at", "pdf_url", "created_at",
        ]
        read_only_fields = fields

    def get_employee_name(self, obj):
        return obj.employee.get_full_name() or obj.employee.username

    def get_period_label(self, obj):
        return f"{obj.period.year}-{obj.period.month:02d}"

    def get_pdf_url(self, obj):
        request = self.context.get("request")
        if obj.pdf_file and request:
            return request.build_absolute_uri(obj.pdf_file.url)
        return None
