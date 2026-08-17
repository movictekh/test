import json

from django.test import TestCase

from user.models.role_workflows import RoleDailyRoutineItem, RoleTaskTemplate
from user.tests.helpers import RoleAPITestMixin


class RoleTaskTemplateAPITests(RoleAPITestMixin, TestCase):
    def test_can_create_list_and_patch_role_task_templates(self):
        admin_role = self.create_role(
            "Template Admin",
            {"role_task_templates": ["create", "list", "update"]},
        )
        admin = self.create_user_with_employee(
            email="template-admin@example.com",
            username="templateadmin",
            employee_id="EMP-TEMPLATE-ADMIN",
            role=admin_role,
        )
        target_role = self.create_role("Surveyor", {})

        payload = {
            "title": "Conduct site survey",
            "description": "Run the initial site inspection workflow.",
            "sequence": 1,
            "default_priority": "high",
            "estimated_minutes": 90,
        }
        response = self.client.post(
            f"/api/v1/roles/{target_role.id}/task-templates",
            data=json.dumps(payload),
            content_type="application/json",
            **self.auth_headers(admin),
        )

        self.assertEqual(response.status_code, 201)
        created = response.json()
        self.assertEqual(created["title"], payload["title"])
        self.assertEqual(created["default_priority"], payload["default_priority"])

        response = self.client.get(
            f"/api/v1/roles/{target_role.id}/task-templates",
            **self.auth_headers(admin),
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(len(data["items"]), 1)
        self.assertEqual(
            data["items"][0]["estimated_minutes"], payload["estimated_minutes"]
        )

        response = self.client.get(
            f"/api/v1/roles/{target_role.id}/task-templates?default_priority=high&search=site&is_active=true",
            **self.auth_headers(admin),
        )

        self.assertEqual(response.status_code, 200)
        filtered = response.json()
        self.assertEqual(filtered["count"], 1)
        self.assertEqual(filtered["items"][0]["title"], payload["title"])

        response = self.client.patch(
            f"/api/v1/roles/{target_role.id}/task-templates/{created['id']}",
            data=json.dumps({"sequence": 2, "is_active": False}),
            content_type="application/json",
            **self.auth_headers(admin),
        )

        self.assertEqual(response.status_code, 200)
        updated = response.json()
        self.assertEqual(updated["sequence"], 2)
        self.assertFalse(updated["is_active"])

    def test_task_template_sequence_auto_increments_when_omitted(self):
        admin_role = self.create_role(
            "Template Admin",
            {"role_task_templates": ["create"]},
        )
        admin = self.create_user_with_employee(
            email="template-seq@example.com",
            username="templateseq",
            employee_id="EMP-TEMPLATE-SEQ",
            role=admin_role,
        )
        target_role = self.create_role("Surveyor", {})

        first_response = self.client.post(
            f"/api/v1/roles/{target_role.id}/task-templates",
            data=json.dumps({"title": "Conduct site survey"}),
            content_type="application/json",
            **self.auth_headers(admin),
        )
        second_response = self.client.post(
            f"/api/v1/roles/{target_role.id}/task-templates",
            data=json.dumps({"title": "Upload coordinates"}),
            content_type="application/json",
            **self.auth_headers(admin),
        )

        self.assertEqual(first_response.status_code, 201)
        self.assertEqual(second_response.status_code, 201)
        self.assertEqual(first_response.json()["sequence"], 1)
        self.assertEqual(second_response.json()["sequence"], 2)

    def test_employee_can_list_own_role_task_templates(self):
        employee_role = self.create_role(
            "Surveyor",
            {"role_task_templates": ["list_own"]},
        )
        employee = self.create_user_with_employee(
            email="surveyor@example.com",
            username="surveyor",
            employee_id="EMP-SURVEYOR",
            role=employee_role,
        )
        RoleTaskTemplate.objects.create(
            role=employee_role,
            title="Upload coordinates",
            sequence=1,
        )

        response = self.client.get(
            "/api/v1/roles/me/task-templates",
            **self.auth_headers(employee),
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(len(data["items"]), 1)
        self.assertEqual(data["items"][0]["title"], "Upload coordinates")


class RoleDailyRoutineAPITests(RoleAPITestMixin, TestCase):
    def test_can_create_list_and_patch_role_daily_routine(self):
        admin_role = self.create_role(
            "Routine Admin",
            {"role_daily_routines": ["create", "list", "update"]},
        )
        admin = self.create_user_with_employee(
            email="routine-admin@example.com",
            username="routineadmin",
            employee_id="EMP-ROUTINE-ADMIN",
            role=admin_role,
        )
        target_role = self.create_role("Surveyor", {})

        payload = {
            "title": "Check dashboard",
            "description": "Review open assignments and alerts.",
            "sequence": 1,
            "time_of_day": "08:00:00",
            "estimated_minutes": 30,
        }
        response = self.client.post(
            f"/api/v1/roles/{target_role.id}/daily-routine",
            data=json.dumps(payload),
            content_type="application/json",
            **self.auth_headers(admin),
        )

        self.assertEqual(response.status_code, 201)
        created = response.json()
        self.assertEqual(created["title"], payload["title"])
        self.assertEqual(created["time_of_day"], payload["time_of_day"])

        response = self.client.get(
            f"/api/v1/roles/{target_role.id}/daily-routine",
            **self.auth_headers(admin),
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(len(data["items"]), 1)
        self.assertEqual(
            data["items"][0]["estimated_minutes"], payload["estimated_minutes"]
        )

        response = self.client.get(
            f"/api/v1/roles/{target_role.id}/daily-routine?search=dashboard&is_active=true",
            **self.auth_headers(admin),
        )

        self.assertEqual(response.status_code, 200)
        filtered = response.json()
        self.assertEqual(filtered["count"], 1)
        self.assertEqual(filtered["items"][0]["title"], payload["title"])

        response = self.client.patch(
            f"/api/v1/roles/{target_role.id}/daily-routine/{created['id']}",
            data=json.dumps({"sequence": 2, "title": "Team briefing"}),
            content_type="application/json",
            **self.auth_headers(admin),
        )

        self.assertEqual(response.status_code, 200)
        updated = response.json()
        self.assertEqual(updated["sequence"], 2)
        self.assertEqual(updated["title"], "Team briefing")

    def test_daily_routine_sequence_auto_increments_when_omitted(self):
        admin_role = self.create_role(
            "Routine Admin",
            {"role_daily_routines": ["create"]},
        )
        admin = self.create_user_with_employee(
            email="routine-seq@example.com",
            username="routineseq",
            employee_id="EMP-ROUTINE-SEQ",
            role=admin_role,
        )
        target_role = self.create_role("Surveyor", {})

        first_response = self.client.post(
            f"/api/v1/roles/{target_role.id}/daily-routine",
            data=json.dumps({"title": "Check dashboard"}),
            content_type="application/json",
            **self.auth_headers(admin),
        )
        second_response = self.client.post(
            f"/api/v1/roles/{target_role.id}/daily-routine",
            data=json.dumps({"title": "Team briefing"}),
            content_type="application/json",
            **self.auth_headers(admin),
        )

        self.assertEqual(first_response.status_code, 201)
        self.assertEqual(second_response.status_code, 201)
        self.assertEqual(first_response.json()["sequence"], 1)
        self.assertEqual(second_response.json()["sequence"], 2)

    def test_employee_can_list_own_daily_routine(self):
        employee_role = self.create_role(
            "Surveyor",
            {"role_daily_routines": ["list_own"]},
        )
        employee = self.create_user_with_employee(
            email="routine-user@example.com",
            username="routineuser",
            employee_id="EMP-ROUTINE-USER",
            role=employee_role,
        )
        RoleDailyRoutineItem.objects.create(
            role=employee_role,
            title="Site inspection",
            sequence=1,
        )

        response = self.client.get(
            "/api/v1/roles/me/daily-routine",
            **self.auth_headers(employee),
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(len(data["items"]), 1)
        self.assertEqual(data["items"][0]["title"], "Site inspection")
