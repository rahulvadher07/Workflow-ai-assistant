from django.db import models


class LeaveType(models.Model):
    name = models.CharField(max_length=50, unique=True)
    default_annual_quota = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.name


class LeaveBalance(models.Model):
    employee = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="leave_balances")
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)
    total = models.PositiveIntegerField(default=0)
    used = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("employee", "leave_type")

    @property
    def remaining(self):
        return self.total - self.used

    def __str__(self):
        return f"{self.employee} - {self.leave_type}: {self.used}/{self.total}"


class LeaveRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"
        CANCELLED = "CANCELLED", "Cancelled"

    employee = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="leave_requests")
    leave_type = models.ForeignKey(LeaveType, on_delete=models.PROTECT)
    from_date = models.DateField()
    to_date = models.DateField()
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    approved_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    cancelled_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="leave_requests_cancelled")
    cancelled_at = models.DateTimeField(null=True, blank=True)

    @property
    def days(self):
        return (self.to_date - self.from_date).days + 1

    def __str__(self):
        return f"{self.employee} {self.leave_type} {self.from_date}-{self.to_date} ({self.status})"
