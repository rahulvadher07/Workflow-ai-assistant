from django.contrib import admin
from .models import EmployeeSalary, PayrollPeriod, Payslip


@admin.register(EmployeeSalary)
class EmployeeSalaryAdmin(admin.ModelAdmin):
    list_display = ["employee", "basic_monthly_salary", "allowances", "updated_by", "updated_at"]


@admin.register(PayrollPeriod)
class PayrollPeriodAdmin(admin.ModelAdmin):
    list_display = ["year", "month", "status", "generated_at"]
    list_filter = ["status"]


@admin.register(Payslip)
class PayslipAdmin(admin.ModelAdmin):
    list_display = ["employee", "period", "status", "net_salary", "approved_by", "approved_at"]
    list_filter = ["status", "period"]
    readonly_fields = [f.name for f in Payslip._meta.fields if f.name not in ("status",)]
