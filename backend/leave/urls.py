from django.urls import path
from .views import HODLeaveApprovalListView, HODLeaveApproveView, HODLeaveRejectView

urlpatterns = [
    path("hod-requests/", HODLeaveApprovalListView.as_view(), name="hod-leave-list"),
    path("hod-requests/<int:pk>/approve/", HODLeaveApproveView.as_view(), name="hod-leave-approve"),
    path("hod-requests/<int:pk>/reject/", HODLeaveRejectView.as_view(), name="hod-leave-reject"),
]
