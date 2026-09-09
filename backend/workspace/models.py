from django.db import models, transaction


class Conversation(models.Model):
    """
    Backs both general team chat and issue-specific chat. `kind`
    distinguishes them; one Message model serves both.
    """

    class Kind(models.TextChoices):
        TEAM_GENERAL = "TEAM_GENERAL", "Team General"
        ISSUE = "ISSUE", "Issue"
        TASK = "TASK", "Task"

    team = models.ForeignKey("teams.Team", on_delete=models.CASCADE, related_name="conversations")
    kind = models.CharField(max_length=20, choices=Kind.choices)
    title = models.CharField(max_length=200, blank=True)
    created_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, related_name="conversations_created"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title or f"{self.kind} - {self.team}"


class Issue(models.Model):
    class Status(models.TextChoices):
        OPEN = "OPEN", "Open"
        IN_PROGRESS = "IN_PROGRESS", "In Progress"
        RESOLVED = "RESOLVED", "Resolved"

    conversation = models.OneToOneField(Conversation, on_delete=models.CASCADE, related_name="issue")
    number = models.PositiveIntegerField()  # per-team sequence, e.g. 1 -> "ISSUE-001"
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    lead = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, related_name="issues_led"
    )
    created_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, related_name="issues_created"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    # Idempotency flag for Celery escalation automation (Part 7).
    escalated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("conversation", "number")

    @property
    def display_number(self):
        return f"ISSUE-{self.number:03d}"

    def __str__(self):
        return f"{self.display_number} - {self.title} ({self.status})"

    @classmethod
    def next_number_for_team(cls, team):
        """
        Per-team sequential numbering, safe under concurrency via a locked
        aggregate read inside the caller's transaction.
        """
        last = (
            cls.objects.select_for_update()
            .filter(conversation__team=team)
            .order_by("-number")
            .first()
        )
        return (last.number + 1) if last else 1


class IssueMessage(models.Model):
    """
    Serves both general team chat and issue chat - Conversation.kind
    tells you which. No separate message model per conversation type.
    """

    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, related_name="+")
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.sender}: {self.text[:40]}"


class Task(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        IN_PROGRESS = "IN_PROGRESS", "In Progress"
        COMPLETED = "COMPLETED", "Completed"

    # OneToOne enforces "one task per conversation" at the DB level.
    conversation = models.OneToOneField(Conversation, on_delete=models.CASCADE, related_name="task")
    number = models.PositiveIntegerField()  # per-team sequence, e.g. "TASK-012"
    creator = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, related_name="tasks_created"
    )
    assignee = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="tasks_assigned"
    )
    description = models.TextField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    deadline = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # Idempotency flags for Celery automation (Part 7) - prevent repeated
    # reminder/overdue notifications for the same task.
    reminder_sent_at = models.DateTimeField(null=True, blank=True)
    overdue_notified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("conversation", "number")

    @property
    def display_number(self):
        return f"TASK-{self.number:03d}"

    def __str__(self):
        return f"{self.display_number} - {self.description[:40]} ({self.status})"

    @classmethod
    def next_number_for_team(cls, team):
        last = (
            cls.objects.select_for_update()
            .filter(conversation__team=team)
            .order_by("-number")
            .first()
        )
        return (last.number + 1) if last else 1
