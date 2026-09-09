from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType


class Notification(models.Model):
    class Verb(models.TextChoices):
        REGISTRATION_SUBMITTED = "REGISTRATION_SUBMITTED", "Registration Submitted"
        REGISTRATION_APPROVED = "REGISTRATION_APPROVED", "Registration Approved"
        REGISTRATION_REJECTED = "REGISTRATION_REJECTED", "Registration Rejected"
        LEAVE_REQUESTED = "LEAVE_REQUESTED", "Leave Requested"
        LEAVE_APPROVED = "LEAVE_APPROVED", "Leave Approved"
        LEAVE_REJECTED = "LEAVE_REJECTED", "Leave Rejected"
        LEAVE_CANCELLED = "LEAVE_CANCELLED", "Leave Cancelled"
        TASK_ASSIGNED = "TASK_ASSIGNED", "Task Assigned"
        TASK_REMINDER = "TASK_REMINDER", "Task Reminder"
        TASK_OVERDUE = "TASK_OVERDUE", "Task Overdue"
        ISSUE_ESCALATED = "ISSUE_ESCALATED", "Issue Escalated"
        ISSUE_UPDATED = "ISSUE_UPDATED", "Issue Updated"
        PAYSLIP_AVAILABLE = "PAYSLIP_AVAILABLE", "Payslip Available"
        DAILY_BRIEF = "DAILY_BRIEF", "Daily Brief"
        ANNOUNCEMENT = "ANNOUNCEMENT", "Announcement"

    recipient = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="notifications"
    )
    verb = models.CharField(max_length=40, choices=Verb.choices)
    title = models.CharField(max_length=200)
    message = models.TextField(blank=True)

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    related_object = GenericForeignKey("content_type", "object_id")

    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["recipient", "is_read"])]

    def __str__(self):
        return f"{self.recipient}: {self.title}"


class NotificationOutbox(models.Model):
    """Durable delivery record for realtime notification publication."""
    notification = models.OneToOneField(Notification, on_delete=models.CASCADE, related_name="outbox")
    delivered_at = models.DateTimeField(null=True, blank=True)
    attempts = models.PositiveIntegerField(default=0)
    last_error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=["delivered_at", "created_at"])]
