from django.contrib import admin
from .models import Company, Department, PolicyDocument, PayrollRule


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ["name", "standard_break_minutes", "shift_start_time", "standard_shift_minutes"]

    def has_add_permission(self, request):
        # Singleton - block creating a second row from admin
        return not Company.objects.exists()


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ["name", "hod", "company", "created_at"]
    list_filter = ["company"]
    search_fields = ["name"]


@admin.register(PolicyDocument)
class PolicyDocumentAdmin(admin.ModelAdmin):
    list_display = ["title", "category", "is_active", "uploaded_by", "created_at"]
    list_filter = ["category", "is_active"]
    search_fields = ["title"]


@admin.register(PayrollRule)
class PayrollRuleAdmin(admin.ModelAdmin):
    list_display = ["pf_percent", "overtime_multiplier", "late_threshold_minutes"]

    def has_add_permission(self, request):
        return not PayrollRule.objects.exists()
