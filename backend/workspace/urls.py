from django.urls import path
from .views import (
    TeamConversationListView,
    ConversationMessageListView,
    IssueListCreateView,
    IssueStatusView,
    TaskCreateView,
    TaskStartView,
    TaskEndView,
)

urlpatterns = [
    path("teams/<int:team_id>/conversations/", TeamConversationListView.as_view(), name="team-conversations"),
    path("teams/<int:team_id>/issues/", IssueListCreateView.as_view(), name="team-issues"),
    path("issues/<int:issue_id>/status/", IssueStatusView.as_view(), name="issue-status"),
    path(
        "conversations/<int:conversation_id>/messages/",
        ConversationMessageListView.as_view(),
        name="conversation-messages",
    ),
    path("conversations/<int:conversation_id>/tasks/", TaskCreateView.as_view(), name="conversation-task-create"),
    path("tasks/<int:task_id>/start/", TaskStartView.as_view(), name="task-start"),
    path("tasks/<int:task_id>/end/", TaskEndView.as_view(), name="task-end"),
]
