import json

from django.test import TestCase

from user.models.role_reporting import RoleReportingLine
from user.tests.helpers import RoleAPITestMixin


class RoleReportingLineAPITests(RoleAPITestMixin, TestCase):
    def test_can_create_list_patch_and_delete_reporting_lines(self):
        admin_role = self.create_role(
            "Reporting Admin",
            {"role_reporting_lines": ["create", "list", "update", "delete"]},
        )
        admin = self.create_user_with_employee(
            email="reporting-admin@example.com",
            username="reportingadmin",
            employee_id="EMP-REPORTING-ADMIN",
            role=admin_role,
        )
        sales_exec = self.create_role("Sales Executive", {})
        sales_manager = self.create_role("Sales Manager", {})
        ceo = self.create_role("CEO", {})

        response = self.client.post(
            f"/api/v1/roles/{sales_exec.id}/reporting-lines",
            data=json.dumps(
                {
                    "reports_to_role_id": sales_manager.id,
                    "relationship_type": "direct",
                }
            ),
            content_type="application/json",
            **self.auth_headers(admin),
        )

        self.assertEqual(response.status_code, 201)
        created = response.json()
        self.assertEqual(created["role_id"], sales_exec.id)
        self.assertEqual(created["role"]["name"], "Sales Executive")
        self.assertEqual(created["reports_to_role_id"], sales_manager.id)
        self.assertEqual(created["reports_to_role"]["name"], "Sales Manager")
        self.assertEqual(created["relationship_type"], "direct")
        self.assertEqual(created["sequence"], 1)

        second_response = self.client.post(
            f"/api/v1/roles/{sales_exec.id}/reporting-lines",
            data=json.dumps(
                {
                    "reports_to_role_id": ceo.id,
                    "relationship_type": "dotted_line",
                }
            ),
            content_type="application/json",
            **self.auth_headers(admin),
        )

        self.assertEqual(second_response.status_code, 201)
        self.assertEqual(second_response.json()["sequence"], 2)

        response = self.client.get(
            (
                f"/api/v1/roles/{sales_exec.id}/reporting-lines"
                f"?relationship_type=direct&search=manager&reports_to_role_id={sales_manager.id}"
            ),
            **self.auth_headers(admin),
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["items"][0]["reports_to_role"]["name"], "Sales Manager")

        response = self.client.patch(
            f"/api/v1/roles/{sales_exec.id}/reporting-lines/{created['id']}",
            data=json.dumps(
                {
                    "reports_to_role_id": ceo.id,
                    "relationship_type": "escalation",
                    "is_active": False,
                }
            ),
            content_type="application/json",
            **self.auth_headers(admin),
        )

        self.assertEqual(response.status_code, 200)
        updated = response.json()
        self.assertEqual(updated["reports_to_role_id"], ceo.id)
        self.assertEqual(updated["relationship_type"], "escalation")
        self.assertFalse(updated["is_active"])

        delete_response = self.client.delete(
            f"/api/v1/roles/{sales_exec.id}/reporting-lines/{updated['id']}",
            **self.auth_headers(admin),
        )
        self.assertEqual(delete_response.status_code, 200)

    def test_employee_can_view_own_reporting_chain_and_direct_report_tree(self):
        manager_role = self.create_role(
            "Sales Manager",
            {"role_reporting_lines": ["list_own"]},
        )
        manager = self.create_user_with_employee(
            email="reporting-manager@example.com",
            username="reportingmanager",
            employee_id="EMP-REPORTING-MANAGER",
            role=manager_role,
        )
        ceo = self.create_role("CEO", {})
        field_officer = self.create_role("Field Officer", {})
        sales_rep = self.create_role("Sales Rep", {})
        junior_rep = self.create_role("Junior Sales Rep", {})

        RoleReportingLine.objects.create(
            role=manager_role,
            reports_to_role=ceo,
            relationship_type="direct",
            sequence=1,
            is_active=True,
        )
        RoleReportingLine.objects.create(
            role=field_officer,
            reports_to_role=manager_role,
            relationship_type="direct",
            sequence=1,
            is_active=True,
        )
        RoleReportingLine.objects.create(
            role=sales_rep,
            reports_to_role=manager_role,
            relationship_type="direct",
            sequence=2,
            is_active=True,
        )
        RoleReportingLine.objects.create(
            role=junior_rep,
            reports_to_role=field_officer,
            relationship_type="direct",
            sequence=1,
            is_active=True,
        )

        response = self.client.get(
            "/api/v1/roles/me/reporting-chain",
            **self.auth_headers(manager),
        )

        self.assertEqual(response.status_code, 200)
        chain = response.json()
        self.assertEqual(chain["role"]["name"], "Sales Manager")
        self.assertEqual(len(chain["chain"]), 1)
        self.assertEqual(chain["chain"][0]["reports_to_role"]["name"], "CEO")

        tree_response = self.client.get(
            "/api/v1/roles/me/reporting-tree",
            **self.auth_headers(manager),
        )

        self.assertEqual(tree_response.status_code, 200)
        tree = tree_response.json()
        self.assertEqual(tree["role"]["name"], "Sales Manager")
        self.assertEqual(len(tree["direct_reports"]), 2)
        self.assertEqual(tree["direct_reports"][0]["role"]["name"], "Field Officer")
        self.assertEqual(tree["direct_reports"][1]["role"]["name"], "Sales Rep")
        self.assertEqual(
            tree["direct_reports"][0]["children"][0]["role"]["name"], "Junior Sales Rep"
        )

    def test_rejects_invalid_direct_reporting_structures(self):
        admin_role = self.create_role(
            "Reporting Admin",
            {"role_reporting_lines": ["create"]},
        )
        admin = self.create_user_with_employee(
            email="reporting-invalid@example.com",
            username="reportinginvalid",
            employee_id="EMP-REPORTING-INVALID",
            role=admin_role,
        )
        field_officer = self.create_role("Field Officer", {})
        manager = self.create_role("Manager", {})
        ceo = self.create_role("CEO", {})

        response = self.client.post(
            f"/api/v1/roles/{field_officer.id}/reporting-lines",
            data=json.dumps({"reports_to_role_id": field_officer.id}),
            content_type="application/json",
            **self.auth_headers(admin),
        )

        self.assertEqual(response.status_code, 400)

        response = self.client.post(
            f"/api/v1/roles/{field_officer.id}/reporting-lines",
            data=json.dumps({"reports_to_role_id": manager.id}),
            content_type="application/json",
            **self.auth_headers(admin),
        )

        self.assertEqual(response.status_code, 201)

        duplicate_direct_response = self.client.post(
            f"/api/v1/roles/{field_officer.id}/reporting-lines",
            data=json.dumps({"reports_to_role_id": ceo.id}),
            content_type="application/json",
            **self.auth_headers(admin),
        )

        self.assertEqual(duplicate_direct_response.status_code, 400)

        cycle_response = self.client.post(
            f"/api/v1/roles/{manager.id}/reporting-lines",
            data=json.dumps({"reports_to_role_id": field_officer.id}),
            content_type="application/json",
            **self.auth_headers(admin),
        )

        self.assertEqual(cycle_response.status_code, 400)

    def test_reporting_chain_marks_legacy_cycles_without_recursing_forever(self):
        employee_role = self.create_role(
            "Legacy Role A",
            {"role_reporting_lines": ["list_own"]},
        )
        employee = self.create_user_with_employee(
            email="reporting-cycle@example.com",
            username="reportingcycle",
            employee_id="EMP-REPORTING-CYCLE",
            role=employee_role,
        )
        role_b = self.create_role("Legacy Role B", {})
        role_c = self.create_role("Legacy Role C", {})

        RoleReportingLine.objects.create(
            role=employee_role,
            reports_to_role=role_b,
            relationship_type="direct",
            sequence=1,
            is_active=True,
        )
        RoleReportingLine.objects.create(
            role=role_b,
            reports_to_role=role_c,
            relationship_type="direct",
            sequence=1,
            is_active=True,
        )
        RoleReportingLine.objects.create(
            role=role_c,
            reports_to_role=employee_role,
            relationship_type="direct",
            sequence=1,
            is_active=True,
        )

        response = self.client.get(
            "/api/v1/roles/me/reporting-chain",
            **self.auth_headers(employee),
        )

        self.assertEqual(response.status_code, 200)
        chain = response.json()["chain"]
        self.assertEqual(len(chain), 3)
        self.assertTrue(chain[-1]["cycle_detected"])
        self.assertEqual(chain[-1]["reports_to_role"]["name"], "Legacy Role A")
