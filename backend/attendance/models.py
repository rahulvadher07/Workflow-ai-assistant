from django.db import models


class PunchRecord(models.Model):
    """
    Append-only log. No `type` field stored - IN/OUT is derived from
    parity (1st, 3rd, 5th... punch of the day = IN; 2nd, 4th, 6th... = OUT).
    No update/delete endpoint exists anywhere in the API for this model.
    """

    employee = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="punch_records"
    )
    timestamp = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["timestamp"]

    def __str__(self):
        return f"{self.employee} @ {self.timestamp}"


class AttendanceDay(models.Model):
    """
    Cached/computed daily rollup, recalculated whenever punches for that
    day change. This is what APIs read from - never recomputed per-request
    from raw punches for list/history views.
    """

    class Status(models.TextChoices):
        PRESENT = "PRESENT", "Present"
        INCOMPLETE = "INCOMPLETE", "Incomplete"
        ABSENT = "ABSENT", "Absent"

    employee = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="attendance_days"
    )
    date = models.DateField()
    first_in = models.DateTimeField(null=True, blank=True)
    last_out = models.DateTimeField(null=True, blank=True)
    total_minutes = models.PositiveIntegerField(default=0)
    break_minutes = models.PositiveIntegerField(default=0)
    overtime_minutes = models.PositiveIntegerField(default=0)
    is_late = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.INCOMPLETE)
    punch_count = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("employee", "date")
        ordering = ["-date"]

    def __str__(self):
        return f"{self.employee} - {self.date} ({self.status})"
