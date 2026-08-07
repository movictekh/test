import json

from django.test import TestCase

from user.models.role import Role
from user.models.role_description import RoleDescription
from user.tests.helpers import RoleAPITestMixin


class RoleDescriptionAPITests(RoleAPITestMixin, TestCase):
    def test_can_create_get_and_patch_role_description(self):
        admin_role = self.create_role(
            "Role Description Admin",
            {"role_descriptions": ["create", "view", "update"]},
        )
        admin = self.create_user_with_employee(
            email="role-admin@example.com",
            username="roleadmin",
            employee_id="EMP-ROLE-ADMIN",
            role=admin_role,
        )
        target_role = self.create_role("Field Officer", {})

        payload = {
            "purpose": "Drive consistent daily field execution.",
        }

        response = self.client.post(
            f"/api/v1/roles/{target_role.id}/description",
            data=json.dumps(payload),
            content_type="application/json",
            **self.auth_headers(admin),
        )

        self.assertEqual(response.status_code, 201)
        created = response.json()
        self.assertEqual(created["purpose"], payload["purpose"])
        self.assertEqual(created["responsibilities"], "")
        self.assertEqual(created["job_description"], "")

        response = self.client.get(
            f"/api/v1/roles/{target_role.id}/description",
            **self.auth_headers(admin),
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["purpose"], payload["purpose"])

        patch_payload = {
            "responsibilities": "Follow up on all assigned leads and submit daily reports.",
            "job_description": "Own lead conversion activities for assigned territories.",
        }
        response = self.client.patch(
            f"/api/v1/roles/{target_role.id}/description",
            data=json.dumps(patch_payload),
            content_type="application/json",
            **self.auth_headers(admin),
        )

        self.assertEqual(response.status_code, 200)
        updated = response.json()
        self.assertEqual(updated["purpose"], payload["purpose"])
        self.assertEqual(updated["responsibilities"], patch_payload["responsibilities"])
        self.assertEqual(updated["job_description"], patch_payload["job_description"])

    def test_employee_with_own_permissions_can_only_read_assigned_role_description(self):
        employee_role = self.create_role(
            "Sales Executive",
            {"role_descriptions": ["view_own"]},
        )
        other_role = self.create_role("HR Officer", {})
        employee = self.create_user_with_employee(
            email="staff@example.com",
            username="staffuser",
            employee_id="EMP-STAFF-001",
            role=employee_role,
        )

        own_description = RoleDescription.objects.create(
            role=employee_role,
            purpose="Convert qualified leads into paying customers.",
            responsibilities="Call all new leads within 24 hours.",
        )
        RoleDescription.objects.create(
            role=other_role,
            purpose="Maintain HR process consistency.",
            responsibilities="Review all leave requests daily.",
        )

        response = self.client.get(
            "/api/v1/roles/me/description",
            **self.auth_headers(employee),
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["id"], own_description.id)
        self.assertEqual(data["purpose"], own_description.purpose)

        response = self.client.get(
            f"/api/v1/roles/{other_role.id}/description",
            **self.auth_headers(employee),
        )

        self.assertEqual(response.status_code, 403)

    def test_deleting_role_cascades_role_description(self):
        admin_role = self.create_role(
            "Role Manager",
            {"roles": ["delete"]},
        )
        admin = self.create_user_with_employee(
            email="deleter@example.com",
            username="deleter",
            employee_id="EMP-ROLE-DELETE",
            role=admin_role,
        )
        target_role = self.create_role("Operations Lead", {})
        description = RoleDescription.objects.create(
            role=target_role,
            purpose="Coordinate daily site operations.",
            responsibilities="Inspect all active sites every morning.",
        )

        response = self.client.delete(
            f"/api/v1/roles/{target_role.id}",
            **self.auth_headers(admin),
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Role.objects.filter(id=target_role.id).exists())
        self.assertFalse(RoleDescription.objects.filter(id=description.id).exists())
