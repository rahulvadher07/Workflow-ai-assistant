from django.urls import path
from .views import TeamListCreateView, TeamDetailView, TeamMemberView

urlpatterns = [
    path("", TeamListCreateView.as_view(), name="team-list-create"),
    path("<int:pk>/", TeamDetailView.as_view(), name="team-detail"),
    path("<int:pk>/members/", TeamMemberView.as_view(), name="team-add-member"),
    path("<int:pk>/members/<int:employee_id>/", TeamMemberView.as_view(), name="team-remove-member"),
]
