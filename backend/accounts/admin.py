from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from .models import User, EmployeeProfile


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    list_display = ["username", "email", "first_name", "last_name", "role", "status", "is_staff"]
    list_filter = ["role", "status", "is_staff", "is_active"]
    fieldsets = DjangoUserAdmin.fieldsets + (
        ("Platform role", {"fields": ("role", "status")}),
    )
    add_fieldsets = DjangoUserAdmin.add_fieldsets + (
        ("Platform role", {"fields": ("role", "status")}),
    )


@admin.register(EmployeeProfile)
class EmployeeProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "department", "employee_code", "phone", "date_joined_company"]
    list_filter = ["department"]
    search_fields = ["employee_code", "user__username", "user__first_name", "user__last_name"]
