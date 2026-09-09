from django.test import TestCase
from rest_framework.test import APIClient

from company.models import Company, Department
from accounts.models import User, EmployeeProfile


class AdminHODManagementTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username="admin", password="Admin@123", role=User.Role.SUPER_ADMIN, status=User.Status.ACTIVE)
        self.company = Company.get_solo()
        self.department = Department.objects.create(company=self.company, name="IT")
        self.client = APIClient()
        self.client.force_authenticate(self.admin)

    def test_admin_can_create_hod(self):
        response = self.client.post("/api/auth/hods/create/", {
            "username": "hod1", "email": "hod1@example.com", "first_name": "First",
            "last_name": "HOD", "password": "HodPass@123", "department_id": self.department.id,
            "employee_code": "HOD-001", "phone": "9999999999",
        }, format="json")
        self.assertEqual(response.status_code, 201)
        hod = User.objects.get(username="hod1")
        self.assertEqual(hod.role, User.Role.HOD)
        self.assertEqual(hod.employee_profile.department_id, self.department.id)
        self.assertTrue(self.department.hods.filter(pk=hod.pk).exists())

    def test_employee_list_contains_employees_only(self):
        employee = User.objects.create_user(username="emp", password="EmpPass@123", role=User.Role.EMPLOYEE, status=User.Status.ACTIVE)
        EmployeeProfile.objects.create(user=employee, department=self.department, employee_code="EMP-001")
        response = self.client.get("/api/auth/employees/")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(all(item["role"] == User.Role.EMPLOYEE for item in response.data))
