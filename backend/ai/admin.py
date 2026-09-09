from django.contrib import admin
from .models import AIConversation, AIMessage, KnowledgeChunk


class AIMessageInline(admin.TabularInline):
    model = AIMessage
    extra = 0
    readonly_fields = ["role", "content", "tool_name", "tool_result", "created_at"]


@admin.register(AIConversation)
class AIConversationAdmin(admin.ModelAdmin):
    list_display = ["employee", "started_at"]
    inlines = [AIMessageInline]


@admin.register(KnowledgeChunk)
class KnowledgeChunkAdmin(admin.ModelAdmin):
    list_display = ["policy_document", "chunk_index"]
    list_filter = ["policy_document"]
    readonly_fields = ["policy_document", "chunk_index", "chunk_text"]

    def has_add_permission(self, request):
        return False
