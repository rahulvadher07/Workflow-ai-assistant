from rest_framework import serializers
from accounts.models import User
from .models import Team, TeamMembership


class TeamMembershipSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()
    employee_username = serializers.CharField(source="employee.username", read_only=True)

    class Meta:
        model = TeamMembership
        fields = ["id", "employee", "employee_name", "employee_username", "is_lead", "joined_at"]
        read_only_fields = ["id", "joined_at"]

    def get_employee_name(self, obj):
        return obj.employee.get_full_name() or obj.employee.username


class TeamSerializer(serializers.ModelSerializer):
    members = TeamMembershipSerializer(source="memberships", many=True, read_only=True)
    member_count = serializers.SerializerMethodField()

    class Meta:
        model = Team
        fields = ["id", "department", "name", "created_by", "created_at", "members", "member_count"]
        read_only_fields = ["id", "created_by", "created_at", "members", "member_count"]

    def get_member_count(self, obj):
        return obj.memberships.count()


class TeamCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Team
        fields = ["id", "name"]
        read_only_fields = ["id"]


class AddMemberSerializer(serializers.Serializer):
    employee_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(status=User.Status.ACTIVE, role=User.Role.EMPLOYEE)
    )
    is_lead = serializers.BooleanField(default=False, required=False)
