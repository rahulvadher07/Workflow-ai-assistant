from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from accounts.models import User
from .models import PolicyDocument
from .views import PolicyDocumentListCreateView


class CompanyPolicyTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.admin = User.objects.create_user(
            username="admin-user", password="StrongPass123!", role=User.Role.SUPER_ADMIN, status=User.Status.ACTIVE
        )
        self.employee = User.objects.create_user(
            username="normal-user", password="StrongPass123!", role=User.Role.EMPLOYEE, status=User.Status.ACTIVE
        )

    def test_policy_upload_is_active_by_default(self):
        pdf = SimpleUploadedFile("policy.pdf", b"%PDF-1.4 test", content_type="application/pdf")
        request = self.factory.post("/api/company/knowledge/", {"title": "Leave Policy", "category": "LEAVE", "file": pdf}, format="multipart")
        force_authenticate(request, user=self.admin)
        response = PolicyDocumentListCreateView.as_view()(request)
        self.assertEqual(response.status_code, 201)
        document = PolicyDocument.objects.get()
        self.assertTrue(document.is_active)

    def test_policy_upload_requires_super_admin(self):
        pdf = SimpleUploadedFile("policy.pdf", b"%PDF-1.4 test", content_type="application/pdf")
        request = self.factory.post("/api/company/knowledge/", {"title": "Leave Policy", "category": "LEAVE", "file": pdf}, format="multipart")
        force_authenticate(request, user=self.employee)
        response = PolicyDocumentListCreateView.as_view()(request)
        self.assertEqual(response.status_code, 403)
