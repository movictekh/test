import json

from django.test import TestCase

from user.models.role_career_path import RoleCareerPath
from user.tests.helpers import RoleAPITestMixin


class RoleCareerPathAPITests(RoleAPITestMixin, TestCase):
    def test_can_create_list_patch_and_delete_career_paths(self):
        admin_role = self.create_role(
            "Career Path Admin",
            {"role_career_paths": ["create", "list", "update", "delete"]},
        )
        admin = self.create_user_with_employee(
            email="career-admin@example.com",
            username="careeradmin",
            employee_id="EMP-CAREER-ADMIN",
            role=admin_role,
        )
        junior = self.create_role("Junior FO", {})
        field = self.create_role("Field Officer", {})
        senior = self.create_role("Senior FO", {})
        manager = self.create_role("FO Manager", {})

        response = self.client.post(
            f"/api/v1/roles/{junior.id}/career-path",
            data=json.dumps(
                {
                    "to_role_id": field.id,
                    "description": "Promotion to field officer.",
                    "requirements": "Strong field execution.",
                    "estimated_duration_months": 12,
                }
            ),
            content_type="application/json",
            **self.auth_headers(admin),
        )

        self.assertEqual(response.status_code, 201)
        created = response.json()
        self.assertEqual(created["to_role_id"], field.id)
        self.assertEqual(created["sequence"], 1)

        second_response = self.client.post(
            f"/api/v1/roles/{junior.id}/career-path",
            data=json.dumps(
                {
                    "to_role_id": senior.id,
                    "description": "Fast-track branch.",
                    "requirements": "Exceptional performance.",
                }
            ),
            content_type="application/json",
            **self.auth_headers(admin),
        )

        self.assertEqual(second_response.status_code, 201)
        self.assertEqual(second_response.json()["sequence"], 2)

        response = self.client.get(
            f"/api/v1/roles/{junior.id}/career-path?is_active=true&search=field&to_role_id={field.id}",
            **self.auth_headers(admin),
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["items"][0]["to_role"]["name"], "Field Officer")

        response = self.client.patch(
            f"/api/v1/roles/{junior.id}/career-path/{created['id']}",
            data=json.dumps({"to_role_id": manager.id, "is_active": False}),
            content_type="application/json",
            **self.auth_headers(admin),
        )

        self.assertEqual(response.status_code, 200)
        updated = response.json()
        self.assertEqual(updated["to_role_id"], manager.id)
        self.assertFalse(updated["is_active"])

        delete_response = self.client.delete(
            f"/api/v1/roles/{junior.id}/career-path/{updated['id']}",
            **self.auth_headers(admin),
        )
        self.assertEqual(delete_response.status_code, 200)

    def test_employee_can_list_own_career_paths_and_tree_handles_branching_and_cycles(
        self,
    ):
        employee_role = self.create_role(
            "Junior FO",
            {"role_career_paths": ["list_own"]},
        )
        employee = self.create_user_with_employee(
            email="career-user@example.com",
            username="careeruser",
            employee_id="EMP-CAREER-USER",
            role=employee_role,
        )
        field = self.create_role("Field Officer", {})
        qa = self.create_role("QA Officer", {})
        senior = self.create_role("Senior FO", {})
        manager = self.create_role("FO Manager", {})

        RoleCareerPath.objects.create(
            from_role=employee_role,
            to_role=field,
            description="Standard progression.",
            sequence=1,
            is_active=True,
        )
        RoleCareerPath.objects.create(
            from_role=employee_role,
            to_role=qa,
            description="Alternative branch.",
            sequence=2,
            is_active=True,
        )
        RoleCareerPath.objects.create(
            from_role=field,
            to_role=senior,
            description="Field growth.",
            sequence=1,
            is_active=True,
        )
        RoleCareerPath.objects.create(
            from_role=senior,
            to_role=manager,
            description="Leadership path.",
            sequence=1,
            is_active=True,
        )
        RoleCareerPath.objects.create(
            from_role=manager,
            to_role=employee_role,
            description="Bad cycle.",
            sequence=1,
            is_active=True,
        )

        response = self.client.get(
            "/api/v1/roles/me/career-path",
            **self.auth_headers(employee),
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["count"], 2)
        self.assertEqual(data["items"][0]["to_role"]["name"], "Field Officer")
        self.assertEqual(data["items"][1]["to_role"]["name"], "QA Officer")

        tree_response = self.client.get(
            "/api/v1/roles/me/career-path/tree",
            **self.auth_headers(employee),
        )

        self.assertEqual(tree_response.status_code, 200)
        tree = tree_response.json()
        self.assertEqual(tree["role"]["name"], "Junior FO")
        self.assertEqual(len(tree["paths"]), 2)

        first_branch = tree["paths"][0]
        self.assertEqual(first_branch["to_role"]["name"], "Field Officer")
        self.assertEqual(first_branch["children"][0]["to_role"]["name"], "Senior FO")
        self.assertEqual(
            first_branch["children"][0]["children"][0]["to_role"]["name"], "FO Manager"
        )
        self.assertTrue(
            first_branch["children"][0]["children"][0]["children"][0]["cycle_detected"]
        )
        self.assertEqual(
            first_branch["children"][0]["children"][0]["children"][0]["to_role"][
                "name"
            ],
            "Junior FO",
        )

        second_branch = tree["paths"][1]
        self.assertEqual(second_branch["to_role"]["name"], "QA Officer")
        self.assertEqual(second_branch["children"], [])

    def test_rejects_self_loop_career_path(self):
        admin_role = self.create_role(
            "Career Path Admin",
            {"role_career_paths": ["create"]},
        )
        admin = self.create_user_with_employee(
            email="career-self@example.com",
            username="careerself",
            employee_id="EMP-CAREER-SELF",
            role=admin_role,
        )
        role = self.create_role("Field Officer", {})

        response = self.client.post(
            f"/api/v1/roles/{role.id}/career-path",
            data=json.dumps({"to_role_id": role.id}),
            content_type="application/json",
            **self.auth_headers(admin),
        )

        self.assertEqual(response.status_code, 400)
