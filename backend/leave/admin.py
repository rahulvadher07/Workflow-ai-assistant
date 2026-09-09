from django.contrib import admin
from .models import LeaveType, LeaveBalance, LeaveRequest


@admin.register(LeaveType)
class LeaveTypeAdmin(admin.ModelAdmin):
    list_display = ["name", "default_annual_quota"]


@admin.register(LeaveBalance)
class LeaveBalanceAdmin(admin.ModelAdmin):
    list_display = ["employee", "leave_type", "total", "used"]
    list_filter = ["leave_type"]


@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = ["employee", "leave_type", "from_date", "to_date", "status", "approved_by"]
    list_filter = ["status", "leave_type"]
