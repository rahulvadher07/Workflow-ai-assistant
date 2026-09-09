from django.urls import path
from .views import (
    PunchView,
    MyAttendanceView,
    MyAttendanceTodayView,
    DepartmentAttendanceView,
    EmployeeMonthlyAttendanceView,
)

urlpatterns = [
    path("punch/", PunchView.as_view(), name="attendance-punch"),
    path("me/", MyAttendanceView.as_view(), name="attendance-me"),
    path("me/today/", MyAttendanceTodayView.as_view(), name="attendance-me-today"),
    path("department/", DepartmentAttendanceView.as_view(), name="attendance-department"),
    path(
        "employee/<int:employee_id>/monthly/",
        EmployeeMonthlyAttendanceView.as_view(),
        name="attendance-employee-monthly",
    ),
]
