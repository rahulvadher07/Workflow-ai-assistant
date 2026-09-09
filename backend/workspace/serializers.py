from rest_framework import serializers
from accounts.models import User
from .models import Conversation, Issue, IssueMessage, Task


class IssueMessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.SerializerMethodField()

    class Meta:
        model = IssueMessage
        fields = ["id", "conversation", "sender", "sender_name", "text", "created_at"]
        read_only_fields = ["id", "sender", "sender_name", "created_at"]

    def get_sender_name(self, obj):
        return obj.sender.get_full_name() or obj.sender.username if obj.sender else None


class IssueSerializer(serializers.ModelSerializer):
    display_number = serializers.CharField(read_only=True)
    lead_name = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = Issue
        fields = [
            "id", "conversation", "number", "display_number", "title", "description",
            "status", "lead", "lead_name", "created_by", "created_by_name", "created_at", "resolved_at",
        ]
        read_only_fields = [
            "id", "conversation", "number", "display_number", "status",
            "created_by", "created_at", "resolved_at",
        ]

    def get_lead_name(self, obj):
        return obj.lead.get_full_name() or obj.lead.username if obj.lead else None

    def get_created_by_name(self, obj):
        return obj.created_by.get_full_name() or obj.created_by.username if obj.created_by else None


class IssueCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=200)
    description = serializers.CharField(required=False, allow_blank=True)


class IssueStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Issue.Status.choices)


class TaskSerializer(serializers.ModelSerializer):
    display_number = serializers.CharField(read_only=True)
    creator_name = serializers.SerializerMethodField()
    assignee_name = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = [
            "id", "conversation", "number", "display_number", "creator", "creator_name",
            "assignee", "assignee_name", "description", "status", "deadline",
            "created_at", "started_at", "completed_at",
        ]
        read_only_fields = [
            "id", "conversation", "number", "display_number", "creator", "creator_name",
            "status", "created_at", "started_at", "completed_at",
        ]

    def get_creator_name(self, obj):
        return obj.creator.get_full_name() or obj.creator.username if obj.creator else None

    def get_assignee_name(self, obj):
        return obj.assignee.get_full_name() or obj.assignee.username if obj.assignee else None


class TaskCreateSerializer(serializers.Serializer):
    description = serializers.CharField()
    assignee_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), source="assignee", required=False, allow_null=True
    )
    deadline = serializers.DateTimeField(required=False, allow_null=True)


class ConversationSerializer(serializers.ModelSerializer):
    issue = IssueSerializer(read_only=True)
    task = TaskSerializer(read_only=True)
    has_task = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = ["id", "team", "kind", "title", "created_by", "created_at", "issue", "task", "has_task"]
        read_only_fields = fields

    def get_has_task(self, obj):
        return hasattr(obj, "task")
