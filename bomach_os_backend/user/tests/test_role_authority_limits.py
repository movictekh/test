from django.test import TestCase

from user.models.employee import Employee
from user.models.user import User
from user.tests.helpers import RoleAPITestMixin


class RoleAuthorityLimitsAPITests(RoleAPITestMixin, TestCase):
    def test_employee_can_get_authority_limits_for_assigned_role(self):
        employee_role = self.create_role(
            "Unit Lead",
            {
                "roles": ["view_own"],
                "leave_requests": ["approve"],
                "projects": ["update"],
            },
        )
        employee = self.create_user_with_employee(
            email="viewer@example.com",
            username="roleviewer",
            employee_id="EMP-ROLE-VIEWER",
            role=employee_role,
        )

        response = self.client.get(
            "/api/v1/roles/me/authority-limits",
            **self.auth_headers(employee),
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()["items"]
        by_permission = {(item["resource"], item["action"]): item for item in data}

        self.assertEqual(
            by_permission[("leave_requests", "approve")]["helper_text"],
            "Approve leave requests.",
        )
        self.assertEqual(
            by_permission[("leave_requests", "approve")]["label"],
            "Approve Leave Requests",
        )
        self.assertEqual(
            by_permission[("projects", "update")]["label"],
            "Update Projects",
        )
        self.assertEqual(
            by_permission[("projects", "update")]["helper_text"],
            "Update projects.",
        )

    def test_returns_403_when_employee_has_no_role_for_authority_limits(self):
        user = User.objects.create_user(
            email="norole@example.com",
            username="noroleuser",
            password="password123",
        )
        employee = Employee.objects.create(
            user=user,
            employee_id="EMP-NO-ROLE",
        )

        response = self.client.get(
            "/api/v1/roles/me/authority-limits",
            **self.auth_headers(employee),
        )

        self.assertEqual(response.status_code, 403)
