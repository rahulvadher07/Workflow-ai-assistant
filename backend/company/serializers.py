from rest_framework import serializers
from .models import Department, Company, PayrollRule, PolicyDocument, DepartmentHOD, CompanyRule


class DepartmentSerializer(serializers.ModelSerializer):
    hod_name = serializers.SerializerMethodField()
    hod_names = serializers.SerializerMethodField()

    class Meta:
        model = Department
        fields = ["id", "name", "hod", "hod_name", "hod_names", "created_at"]
        read_only_fields = ["id", "created_at", "hod_names"]

    def get_hod_name(self, obj):
        return obj.hod.get_full_name() if obj.hod else None

    def get_hod_names(self, obj):
        names = list(obj.hods.filter(status="ACTIVE").values_list("first_name", "last_name"))
        if obj.hod_id and not any(obj.hod_id == h.id for h in obj.hods.all()):
            names.insert(0, (obj.hod.first_name, obj.hod.last_name))
        return [f"{first} {last}".strip() for first, last in names]


    def update(self, instance, validated_data):
        hod = validated_data.get("hod", serializers.empty)
        instance = super().update(instance, validated_data)
        if hod is not serializers.empty and hod is not None:
            from .models import DepartmentHOD
            DepartmentHOD.objects.get_or_create(department=instance, hod=hod)
        return instance

    def validate_hod(self, value):
        if value is not None and value.role != value.Role.HOD:
            raise serializers.ValidationError("Assigned user must have the HOD role.")
        return value

    def create(self, validated_data):
        # Company is a singleton - the client never supplies it explicitly.
        validated_data["company"] = Company.get_solo()
        return super().create(validated_data)


class DepartmentPublicSerializer(serializers.ModelSerializer):
    """Minimal, safe-for-anyone view — used on the registration form."""

    class Meta:
        model = Department
        fields = ["id", "name"]


class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = ["id", "name", "standard_break_minutes", "shift_start_time", "standard_shift_minutes"]
        read_only_fields = ["id"]


class PayrollRuleSerializer(serializers.ModelSerializer):
    def validate_pf_percent(self, value):
        if value < 0 or value > 100:
            raise serializers.ValidationError("PF percent must be between 0 and 100.")
        return value

    def validate_overtime_multiplier(self, value):
        if value < 0:
            raise serializers.ValidationError("Overtime multiplier cannot be negative.")
        return value

    class Meta:
        model = PayrollRule
        fields = ["id", "pf_percent", "overtime_multiplier", "late_threshold_minutes"]
        read_only_fields = ["id"]


class PolicyDocumentSerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.SerializerMethodField()

    class Meta:
        model = PolicyDocument
        fields = ["id", "title", "category", "file", "uploaded_by", "uploaded_by_name", "is_active", "created_at"]
        read_only_fields = ["id", "uploaded_by", "uploaded_by_name", "is_active", "created_at"]

    def get_uploaded_by_name(self, obj):
        return obj.uploaded_by.get_full_name() if obj.uploaded_by else None


class CompanyRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanyRule
        fields = ["id", "title", "category", "details", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]
