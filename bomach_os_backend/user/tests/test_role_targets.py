import json
from datetime import date
from decimal import Decimal

from django.test import TestCase

from user.models.role_targets import EmployeeTarget, RoleTargetTemplate
from user.tests.helpers import RoleAPITestMixin


class RoleTargetTemplateAPITests(RoleAPITestMixin, TestCase):
    def test_can_create_list_and_patch_role_target_templates(self):
        admin_role = self.create_role(
            "Role Target Admin",
            {"role_target_templates": ["create", "list", "update"]},
        )
        admin = self.create_user_with_employee(
            email="roletarget-admin@example.com",
            username="roletargetadmin",
            employee_id="EMP-ROLE-TARGET-ADMIN",
            role=admin_role,
        )
        target_role = self.create_role("Sales Executive", {})

        response = self.client.post(
            f"/api/v1/roles/{target_role.id}/target-templates",
            data=json.dumps(
                {
                    "title": "Monthly Sales",
                    "description": "Hit the standard sales goal.",
                    "target_value": "1000000.00",
                    "unit": "NGN",
                    "period": "monthly",
                }
            ),
            content_type="application/json",
            **self.auth_headers(admin),
        )

        self.assertEqual(response.status_code, 201)
        created = response.json()
        self.assertEqual(created["sequence"], 1)
        self.assertEqual(created["period"], "monthly")

        second_response = self.client.post(
            f"/api/v1/roles/{target_role.id}/target-templates",
            data=json.dumps(
                {
                    "title": "New Clients",
                    "target_value": "10.00",
                    "unit": "count",
                    "period": "monthly",
                }
            ),
            content_type="application/json",
            **self.auth_headers(admin),
        )

        self.assertEqual(second_response.status_code, 201)
        self.assertEqual(second_response.json()["sequence"], 2)

        response = self.client.get(
            f"/api/v1/roles/{target_role.id}/target-templates?period=monthly&is_active=true&search=sales",
            **self.auth_headers(admin),
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["items"][0]["title"], "Monthly Sales")

        response = self.client.patch(
            f"/api/v1/roles/{target_role.id}/target-templates/{created['id']}",
            data=json.dumps({"is_active": False, "target_value": "1200000.00"}),
            content_type="application/json",
            **self.auth_headers(admin),
        )

        self.assertEqual(response.status_code, 200)
        updated = response.json()
        self.assertFalse(updated["is_active"])
        self.assertEqual(updated["target_value"], "1200000.00")


