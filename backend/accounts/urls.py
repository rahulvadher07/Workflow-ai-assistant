from django.urls import path
from .views import (
    RegisterView,
    LoginView,
    RefreshView,
    LogoutView,
    ChangePasswordView,
    MeView,
    EmployeeListView,
    PendingRegistrationListView,
    ApproveRegistrationView,
    RejectRegistrationView, HODListView, HODCreateView, AdminUserUpdateView,
)

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("refresh/", RefreshView.as_view(), name="token-refresh"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("change-password/", ChangePasswordView.as_view(), name="change-password"),
    path("me/", MeView.as_view(), name="me"),
    path("employees/", EmployeeListView.as_view(), name="employee-list"),
    path("hods/", HODListView.as_view(), name="hod-list"),
    path("hods/create/", HODCreateView.as_view(), name="hod-create"),
    path("users/<int:pk>/", AdminUserUpdateView.as_view(), name="admin-user-update"),
    path("registrations/pending/", PendingRegistrationListView.as_view(), name="registrations-pending"),
    path("registrations/<int:pk>/approve/", ApproveRegistrationView.as_view(), name="registration-approve"),
    path("registrations/<int:pk>/reject/", RejectRegistrationView.as_view(), name="registration-reject"),
]
