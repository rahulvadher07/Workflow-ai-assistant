from django.contrib import admin
from .models import PunchRecord, AttendanceDay


@admin.register(PunchRecord)
class PunchRecordAdmin(admin.ModelAdmin):
    list_display = ["employee", "timestamp", "created_at"]
    list_filter = ["employee"]
    search_fields = ["employee__username"]
    # Read-only in admin too - punches are never edited, only viewed.
    readonly_fields = ["employee", "timestamp", "created_at"]

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(AttendanceDay)
class AttendanceDayAdmin(admin.ModelAdmin):
    list_display = ["employee", "date", "status", "total_minutes", "is_late", "overtime_minutes"]
    list_filter = ["status", "is_late", "date"]
    search_fields = ["employee__username"]
    readonly_fields = [f.name for f in AttendanceDay._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
