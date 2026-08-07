import json

from django.test import TestCase

from user.models.role_resources import RoleResource
from user.tests.helpers import RoleAPITestMixin


class RoleResourceAPITests(RoleAPITestMixin, TestCase):
    def test_can_create_list_and_patch_role_resources(self):
        admin_role = self.create_role(
            "Resource Admin",
            {"role_resources": ["create", "list", "update"]},
        )
        admin = self.create_user_with_employee(
            email="resource-admin@example.com",
            username="resourceadmin",
            employee_id="EMP-RESOURCE-ADMIN",
            role=admin_role,
        )
        target_role = self.create_role("Surveyor", {})

        payload = {
            "name": "Laptop",
            "description": "Primary field work laptop.",
            "kind": "physical",
        }
        response = self.client.post(
            f"/api/v1/roles/{target_role.id}/resources",
            data=json.dumps(payload),
            content_type="application/json",
            **self.auth_headers(admin),
        )

        self.assertEqual(response.status_code, 201)
        created = response.json()
        self.assertEqual(created["name"], payload["name"])
        self.assertEqual(created["kind"], payload["kind"])
        self.assertEqual(created["sequence"], 1)

        response = self.client.get(
            f"/api/v1/roles/{target_role.id}/resources",
            **self.auth_headers(admin),
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(len(data["items"]), 1)
        self.assertEqual(data["items"][0]["description"], payload["description"])

        response = self.client.get(
            f"/api/v1/roles/{target_role.id}/resources?kind=physical&search=laptop&is_active=true",
            **self.auth_headers(admin),
        )

        self.assertEqual(response.status_code, 200)
        filtered = response.json()
        self.assertEqual(filtered["count"], 1)
        self.assertEqual(filtered["items"][0]["name"], payload["name"])

        response = self.client.patch(
            f"/api/v1/roles/{target_role.id}/resources/{created['id']}",
            data=json.dumps({"kind": "software", "is_active": False}),
            content_type="application/json",
            **self.auth_headers(admin),
        )

        self.assertEqual(response.status_code, 200)
        updated = response.json()
        self.assertEqual(updated["kind"], "software")
        self.assertFalse(updated["is_active"])

    def test_employee_can_list_own_role_resources(self):
        employee_role = self.create_role(
            "Surveyor",
            {"role_resources": ["list_own"]},
        )
        employee = self.create_user_with_employee(
            email="resource-user@example.com",
            username="resourceuser",
            employee_id="EMP-RESOURCE-USER",
            role=employee_role,
        )
        RoleResource.objects.create(
            role=employee_role,
            name="Bomach OS",
            kind="software",
            sequence=1,
        )

        response = self.client.get(
            "/api/v1/roles/me/resources",
            **self.auth_headers(employee),
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(len(data["items"]), 1)
        self.assertEqual(data["items"][0]["name"], "Bomach OS")

    def test_employee_can_get_grouped_own_role_resources(self):
        employee_role = self.create_role(
            "Surveyor",
            {"role_resources": ["list_own"]},
        )
        employee = self.create_user_with_employee(
            email="resource-grouped@example.com",
            username="resourcegrouped",
            employee_id="EMP-RESOURCE-GROUPED",
            role=employee_role,
        )
        RoleResource.objects.create(
            role=employee_role,
            name="Laptop",
            kind="physical",
            sequence=1,
        )
        RoleResource.objects.create(
            role=employee_role,
            name="Bomach OS",
            kind="software",
            sequence=2,
        )
        RoleResource.objects.create(
            role=employee_role,
            name="Survey Calculations",
            kind="skill",
            sequence=3,
        )

        response = self.client.get(
            "/api/v1/roles/me/resources/grouped",
            **self.auth_headers(employee),
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data["physical"]), 1)
        self.assertEqual(data["physical"][0]["name"], "Laptop")
        self.assertEqual(len(data["software"]), 1)
        self.assertEqual(data["software"][0]["name"], "Bomach OS")
        self.assertEqual(len(data["skill"]), 1)
        self.assertEqual(data["skill"][0]["name"], "Survey Calculations")
        self.assertEqual(data["document"], [])

    def test_resource_sequence_auto_increments_when_omitted(self):
        admin_role = self.create_role(
            "Resource Admin",
            {"role_resources": ["create"]},
        )
        admin = self.create_user_with_employee(
            email="resource-seq@example.com",
            username="resourceseq",
            employee_id="EMP-RESOURCE-SEQ",
            role=admin_role,
        )
        target_role = self.create_role("Surveyor", {})

        first_response = self.client.post(
            f"/api/v1/roles/{target_role.id}/resources",
            data=json.dumps({"name": "Laptop", "kind": "physical"}),
            content_type="application/json",
            **self.auth_headers(admin),
        )
        second_response = self.client.post(
            f"/api/v1/roles/{target_role.id}/resources",
            data=json.dumps({"name": "Bomach OS", "kind": "software"}),
            content_type="application/json",
            **self.auth_headers(admin),
        )

        self.assertEqual(first_response.status_code, 201)
        self.assertEqual(second_response.status_code, 201)
        self.assertEqual(first_response.json()["sequence"], 1)
        self.assertEqual(second_response.json()["sequence"], 2)

    def test_kind_is_required_when_creating_role_resource(self):
        admin_role = self.create_role(
            "Resource Admin",
            {"role_resources": ["create"]},
        )
        admin = self.create_user_with_employee(
            email="resource-required@example.com",
            username="resourcerequired",
            employee_id="EMP-RESOURCE-REQ",
            role=admin_role,
        )
        target_role = self.create_role("Surveyor", {})

        response = self.client.post(
            f"/api/v1/roles/{target_role.id}/resources",
            data=json.dumps({"name": "Laptop"}),
            content_type="application/json",
            **self.auth_headers(admin),
        )

        self.assertEqual(response.status_code, 422)
