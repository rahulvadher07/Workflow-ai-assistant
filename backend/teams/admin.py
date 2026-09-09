from django.contrib import admin
from .models import Team, TeamMembership


class TeamMembershipInline(admin.TabularInline):
    model = TeamMembership
    extra = 0


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ["name", "department", "created_by", "created_at"]
    list_filter = ["department"]
    search_fields = ["name"]
    inlines = [TeamMembershipInline]


@admin.register(TeamMembership)
class TeamMembershipAdmin(admin.ModelAdmin):
    list_display = ["team", "employee", "is_lead", "joined_at"]
    list_filter = ["is_lead"]
