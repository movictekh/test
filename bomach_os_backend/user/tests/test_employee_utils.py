from django.core.exceptions import ValidationError
from django.test import TestCase

from user.api.v1.employee import resolve_reporting_to_employee
from user.models.employee import Employee
from user.models.user import User


class ResolveReportingToEmployeeTests(TestCase):
    def create_employee(self, email: str, username: str, employee_id: str) -> Employee:
        user = User.objects.create_user(
            email=email,
            username=username,
            password="password123",
        )
        return Employee.objects.create(
            user=user,
            employee_id=employee_id,
        )

    def test_resolves_reporting_manager_from_user_id(self):
        manager = self.create_employee(
            email="manager@example.com",
            username="manager",
            employee_id="MEM-MANAGER001",
        )

        resolved = resolve_reporting_to_employee(manager.user_id)

        self.assertEqual(resolved, manager)

    def test_falls_back_to_employee_id(self):
        manager = self.create_employee(
            email="lead@example.com",
            username="lead",
            employee_id="MEM-LEAD000001",
        )

        resolved = resolve_reporting_to_employee(manager.id)

        self.assertEqual(resolved, manager)

    def test_raises_when_user_has_no_employee_profile(self):
        user = User.objects.create_user(
            email="user-only@example.com",
            username="useronly",
            password="password123",
        )

        with self.assertRaises(ValidationError):
            resolve_reporting_to_employee(user.id)
