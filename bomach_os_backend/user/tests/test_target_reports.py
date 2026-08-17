import json
from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from user.models.branch import Branch
from user.models.role_targets import EmployeeTarget, EmployeeTargetReport
from user.tests.helpers import RoleAPITestMixin


class TargetReportAPITests(RoleAPITestMixin, TestCase):
    def create_branch(self, name: str, branch_id: str) -> Branch:
        return Branch.objects.create(
            branch_name=name,
            branch_id=branch_id,
            country="Nigeria",
            state="Lagos",
            city="Lagos",
            office_address=f"{name} office",
            contact_email=f"{branch_id.lower()}@example.com",
            contact_phone="+2348012345678",
        )

    def create_target(
        self, employee, target_value="100.00", start_offset=-1, end_offset=1
    ):
        today = timezone.localdate()
        return EmployeeTarget.objects.create(
            employee=employee,
            role=employee.role,
            title="Monthly Sales",
            description="Close qualified sales.",
            target_value=Decimal(target_value),
            unit="count",
            period="monthly",
            period_start=today + timedelta(days=start_offset),
            period_end=today + timedelta(days=end_offset),
            sequence=1,
            is_active=True,
        )

    def submit_report(
        self, employee, target, value="25.00", summary="Completed target work."
    ):
        return self.client.post(
            "/api/v1/target-reports/",
            data=json.dumps(
                {
                    "employee_target_id": target.id,
                    "summary": summary,
                    "progress_value": value,
                }
            ),
            content_type="application/json",
            **self.auth_headers(employee),
        )

    def setUp(self):
        self.lagos = self.create_branch("Lagos", "BR-LAGOS")
        self.abuja = self.create_branch("Abuja", "BR-ABUJA")

        self.employee_role = self.create_role(
            "Target Owner",
            {
                "target_reports": ["create", "list_own", "view_own"],
                "employee_targets": ["list_own"],
            },
        )
        self.employee = self.create_user_with_employee(
            email="target-owner@example.com",
            username="targetowner",
            employee_id="EMP-TARGET-OWNER",
            role=self.employee_role,
        )
        self.employee.branch = self.lagos
        self.employee.save(update_fields=["branch"])

        self.approver_role = self.create_role(
            "Target Approver",
            {"target_reports": ["list", "view", "approve", "reject"]},
        )
        self.approver_role.branches.add(self.lagos)
        self.approver = self.create_user_with_employee(
            email="target-approver@example.com",
            username="targetapprover",
            employee_id="EMP-TARGET-APPROVER",
            role=self.approver_role,
        )
        self.approver.branch = self.lagos
        self.approver.save(update_fields=["branch"])

    def test_approved_reports_accumulate_and_complete_target(self):
        target = self.create_target(self.employee)

        first_response = self.submit_report(self.employee, target, "40.00")
        self.assertEqual(first_response.status_code, 201)
        first = first_response.json()
        self.assertEqual(first["status"], "submitted")

        approve_response = self.client.post(
            f"/api/v1/target-reports/{first['id']}/approve",
            **self.auth_headers(self.approver),
        )
        self.assertEqual(approve_response.status_code, 200)
        self.assertEqual(approve_response.json()["status"], "approved")

        target_response = self.client.get(
            "/api/v1/employees/me/targets",
            **self.auth_headers(self.employee),
        )
        self.assertEqual(target_response.status_code, 200)
        target_data = target_response.json()["items"][0]
        self.assertEqual(target_data["approved_progress_value"], "40.00")
        self.assertEqual(target_data["remaining_value"], "60.00")
        self.assertEqual(target_data["progress_percentage"], "40.00")
        self.assertFalse(target_data["is_completed"])

        second_response = self.submit_report(self.employee, target, "60.00")
        self.assertEqual(second_response.status_code, 201)
        second_id = second_response.json()["id"]
        approve_response = self.client.post(
            f"/api/v1/target-reports/{second_id}/approve",
            **self.auth_headers(self.approver),
        )
        self.assertEqual(approve_response.status_code, 200)

        target.refresh_from_db()
        self.assertEqual(target.get_approved_progress_value(), Decimal("100.00"))
        self.assertTrue(target.get_is_completed())
        self.assertEqual(
            self.submit_report(self.employee, target, "1.00").status_code, 400
        )

    def test_pending_and_rejected_reports_do_not_inflate_progress(self):
        target = self.create_target(self.employee)
        first_response = self.submit_report(self.employee, target, "30.00")
        report_id = first_response.json()["id"]

        duplicate_response = self.submit_report(self.employee, target, "10.00")
        self.assertEqual(duplicate_response.status_code, 400)
        self.assertIn(
            "submitted report already exists", duplicate_response.json()["detail"]
        )

        empty_rejection = self.client.post(
            f"/api/v1/target-reports/{report_id}/reject",
            data=json.dumps({"rejection_reason": "  "}),
            content_type="application/json",
            **self.auth_headers(self.approver),
        )
        self.assertEqual(empty_rejection.status_code, 400)

        rejection = self.client.post(
            f"/api/v1/target-reports/{report_id}/reject",
            data=json.dumps({"rejection_reason": "Evidence was incomplete."}),
            content_type="application/json",
            **self.auth_headers(self.approver),
        )
        self.assertEqual(rejection.status_code, 200)
        self.assertEqual(rejection.json()["status"], "rejected")
        self.assertEqual(target.get_approved_progress_value(), Decimal("0.00"))

        replacement = self.submit_report(self.employee, target, "30.00")
        self.assertEqual(replacement.status_code, 201)
        repeat_rejection = self.client.post(
            f"/api/v1/target-reports/{report_id}/reject",
            data=json.dumps({"rejection_reason": "Second decision."}),
            content_type="application/json",
            **self.auth_headers(self.approver),
        )
        self.assertEqual(repeat_rejection.status_code, 400)

    def test_submission_validates_owner_value_period_and_current_role(self):
        target = self.create_target(self.employee)
        self.assertEqual(
            self.submit_report(self.employee, target, "0.00").status_code, 400
        )
        self.assertEqual(
            self.submit_report(self.employee, target, "101.00").status_code, 400
        )

        other_employee = self.create_user_with_employee(
            email="other-target-owner@example.com",
            username="othertargetowner",
            employee_id="EMP-OTHER-TARGET",
            role=self.employee_role,
        )
        other_employee.branch = self.lagos
        other_employee.save(update_fields=["branch"])
        self.assertEqual(
            self.submit_report(other_employee, target, "10.00").status_code, 400
        )

        expired_target = self.create_target(
            self.employee, start_offset=-3, end_offset=-1
        )
        self.assertEqual(
            self.submit_report(self.employee, expired_target, "10.00").status_code, 400
        )

        stale_target = self.create_target(self.employee)
        replacement_role = self.create_role(
            "Replacement Role",
            {"target_reports": ["create"]},
        )
        self.employee.role = replacement_role
        self.employee.save(update_fields=["role"])
        self.assertEqual(
            self.submit_report(self.employee, stale_target, "10.00").status_code, 400
        )

    def test_approval_is_permission_based_branch_scoped_and_not_self_service(self):
        self.employee_role.permissions["target_reports"].append("approve")
        self.employee_role.save(update_fields=["permissions"])
        target = self.create_target(self.employee)
        report_id = self.submit_report(self.employee, target, "25.00").json()["id"]

        self_approval = self.client.post(
            f"/api/v1/target-reports/{report_id}/approve",
            **self.auth_headers(self.employee),
        )
        self.assertEqual(self_approval.status_code, 400)

        wrong_branch_role = self.create_role(
            "Wrong Branch Approver",
            {"target_reports": ["approve"]},
        )
        wrong_branch_role.branches.add(self.abuja)
        wrong_branch_approver = self.create_user_with_employee(
            email="wrong-branch@example.com",
            username="wrongbranch",
            employee_id="EMP-WRONG-BRANCH",
            role=wrong_branch_role,
        )
        wrong_branch_approver.branch = self.abuja
        wrong_branch_approver.save(update_fields=["branch"])
        wrong_branch_response = self.client.post(
            f"/api/v1/target-reports/{report_id}/approve",
            **self.auth_headers(wrong_branch_approver),
        )
        self.assertEqual(wrong_branch_response.status_code, 403)

        no_permission = self.create_user_with_employee(
            email="no-target-permission@example.com",
            username="notargetpermission",
            employee_id="EMP-NO-TARGET-PERM",
            role=self.create_role("No Target Permission", {}),
        )
        no_permission_response = self.client.post(
            f"/api/v1/target-reports/{report_id}/approve",
            **self.auth_headers(no_permission),
        )
        self.assertEqual(no_permission_response.status_code, 403)

        valid_response = self.client.post(
            f"/api/v1/target-reports/{report_id}/approve",
            **self.auth_headers(self.approver),
        )
        self.assertEqual(valid_response.status_code, 200)

    def test_approval_revalidates_remaining_progress(self):
        target = self.create_target(self.employee)
        pending = EmployeeTargetReport.objects.create(
            employee_target=target,
            summary="Pending progress.",
            progress_value=Decimal("60.00"),
        )
        EmployeeTargetReport.objects.create(
            employee_target=target,
            summary="Previously approved progress.",
            progress_value=Decimal("50.00"),
            status=EmployeeTargetReport.Status.APPROVED,
            reviewed_by=self.approver.user,
            reviewed_at=timezone.now(),
        )

        response = self.client.post(
            f"/api/v1/target-reports/{pending.id}/approve",
            **self.auth_headers(self.approver),
        )
        self.assertEqual(response.status_code, 400)
        pending.refresh_from_db()
        self.assertEqual(pending.status, EmployeeTargetReport.Status.SUBMITTED)

    def test_report_lists_are_owner_and_branch_scoped(self):
        target = self.create_target(self.employee)
        report = self.submit_report(
            self.employee, target, "20.00", "Qualified leads."
        ).json()

        own_response = self.client.get(
            f"/api/v1/target-reports/me?employee_target_id={target.id}&status=submitted&search=leads",
            **self.auth_headers(self.employee),
        )
        self.assertEqual(own_response.status_code, 200)
        self.assertEqual(own_response.json()["count"], 1)

        branch_response = self.client.get(
            f"/api/v1/target-reports/?employee_user_id={self.employee.user_id}",
            **self.auth_headers(self.approver),
        )
        self.assertEqual(branch_response.status_code, 200)
        self.assertEqual(branch_response.json()["items"][0]["id"], report["id"])

        wrong_branch_role = self.create_role(
            "Abuja Target Viewer",
            {"target_reports": ["list"]},
        )
        wrong_branch_role.branches.add(self.abuja)
        wrong_branch_viewer = self.create_user_with_employee(
            email="abuja-target-viewer@example.com",
            username="abujatargetviewer",
            employee_id="EMP-ABUJA-TARGET-VIEWER",
            role=wrong_branch_role,
        )
        response = self.client.get(
            "/api/v1/target-reports/",
            **self.auth_headers(wrong_branch_viewer),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 0)
