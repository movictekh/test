import json
from datetime import date, timedelta

from django.test import TestCase

from hr.api.v1.work_reports import _locked_work_report_queryset
from hr.models.work_report import DailyWorkReport
from user.models.branch import Branch
from user.tests.helpers import RoleAPITestMixin


class WorkReportAPITests(RoleAPITestMixin, TestCase):
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

    def setUp(self):
        self.lagos = self.create_branch("Lagos", "BR-WORK-LAGOS")
        self.abuja = self.create_branch("Abuja", "BR-WORK-ABUJA")
        self.report_day = date.today()

        self.employee_role = self.create_role(
            "Work Report Employee",
            {
                "work_reports": [
                    "create",
                    "view_own",
                    "list_own",
                    "update_own",
                    "approve",
                ]
            },
        )
        self.employee = self.create_user_with_employee(
            email="work-report-owner@example.com",
            username="workreportowner",
            employee_id="EMP-WORK-REPORT-OWNER",
            role=self.employee_role,
        )
        self.employee.branch = self.lagos
        self.employee.save(update_fields=["branch"])

        self.approver_role = self.create_role(
            "Work Report Approver",
            {"work_reports": ["list", "view", "approve", "reject", "delete"]},
        )
        self.approver_role.branches.add(self.lagos)
        self.approver = self.create_user_with_employee(
            email="work-report-approver@example.com",
            username="workreportapprover",
            employee_id="EMP-WORK-REPORT-APPROVER",
            role=self.approver_role,
        )
        self.approver.branch = self.lagos
        self.approver.save(update_fields=["branch"])

    def test_locked_queryset_locks_only_work_report_rows(self):
        queryset = _locked_work_report_queryset()

        self.assertTrue(queryset.query.select_for_update)
        self.assertEqual(queryset.query.select_for_update_of, ("self",))

    def create_report(self, employee=None, status="submitted", day=None):
        employee = employee or self.employee
        return DailyWorkReport.objects.create(
            employee=employee,
            day=day or self.report_day,
            hours_worked="8.0",
            work_activities="Completed assigned work.",
            status=status,
        )

    def test_employee_cannot_forge_decision_status(self):
        response = self.client.post(
            "/api/v1/work-reports/",
            data=json.dumps(
                {
                    "day": self.report_day.isoformat(),
                    "hours_worked": "8.0",
                    "work_activities": "Completed assigned work.",
                    "status": "approved",
                    "attachments": [],
                }
            ),
            content_type="application/json",
            **self.auth_headers(self.employee),
        )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(DailyWorkReport.objects.count(), 0)

        valid_response = self.client.post(
            "/api/v1/work-reports/",
            data=json.dumps(
                {
                    "day": self.report_day.isoformat(),
                    "hours_worked": "8.0",
                    "work_activities": "Completed assigned work.",
                    "status": "submitted",
                    "attachments": ["https://example.com/evidence.pdf"],
                }
            ),
            content_type="application/json",
            **self.auth_headers(self.employee),
        )
        self.assertEqual(valid_response.status_code, 201)
        self.assertEqual(valid_response.json()["status"], "submitted")
        self.assertEqual(
            valid_response.json()["attachments"][0]["file_url"],
            "https://example.com/evidence.pdf",
        )

    def test_update_own_cannot_modify_another_employee_report(self):
        owner_report = self.create_report(status="draft")
        other_employee = self.create_user_with_employee(
            email="other-work-report@example.com",
            username="otherworkreport",
            employee_id="EMP-OTHER-WORK-REPORT",
            role=self.employee_role,
        )
        other_employee.branch = self.lagos
        other_employee.save(update_fields=["branch"])

        attack_response = self.client.put(
            f"/api/v1/work-reports/{owner_report.id}",
            data=json.dumps({"work_activities": "Changed by another employee."}),
            content_type="application/json",
            **self.auth_headers(other_employee),
        )
        self.assertEqual(attack_response.status_code, 403)
        owner_report.refresh_from_db()
        self.assertEqual(owner_report.work_activities, "Completed assigned work.")

        submit_response = self.client.put(
            f"/api/v1/work-reports/{owner_report.id}",
            data=json.dumps(
                {
                    "work_activities": "Updated by the owner.",
                    "status": "submitted",
                }
            ),
            content_type="application/json",
            **self.auth_headers(self.employee),
        )
        self.assertEqual(submit_response.status_code, 200)

        submitted_update_response = self.client.put(
            f"/api/v1/work-reports/{owner_report.id}",
            data=json.dumps({"work_activities": "Edited after submission."}),
            content_type="application/json",
            **self.auth_headers(self.employee),
        )
        self.assertEqual(submitted_update_response.status_code, 200)
        self.assertEqual(submitted_update_response.json()["status"], "submitted")
        self.assertEqual(
            submitted_update_response.json()["work_activities"],
            "Edited after submission.",
        )

    def test_approve_records_reviewer_rating_and_blocks_self_approval(self):
        report = self.create_report()

        self_approval = self.client.post(
            f"/api/v1/work-reports/{report.id}/approve",
            data=json.dumps({"rating": 5}),
            content_type="application/json",
            **self.auth_headers(self.employee),
        )
        self.assertEqual(self_approval.status_code, 400)

        response = self.client.post(
            f"/api/v1/work-reports/{report.id}/approve",
            data=json.dumps({"rating": 5, "feedback": "Strong delivery."}),
            content_type="application/json",
            **self.auth_headers(self.approver),
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "approved")
        self.assertEqual(data["rating"], 5)
        self.assertEqual(data["reviewed_by"]["id"], self.approver.user_id)
        self.assertIsNotNone(data["reviewed_at"])

        employee_edit_response = self.client.put(
            f"/api/v1/work-reports/{report.id}",
            data=json.dumps({"work_activities": "Changed after approval."}),
            content_type="application/json",
            **self.auth_headers(self.employee),
        )
        self.assertEqual(employee_edit_response.status_code, 400)

        repeat_response = self.client.post(
            f"/api/v1/work-reports/{report.id}/approve",
            data=json.dumps({}),
            content_type="application/json",
            **self.auth_headers(self.approver),
        )
        self.assertEqual(repeat_response.status_code, 400)

    def test_rejection_requires_feedback_and_can_be_corrected_and_resubmitted(self):
        report = self.create_report()
        empty_response = self.client.post(
            f"/api/v1/work-reports/{report.id}/reject",
            data=json.dumps({"feedback": "  "}),
            content_type="application/json",
            **self.auth_headers(self.approver),
        )
        self.assertEqual(empty_response.status_code, 400)

        reject_response = self.client.post(
            f"/api/v1/work-reports/{report.id}/reject",
            data=json.dumps({"feedback": "Add supporting task details."}),
            content_type="application/json",
            **self.auth_headers(self.approver),
        )
        self.assertEqual(reject_response.status_code, 200)
        self.assertEqual(reject_response.json()["status"], "rejected")

        resubmit_response = self.client.put(
            f"/api/v1/work-reports/{report.id}",
            data=json.dumps(
                {
                    "task_details": "Added supporting task details.",
                    "status": "submitted",
                }
            ),
            content_type="application/json",
            **self.auth_headers(self.employee),
        )
        self.assertEqual(resubmit_response.status_code, 200)
        resubmitted = resubmit_response.json()
        self.assertEqual(resubmitted["status"], "submitted")
        self.assertIsNone(resubmitted["reviewed_by"])
        self.assertIsNone(resubmitted["reviewed_at"])
        self.assertIsNone(resubmitted["feedback"])

    def test_approval_and_visibility_are_branch_scoped(self):
        report = self.create_report()
        wrong_branch_role = self.create_role(
            "Abuja Work Report Approver",
            {"work_reports": ["list", "view", "approve"]},
        )
        wrong_branch_role.branches.add(self.abuja)
        wrong_branch_approver = self.create_user_with_employee(
            email="abuja-work-approver@example.com",
            username="abujaworkapprover",
            employee_id="EMP-ABUJA-WORK-APPROVER",
            role=wrong_branch_role,
        )
        wrong_branch_approver.branch = self.abuja
        wrong_branch_approver.save(update_fields=["branch"])

        list_response = self.client.get(
            "/api/v1/work-reports/",
            **self.auth_headers(wrong_branch_approver),
        )
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(list_response.json()["count"], 0)

        detail_response = self.client.get(
            f"/api/v1/work-reports/{report.id}",
            **self.auth_headers(wrong_branch_approver),
        )
        self.assertEqual(detail_response.status_code, 403)

        approval_response = self.client.post(
            f"/api/v1/work-reports/{report.id}/approve",
            data=json.dumps({}),
            content_type="application/json",
            **self.auth_headers(wrong_branch_approver),
        )
        self.assertEqual(approval_response.status_code, 403)

    def test_submitted_and_approved_reports_cannot_be_deleted(self):
        submitted = self.create_report()
        response = self.client.delete(
            f"/api/v1/work-reports/{submitted.id}",
            **self.auth_headers(self.approver),
        )
        self.assertEqual(response.status_code, 400)

        draft = self.create_report(
            status="draft",
            day=self.report_day + timedelta(days=1),
        )
        response = self.client.delete(
            f"/api/v1/work-reports/{draft.id}",
            **self.auth_headers(self.approver),
        )
        self.assertEqual(response.status_code, 200)
