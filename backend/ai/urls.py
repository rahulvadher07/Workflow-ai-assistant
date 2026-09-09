from django.urls import path
from .views import AIChatView, AIConversationDetailView, TeamChatAIBoundaryView

urlpatterns = [
    path("chat/", AIChatView.as_view(), name="ai-chat"),
    path("conversations/<int:pk>/", AIConversationDetailView.as_view(), name="ai-conversation-detail"),
    path("team-chat-check/", TeamChatAIBoundaryView.as_view(), name="ai-team-chat-boundary"),
]
