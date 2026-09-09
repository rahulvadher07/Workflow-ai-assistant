from django.contrib import admin
from .models import Conversation, Issue, IssueMessage, Task


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ["title", "team", "kind", "created_by", "created_at"]
    list_filter = ["kind", "team"]


@admin.register(Issue)
class IssueAdmin(admin.ModelAdmin):
    list_display = ["display_number", "title", "status", "lead", "created_at", "resolved_at"]
    list_filter = ["status"]
    search_fields = ["title"]


@admin.register(IssueMessage)
class IssueMessageAdmin(admin.ModelAdmin):
    list_display = ["conversation", "sender", "text", "created_at"]
    readonly_fields = ["conversation", "sender", "text", "created_at"]

    def has_add_permission(self, request):
        return False


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ["display_number", "description", "status", "creator", "assignee", "deadline"]
    list_filter = ["status"]
