from django.contrib import admin
from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ["recipient", "verb", "title", "is_read", "created_at"]
    list_filter = ["verb", "is_read"]
    readonly_fields = ["recipient", "verb", "title", "message", "content_type", "object_id", "created_at"]

    def has_add_permission(self, request):
        return False
