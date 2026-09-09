from django.urls import path
from .views import (
    EmployeeSalaryView,
    PayrollGenerateView,
    PayslipListView,
    PayslipDetailView,
    PayslipApproveView,
    PayslipDownloadView,
)

urlpatterns = [
    path("salary/<int:employee_id>/", EmployeeSalaryView.as_view(), name="employee-salary"),
    path("generate/", PayrollGenerateView.as_view(), name="payroll-generate"),
    path("payslips/", PayslipListView.as_view(), name="payslip-list"),
    path("payslips/<int:pk>/", PayslipDetailView.as_view(), name="payslip-detail"),
    path("payslips/<int:pk>/approve/", PayslipApproveView.as_view(), name="payslip-approve"),
    path("payslips/<int:pk>/download/", PayslipDownloadView.as_view(), name="payslip-download"),
]
