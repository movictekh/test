import json

from django.test import TestCase

from user.models.role_success_playbook import RoleSuccessPlaybookItem
from user.tests.helpers import RoleAPITestMixin


class RoleSuccessPlaybookAPITests(RoleAPITestMixin, TestCase):
    def test_can_create_list_and_patch_success_playbook_items(self):
        admin_role = self.create_role(
            "Playbook Admin",
            {"role_success_playbook": ["create", "list", "update"]},
        )
        admin = self.create_user_with_employee(
            email="playbook-admin@example.com",
            username="playbookadmin",
            employee_id="EMP-PLAYBOOK-ADMIN",
            role=admin_role,
        )
        target_role = self.create_role("Sales Executive", {})

        payload = {
            "title": "Follow up within 10 minutes",
            "description": "Respond to all new leads immediately.",
            "kind": "best_practice",
        }
        response = self.client.post(
            f"/api/v1/roles/{target_role.id}/success-playbook",
            data=json.dumps(payload),
            content_type="application/json",
            **self.auth_headers(admin),
        )

        self.assertEqual(response.status_code, 201)
        created = response.json()
        self.assertEqual(created["title"], payload["title"])
        self.assertEqual(created["kind"], payload["kind"])
        self.assertEqual(created["sequence"], 1)

        response = self.client.get(
            f"/api/v1/roles/{target_role.id}/success-playbook?kind=best_practice&search=follow&is_active=true",
            **self.auth_headers(admin),
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["items"][0]["description"], payload["description"])

        response = self.client.patch(
            f"/api/v1/roles/{target_role.id}/success-playbook/{created['id']}",
            data=json.dumps({"kind": "winning_strategy", "is_active": False}),
            content_type="application/json",
            **self.auth_headers(admin),
        )

        self.assertEqual(response.status_code, 200)
        updated = response.json()
        self.assertEqual(updated["kind"], "winning_strategy")
        self.assertFalse(updated["is_active"])

    def test_employee_can_list_own_success_playbook_items(self):
        employee_role = self.create_role(
            "Sales Executive",
            {"role_success_playbook": ["list_own"]},
        )
        employee = self.create_user_with_employee(
            email="playbook-user@example.com",
            username="playbookuser",
            employee_id="EMP-PLAYBOOK-USER",
            role=employee_role,
        )
        RoleSuccessPlaybookItem.objects.create(
            role=employee_role,
            title="Update CRM immediately",
            kind="best_practice",
            sequence=1,
        )

        response = self.client.get(
            "/api/v1/roles/me/success-playbook",
            **self.auth_headers(employee),
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["items"][0]["title"], "Update CRM immediately")

    def test_employee_can_get_grouped_own_success_playbook(self):
        employee_role = self.create_role(
            "Sales Executive",
            {"role_success_playbook": ["list_own"]},
        )
        employee = self.create_user_with_employee(
            email="playbook-grouped@example.com",
            username="playbookgrouped",
            employee_id="EMP-PLAYBOOK-GROUPED",
            role=employee_role,
        )
        RoleSuccessPlaybookItem.objects.create(
            role=employee_role,
            title="Update CRM immediately",
            kind="best_practice",
            sequence=1,
        )
        RoleSuccessPlaybookItem.objects.create(
            role=employee_role,
            title="Delayed follow-up",
            kind="common_mistake",
            sequence=2,
        )
        RoleSuccessPlaybookItem.objects.create(
            role=employee_role,
            title="Schedule next meeting before ending current meeting",
            kind="winning_strategy",
            sequence=3,
        )

        response = self.client.get(
            "/api/v1/roles/me/success-playbook/grouped",
            **self.auth_headers(employee),
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data["best_practice"]), 1)
        self.assertEqual(data["best_practice"][0]["title"], "Update CRM immediately")
        self.assertEqual(len(data["common_mistake"]), 1)
        self.assertEqual(data["common_mistake"][0]["title"], "Delayed follow-up")
        self.assertEqual(len(data["winning_strategy"]), 1)
        self.assertEqual(
            data["winning_strategy"][0]["title"],
            "Schedule next meeting before ending current meeting",
        )
        self.assertEqual(data["lesson_learned"], [])

    def test_success_playbook_sequence_auto_increments_when_omitted(self):
        admin_role = self.create_role(
            "Playbook Admin",
            {"role_success_playbook": ["create"]},
        )
        admin = self.create_user_with_employee(
            email="playbook-seq@example.com",
            username="playbookseq",
            employee_id="EMP-PLAYBOOK-SEQ",
            role=admin_role,
        )
        target_role = self.create_role("Sales Executive", {})

        first_response = self.client.post(
            f"/api/v1/roles/{target_role.id}/success-playbook",
            data=json.dumps(
                {"title": "Update CRM immediately", "kind": "best_practice"}
            ),
            content_type="application/json",
            **self.auth_headers(admin),
        )
        second_response = self.client.post(
            f"/api/v1/roles/{target_role.id}/success-playbook",
            data=json.dumps({"title": "Delayed follow-up", "kind": "common_mistake"}),
            content_type="application/json",
            **self.auth_headers(admin),
        )

        self.assertEqual(first_response.status_code, 201)
        self.assertEqual(second_response.status_code, 201)
        self.assertEqual(first_response.json()["sequence"], 1)
        self.assertEqual(second_response.json()["sequence"], 2)

    def test_kind_is_required_when_creating_success_playbook_item(self):
        admin_role = self.create_role(
            "Playbook Admin",
            {"role_success_playbook": ["create"]},
        )
        admin = self.create_user_with_employee(
            email="playbook-required@example.com",
            username="playbookrequired",
            employee_id="EMP-PLAYBOOK-REQ",
            role=admin_role,
        )
        target_role = self.create_role("Sales Executive", {})

        response = self.client.post(
            f"/api/v1/roles/{target_role.id}/success-playbook",
            data=json.dumps({"title": "Update CRM immediately"}),
            content_type="application/json",
            **self.auth_headers(admin),
        )

        self.assertEqual(response.status_code, 422)
