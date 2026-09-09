from django.urls import path
from .views import (
    DepartmentListCreateView,
    DepartmentDetailView,
    DepartmentPublicListView,
    CompanyDetailView,
    PayrollRuleDetailView,
    PolicyDocumentListCreateView,
    PolicyDocumentDetailView,
    CompanyRuleListCreateView,
    CompanyRuleDetailView,
)

urlpatterns = [
    path("departments/", DepartmentListCreateView.as_view(), name="department-list-create"),
    path("departments/<int:pk>/", DepartmentDetailView.as_view(), name="department-detail"),
    path("departments/public/", DepartmentPublicListView.as_view(), name="department-public-list"),
    path("info/", CompanyDetailView.as_view(), name="company-detail"),
    path("payroll-rules/", PayrollRuleDetailView.as_view(), name="payroll-rule-detail"),
    path("knowledge/", PolicyDocumentListCreateView.as_view(), name="policy-document-list-create"),
    path("knowledge/<int:pk>/", PolicyDocumentDetailView.as_view(), name="policy-document-detail"),
    path("rules/", CompanyRuleListCreateView.as_view(), name="company-rule-list-create"),
    path("rules/<int:pk>/", CompanyRuleDetailView.as_view(), name="company-rule-detail"),
]
