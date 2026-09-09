from rest_framework import serializers
from .models import PunchRecord, AttendanceDay


class PunchRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = PunchRecord
        fields = ["id", "employee", "timestamp", "created_at"]
        read_only_fields = fields


class AttendanceDaySerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()
    is_incomplete = serializers.SerializerMethodField()

    class Meta:
        model = AttendanceDay
        fields = [
            "id", "employee", "employee_name", "date", "first_in", "last_out",
            "total_minutes", "break_minutes", "overtime_minutes",
            "is_late", "status", "punch_count", "is_incomplete",
        ]
        read_only_fields = fields

    def get_employee_name(self, obj):
        return obj.employee.get_full_name() or obj.employee.username

    def get_is_incomplete(self, obj):
        return obj.status == AttendanceDay.Status.INCOMPLETE
