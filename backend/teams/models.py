from django.db import models


class Team(models.Model):
    department = models.ForeignKey(
        "company.Department", on_delete=models.CASCADE, related_name="teams"
    )
    name = models.CharField(max_length=150)
    created_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, related_name="teams_created"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("department", "name")

    def __str__(self):
        return f"{self.name} ({self.department.name})"


class TeamMembership(models.Model):
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="memberships")
    employee = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="team_memberships"
    )
    is_lead = models.BooleanField(default=False)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("team", "employee")

    def __str__(self):
        return f"{self.employee} in {self.team}" + (" (lead)" if self.is_lead else "")