class EmployeeTargetAPITests(RoleAPITestMixin, TestCase):
    def create_target_template(
        self, role, title: str, sequence: int = 1
    ) -> RoleTargetTemplate:
        return RoleTargetTemplate.objects.create(
            role=role,
            title=title,
            description=f"{title} target",
            target_value=Decimal("1000000.00"),
            unit="NGN",
            period="monthly",
            sequence=sequence,
            is_active=True,
        )

    def test_can_generate_role_targets_and_skip_duplicates(self):
        admin_role = self.create_role(
            "Employee Target Admin",
            {
                "role_target_templates": ["create"],
                "employee_targets": ["create"],
            },
        )
        admin = self.create_user_with_employee(
            email="employeetarget-admin@example.com",
            username="employeetargetadmin",
            employee_id="EMP-EMP-TARGET-ADMIN",
            role=admin_role,
        )
        sales_role = self.create_role("Sales Executive", {})
        template = self.create_target_template(sales_role, "Monthly Sales")
        employee_one = self.create_user_with_employee(
            email="sales1@example.com",
            username="salesone",
            employee_id="EMP-SALES-001",
            role=sales_role,
        )
        employee_two = self.create_user_with_employee(
            email="sales2@example.com",
            username="salestwo",
            employee_id="EMP-SALES-002",
            role=sales_role,
        )

        payload = {"period_start": "2026-06-01", "period_end": "2026-06-30"}
        response = self.client.post(
            f"/api/v1/roles/{sales_role.id}/targets/generate",
            data=json.dumps(payload),
            content_type="application/json",
            **self.auth_headers(admin),
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["created_count"], 2)
        self.assertEqual(data["skipped_count"], 0)
        self.assertEqual(len(data["items"]), 2)
        self.assertEqual(data["items"][0]["role_target_template"]["id"], template.id)
        self.assertEqual(EmployeeTarget.objects.count(), 2)

        second_response = self.client.post(
            f"/api/v1/roles/{sales_role.id}/targets/generate",
            data=json.dumps(payload),
            content_type="application/json",
            **self.auth_headers(admin),
        )

        self.assertEqual(second_response.status_code, 200)
        second_data = second_response.json()
        self.assertEqual(second_data["created_count"], 0)
        self.assertEqual(second_data["skipped_count"], 2)
        self.assertEqual(EmployeeTarget.objects.count(), 2)

        filtered_response = self.client.post(
            f"/api/v1/roles/{sales_role.id}/targets/generate",
            data=json.dumps(
                {
                    "period_start": "2026-07-01",
                    "period_end": "2026-07-31",
                    "employee_user_ids": [employee_one.user_id],
                }
            ),
            content_type="application/json",
            **self.auth_headers(admin),
        )

        self.assertEqual(filtered_response.status_code, 200)
        filtered_data = filtered_response.json()
        self.assertEqual(filtered_data["created_count"], 1)
        self.assertEqual(
            filtered_data["items"][0]["employee"]["user_id"], employee_one.user_id
        )

    def test_can_generate_and_list_employee_targets(self):
        admin_role = self.create_role(
            "Employee Target Admin",
            {
                "employee_targets": ["create", "list"],
            },
        )
        admin = self.create_user_with_employee(
            email="emp-targets-list-admin@example.com",
            username="emptargetslistadmin",
            employee_id="EMP-EMP-TARGET-LIST-ADMIN",
            role=admin_role,
        )
        sales_role = self.create_role("Sales Executive", {})
        employee = self.create_user_with_employee(
            email="sales-user@example.com",
            username="salesuser",
            employee_id="EMP-SALES-003",
            role=sales_role,
        )
        self.create_target_template(sales_role, "Monthly Sales", sequence=1)
        self.create_target_template(sales_role, "New Clients", sequence=2)

        response = self.client.post(
            f"/api/v1/employees/{employee.user_id}/targets/generate",
            data=json.dumps({"period_start": "2026-06-01", "period_end": "2026-06-30"}),
            content_type="application/json",
            **self.auth_headers(admin),
        )

        self.assertEqual(response.status_code, 200)
        generated = response.json()
        self.assertEqual(generated["created_count"], 2)

        response = self.client.get(
            f"/api/v1/employees/{employee.user_id}/targets?period=monthly&search=sales&period_start=2026-06-01&period_end=2026-06-30&is_active=true",
            **self.auth_headers(admin),
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(
            data["items"][0]["employee"]["employee_id"], employee.employee_id
        )
        self.assertEqual(data["items"][0]["title"], "Monthly Sales")

    def test_employee_can_list_own_targets(self):
        employee_role = self.create_role(
            "Sales Executive",
            {"employee_targets": ["list_own"]},
        )
        employee = self.create_user_with_employee(
            email="own-targets@example.com",
            username="owntargets",
            employee_id="EMP-OWN-TARGETS",
            role=employee_role,
        )
        template = self.create_target_template(
            employee_role, "Monthly Sales", sequence=1
        )
        EmployeeTarget.objects.create(
            employee=employee,
            role=employee_role,
            role_target_template=template,
            title=template.title,
            description=template.description,
            target_value=template.target_value,
            unit=template.unit,
            period=template.period,
            period_start=date(2026, 6, 1),
            period_end=date(2026, 6, 30),
            sequence=template.sequence,
            is_active=True,
        )

        response = self.client.get(
            "/api/v1/employees/me/targets",
            **self.auth_headers(employee),
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["items"][0]["employee"]["user_id"], employee.user_id)
