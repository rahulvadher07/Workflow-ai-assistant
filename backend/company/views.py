import logging

from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from core.permissions_base import IsSuperAdmin
from .models import Department, Company, PayrollRule, PolicyDocument, CompanyRule
logger = logging.getLogger(__name__)

from .serializers import (
    DepartmentSerializer,
    DepartmentPublicSerializer,
    CompanySerializer,
    PayrollRuleSerializer,
    PolicyDocumentSerializer,
    CompanyRuleSerializer,
)


class DepartmentListCreateView(generics.ListCreateAPIView):
    """
    GET: any authenticated user can list departments (needed for
         registration/display purposes elsewhere).
    POST: Super Admin only.
    """

    queryset = Department.objects.select_related("hod").all()

    def get_permissions(self):
        if self.request.method == "POST":
            return [permissions.IsAuthenticated(), IsSuperAdmin()]
        return [permissions.IsAuthenticated()]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return DepartmentSerializer
        return DepartmentSerializer


class DepartmentDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Department.objects.select_related("hod").all()
    serializer_class = DepartmentSerializer
    permission_classes = [permissions.IsAuthenticated, IsSuperAdmin]


class DepartmentPublicListView(generics.ListAPIView):
    """
    Public, unauthenticated list of departments — used by the
    registration form so a new employee can pick a department.
    """

    queryset = Department.objects.all()
    serializer_class = DepartmentPublicSerializer
    permission_classes = [permissions.AllowAny]


class CompanyDetailView(APIView):
    """Singleton company config. Super Admin can update; others can read."""

    def get_permissions(self):
        if self.request.method in ("PUT", "PATCH"):
            return [permissions.IsAuthenticated(), IsSuperAdmin()]
        return [permissions.IsAuthenticated()]

    def get(self, request):
        company = Company.get_solo()
        return Response(CompanySerializer(company).data)

    def patch(self, request):
        company = Company.get_solo()
        serializer = CompanySerializer(company, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class PayrollRuleDetailView(APIView):
    """Singleton payroll rule config. Super Admin can update; others can read."""

    def get_permissions(self):
        if self.request.method in ("PUT", "PATCH"):
            return [permissions.IsAuthenticated(), IsSuperAdmin()]
        return [permissions.IsAuthenticated()]

    def get(self, request):
        rule = PayrollRule.get_solo()
        return Response(PayrollRuleSerializer(rule).data)

    def patch(self, request):
        rule = PayrollRule.get_solo()
        serializer = PayrollRuleSerializer(rule, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class PolicyDocumentListCreateView(generics.ListCreateAPIView):
    """
    GET: any authenticated user can list active policy documents (the AI
         knowledge tool reads through ai/knowledge.py directly, not this
         endpoint - this is for the admin UI list view).
    POST: Super Admin only. Triggers indexing (Part 6's
          ai/knowledge.py::index_policy_document) right after upload so
          the document is searchable immediately.
    """

    queryset = PolicyDocument.objects.filter(is_active=True).order_by("-created_at")
    serializer_class = PolicyDocumentSerializer

    def get_permissions(self):
        if self.request.method == "POST":
            return [permissions.IsAuthenticated(), IsSuperAdmin()]
        return [permissions.IsAuthenticated()]

    def perform_create(self, serializer):
        document = serializer.save(uploaded_by=self.request.user)
        from ai.knowledge import index_policy_document
        try:
            index_policy_document(document)
        except Exception:
            logger.exception(
                "Knowledge document indexing failed after upload: document_id=%s",
                document.id,
            )
            # Indexing failure must not change the existing upload response
            # contract; the saved document can still be re-indexed later.
            pass


class PolicyDocumentDetailView(generics.DestroyAPIView):
    """DELETE: Super Admin only. Matches DepartmentDetailView's pattern."""

    queryset = PolicyDocument.objects.all()
    permission_classes = [permissions.IsAuthenticated, IsSuperAdmin]


class CompanyRuleListCreateView(generics.ListCreateAPIView):
    queryset = CompanyRule.objects.all()
    serializer_class = CompanyRuleSerializer

    def get_permissions(self):
        if self.request.method == "POST":
            return [permissions.IsAuthenticated(), IsSuperAdmin()]
        return [permissions.IsAuthenticated()]


class CompanyRuleDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = CompanyRule.objects.all()
    serializer_class = CompanyRuleSerializer
    permission_classes = [permissions.IsAuthenticated, IsSuperAdmin]
