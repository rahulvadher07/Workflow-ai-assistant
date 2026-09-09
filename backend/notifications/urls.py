from django.urls import path
from .views import (
    CreateNotificationView,
    NotificationListView,
    NotificationUnreadCountView,
    NotificationMarkReadView,
    NotificationMarkAllReadView,
    HODDailyBriefView,
)

urlpatterns = [
    path("create/", CreateNotificationView.as_view(), name="notification-create"),
    path("", NotificationListView.as_view(), name="notification-list"),
    path("unread-count/", NotificationUnreadCountView.as_view(), name="notification-unread-count"),
    path("<int:pk>/read/", NotificationMarkReadView.as_view(), name="notification-mark-read"),
    path("mark-all-read/", NotificationMarkAllReadView.as_view(), name="notification-mark-all-read"),
    path("daily-brief/", HODDailyBriefView.as_view(), name="hod-daily-brief"),
]
