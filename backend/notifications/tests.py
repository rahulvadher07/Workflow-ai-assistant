from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import User, EmployeeProfile
from company.models import Company, Department, DepartmentHOD
from teams.models import Team, TeamMembership
from notifications.models import Notification


class ManualNotificationTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username="admin", password="Admin@123", role=User.Role.SUPER_ADMIN, status=User.Status.ACTIVE)
        self.hod = User.objects.create_user(username="hod", password="Hod@123", role=User.Role.HOD, status=User.Status.ACTIVE)
        self.employee = User.objects.create_user(username="emp", password="Emp@123", role=User.Role.EMPLOYEE, status=User.Status.ACTIVE)
        company = Company.get_solo()
        dept = Department.objects.create(company=company, name="IT")
        EmployeeProfile.objects.create(user=self.hod, department=dept, employee_code="HOD-001")
        EmployeeProfile.objects.create(user=self.employee, department=dept, employee_code="EMP-001")
        DepartmentHOD.objects.create(department=dept, hod=self.hod)
        team = Team.objects.create(department=dept, name="Team A", created_by=self.hod)
        TeamMembership.objects.create(team=team, employee=self.employee)
        self.client = APIClient()

    def test_hod_notification_targets_team_members_only(self):
        self.client.force_authenticate(self.hod)
        response = self.client.post("/api/notifications/create/", {"title": "Team update", "message": "Please check."}, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertTrue(Notification.objects.filter(recipient=self.employee, verb=Notification.Verb.ANNOUNCEMENT).exists())
        self.assertTrue(Notification.objects.filter(recipient=self.hod, verb=Notification.Verb.ANNOUNCEMENT).exists())
        self.assertFalse(Notification.objects.filter(recipient=self.admin, verb=Notification.Verb.ANNOUNCEMENT).exists())

    def test_admin_notification_targets_active_staff(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post("/api/notifications/create/", {"title": "Company update", "message": "Everyone please read."}, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertTrue(Notification.objects.filter(recipient=self.hod, verb=Notification.Verb.ANNOUNCEMENT).exists())
        self.assertTrue(Notification.objects.filter(recipient=self.employee, verb=Notification.Verb.ANNOUNCEMENT).exists())
        self.assertTrue(Notification.objects.filter(recipient=self.admin, verb=Notification.Verb.ANNOUNCEMENT).exists())
