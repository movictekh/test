from datetime import date
from decimal import Decimal

from django.test import Client as DjangoClient
from django.test import TestCase

from finance.models import FinanceAccount, PayrollLineItem, PayrollRun
from user.models.branch import Branch
from user.models.employee import Employee
from user.models.role import Role
from user.models.user import User
from user.tests.helpers import RoleAPITestMixin


class FinancePayrollAPITests(RoleAPITestMixin, TestCase):
    PERIOD_YEAR = 2026
    PERIOD_MONTH = 8

    def setUp(self):
        self.client = DjangoClient()
        self.role = self.create_role(
            "Finance Payroll Manager",
            {
                "finance_payroll": [
                    "list",
                    "view",
                    "create",
                    "update",
                    "calculate",
                    "submit",
                    "approve",
                    "reject",
                    "pay",
                    "cancel",
                ],
                "payments": ["list"],
                "cash_flow": ["view"],
            },
        )
        self.employee = self.create_user_with_employee(
            "payroll.manager@test.com",
            "payrollmanager",
            "EMP-PAY-MGR",
            role=self.role,
        )
        self.headers = self.auth_headers(self.employee)

        self.enugu = self._branch("Enugu", "BR-PAY-ENU")
        self.lagos = self._branch("Lagos", "BR-PAY-LAG")

        self.ada = self._salary_employee(
            email="ada.payroll@test.com",
            username="adapayroll",
            employee_id="EMP-PAY-001",
            first_name="Ada",
            last_name="Okafor",
            branch=self.enugu,
            gross_salary="500000.00",
            allowances={
                "housing": "100000.00",
                "transport": "50000.00",
            },
            bank_name="GTBank",
            account_number="0123456789",
        )
        self.chidi = self._salary_employee(
            email="chidi.payroll@test.com",
            username="chidipayroll",
            employee_id="EMP-PAY-002",
            first_name="Chidi",
            last_name="Eze",
            branch=self.lagos,
            gross_salary="400000.00",
            allowances={},
            bank_name="Access Bank",
            account_number="9876543210",
        )
        self.terminated = self._salary_employee(
            email="former.payroll@test.com",
            username="formerpayroll",
            employee_id="EMP-PAY-003",
            first_name="Former",
            last_name="Employee",
            branch=self.enugu,
            gross_salary="300000.00",
            allowances={},
            bank_name="GTBank",
            account_number="1111222233",
        )
        self.terminated.employment_status = "terminated"
        self.terminated.is_active = False
        self.terminated.save()

        self.account = FinanceAccount.objects.create(
            account_type=FinanceAccount.ACCOUNT_TYPE.BANK,
            display_name="Payroll Operating Account",
            bank_name="GTBank",
            account_number="0001112223",
            account_name="Bomach Group",
            opening_balance=Decimal("2000000.00"),
            opening_balance_date=date(2026, 8, 1),
            created_by=self.employee.user,
        )

    def _branch(self, name, branch_id):
        return Branch.objects.create(
            branch_name=name,
            branch_id=branch_id,
            country="Nigeria",
            state=name,
            office_address=f"{name} office",
            contact_email=f"{branch_id.lower()}@test.com",
            contact_phone="+2348010000001",
        )

    def _salary_employee(
        self,
        *,
        email,
        username,
        employee_id,
        first_name,
        last_name,
        branch,
        gross_salary,
        allowances,
        bank_name,
        account_number,
    ):
        user = User.objects.create_user(
            email=email,
            username=username,
            password="password123",
            first_name=first_name,
            last_name=last_name,
        )
        return Employee.objects.create(
            user=user,
            employee_id=employee_id,
            branch=branch,
            designation="Staff",
            gross_salary=Decimal(gross_salary),
            allowances=allowances,
            salary_frequency="monthly",
            employment_status="active",
            bank_name=bank_name,
            account_number=account_number,
            is_active=True,
        )

    def _create_run(self, **overrides):
        payload = {
            "period_month": self.PERIOD_MONTH,
            "period_year": self.PERIOD_YEAR,
            "scheduled_payment_date": "2026-08-31",
            "notes": "August company payroll",
        }
        payload.update(overrides)
        return self.client.post(
            "/api/v1/finance/payroll",
            data=payload,
            content_type="application/json",
            **self.headers,
        )

    def _post(self, path, payload=None, headers=None):
        return self.client.post(
            path,
            data=payload or {},
            content_type="application/json",
            **(headers or self.headers),
        )

    def test_calculate_creates_company_run_lines_and_structured_items(self):
        created = self._create_run()
        self.assertEqual(created.status_code, 201)
        run_id = created.json()["id"]

        response = self._post(
            f"/api/v1/finance/payroll/{run_id}/calculate"
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()

        self.assertEqual(body["run_number"], "PAYR-2608")
        self.assertEqual(body["status"], "calculated")
        self.assertEqual(body["employee_count"], 2)
        self.assertEqual(body["gross_pay"], "1050000.00")
        self.assertEqual(body["total_deductions"], "0.00")
        self.assertEqual(body["net_pay"], "1050000.00")
        self.assertEqual(len(body["lines"]), 2)

        ada_line = next(
            line for line in body["lines"]
            if line["employee_number"] == self.ada.employee_id
        )
        self.assertEqual(ada_line["gross_salary_snapshot"], "500000.00")
        self.assertEqual(ada_line["gross_pay"], "650000.00")
        self.assertEqual(ada_line["account_number_masked"], "******6789")
        self.assertFalse(ada_line["missing_bank_details"])

        employee_items = [
            item for item in ada_line["items"]
            if item["source_type"] == "employee"
        ]
        self.assertEqual(len(employee_items), 3)
        self.assertEqual(
            {item["category"] for item in employee_items},
            {"base_salary", "allowance"},
        )

        self.assertNotIn(
            self.terminated.employee_id,
            {line["employee_number"] for line in body["lines"]},
        )

        listed = self.client.get(
            "/api/v1/finance/payroll",
            {"period_year": 2026, "period_month": 8},
            **self.headers,
        )
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(listed.json()["count"], 1)
        self.assertEqual(listed.json()["items"][0]["run_number"], "PAYR-2608")
        self.assertEqual(listed.json()["items"][0]["net_pay"], "1050000.00")

    def test_manual_items_update_totals_and_survive_recalculation(self):
        run_id = self._create_run().json()["id"]
        calculated = self._post(
            f"/api/v1/finance/payroll/{run_id}/calculate"
        ).json()

        ada_line = next(
            line for line in calculated["lines"]
            if line["employee_number"] == self.ada.employee_id
        )

        adjusted = self.client.put(
            f"/api/v1/finance/payroll/{run_id}/lines/{ada_line['id']}/manual-items",
            data={
                "items": [
                    {
                        "item_type": "deduction",
                        "category": "loan",
                        "name": "Staff Loan Repayment",
                        "amount": "25000.00",
                        "notes": "August staff loan recovery",
                    }
                ]
            },
            content_type="application/json",
            **self.headers,
        )
        self.assertEqual(adjusted.status_code, 200)
        body = adjusted.json()
        self.assertEqual(body["total_deductions"], "25000.00")
        self.assertEqual(body["net_pay"], "1025000.00")

        self.ada.allowances = {
            "housing": "120000.00",
            "transport": "50000.00",
        }
        self.ada.save()

        recalculated = self._post(
            f"/api/v1/finance/payroll/{run_id}/calculate"
        )
        self.assertEqual(recalculated.status_code, 200)
        body = recalculated.json()

        self.assertEqual(body["gross_pay"], "1070000.00")
        self.assertEqual(body["total_deductions"], "25000.00")
        self.assertEqual(body["net_pay"], "1045000.00")

        ada_line = next(
            line for line in body["lines"]
            if line["employee_number"] == self.ada.employee_id
        )
        manual_items = [
            item for item in ada_line["items"]
            if item["source_type"] == "manual"
        ]
        self.assertEqual(len(manual_items), 1)
        self.assertEqual(manual_items[0]["category"], "loan")
        self.assertEqual(manual_items[0]["amount"], "25000.00")

    def test_submit_approve_pay_posts_single_payroll_cashbook_outflow(self):
        run_id = self._create_run().json()["id"]
        self._post(f"/api/v1/finance/payroll/{run_id}/calculate")

        submitted = self._post(
            f"/api/v1/finance/payroll/{run_id}/submit"
        )
        self.assertEqual(submitted.status_code, 200)
        self.assertEqual(submitted.json()["status"], "awaiting_approval")

        approved = self._post(
            f"/api/v1/finance/payroll/{run_id}/approve"
        )
        self.assertEqual(approved.status_code, 200)
        self.assertEqual(approved.json()["status"], "approved")

        paid = self._post(
            f"/api/v1/finance/payroll/{run_id}/pay",
            {
                "finance_account_id": self.account.id,
                "paid_at": "2026-08-31T10:00:00+01:00",
                "payment_reference": "GTB-PAYROLL-2608",
            },
        )
        self.assertEqual(paid.status_code, 200)
        self.assertEqual(paid.json()["status"], "paid")
        self.assertEqual(
            paid.json()["finance_account_id"],
            self.account.id,
        )

        cashbook = self.client.get(
            "/api/v1/finance/cashbook",
            {
                "date_from": "2026-08-31",
                "date_to": "2026-08-31",
                "source": "payroll",
            },
            **self.headers,
        )
        self.assertEqual(cashbook.status_code, 200)
        items = cashbook.json()["items"]
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["source"], "payroll")
        self.assertEqual(items[0]["money_in"], "0.00")
        self.assertEqual(items[0]["money_out"], "1050000.00")
        self.assertEqual(items[0]["reference"], "GTB-PAYROLL-2608")

        # Cash Flow opening cash reuses actual Cashbook sources, so a paid
        # payroll reduces the next opening cash without another integration.
        cash_flow = self.client.get(
            "/api/v1/finance/cash-flow/forecast",
            {"as_of": "2026-08-31", "weeks": 1},
            **self.headers,
        )
        self.assertEqual(cash_flow.status_code, 200)
        self.assertEqual(cash_flow.json()["opening_cash"], "950000.00")

    def test_finance_payroll_permission_is_separate_from_legacy_hr_payroll(self):
        legacy_role = Role.objects.create(
            name="Legacy Payroll Only",
            permissions={"payroll": ["list"]},
        )
        legacy_employee = self.create_user_with_employee(
            "legacy.payroll@test.com",
            "legacypayroll",
            "EMP-PAY-LEGACY",
            role=legacy_role,
        )

        response = self.client.get(
            "/api/v1/finance/payroll",
            **self.auth_headers(legacy_employee),
        )
        self.assertEqual(response.status_code, 403)

    def test_branch_run_calculates_only_branch_employees_and_scope_is_enforced(self):
        created = self._create_run(
            period_month=9,
            scheduled_payment_date="2026-09-30",
            branch_id=self.enugu.id,
        )
        self.assertEqual(created.status_code, 201)
        run_id = created.json()["id"]

        calculated = self._post(
            f"/api/v1/finance/payroll/{run_id}/calculate"
        )
        self.assertEqual(calculated.status_code, 200)
        body = calculated.json()
        self.assertEqual(body["employee_count"], 1)
        self.assertEqual(body["lines"][0]["employee_number"], self.ada.employee_id)

        branch_role = Role.objects.create(
            name="Enugu Payroll Viewer",
            permissions={"finance_payroll": ["list", "view"]},
        )
        branch_role.branches.add(self.enugu)
        branch_employee = self.create_user_with_employee(
            "enugu.payroll@test.com",
            "enugupayroll",
            "EMP-PAY-ENU",
            role=branch_role,
        )
        branch_headers = self.auth_headers(branch_employee)

        allowed = self.client.get(
            f"/api/v1/finance/payroll/{run_id}",
            **branch_headers,
        )
        self.assertEqual(allowed.status_code, 200)

        lagos_run = PayrollRun.objects.create(
            period_month=10,
            period_year=2026,
            scheduled_payment_date=date(2026, 10, 31),
            branch=self.lagos,
            created_by=self.employee.user,
        )
        denied = self.client.get(
            f"/api/v1/finance/payroll/{lagos_run.id}",
            **branch_headers,
        )
        self.assertEqual(denied.status_code, 404)

        company_run = PayrollRun.objects.create(
            period_month=11,
            period_year=2026,
            scheduled_payment_date=date(2026, 11, 30),
            created_by=self.employee.user,
        )
        company_denied = self.client.get(
            f"/api/v1/finance/payroll/{company_run.id}",
            **branch_headers,
        )
        self.assertEqual(company_denied.status_code, 404)

    def test_period_scope_conflict_and_workflow_guards(self):
        first = self._create_run(
            period_month=10,
            scheduled_payment_date="2026-10-31",
            branch_id=self.enugu.id,
        )
        self.assertEqual(first.status_code, 201)

        company_conflict = self._create_run(
            period_month=10,
            scheduled_payment_date="2026-10-31",
        )
        self.assertEqual(company_conflict.status_code, 400)

        run_id = first.json()["id"]

        premature_pay = self._post(
            f"/api/v1/finance/payroll/{run_id}/pay",
            {"finance_account_id": self.account.id},
        )
        self.assertEqual(premature_pay.status_code, 400)

        self._post(f"/api/v1/finance/payroll/{run_id}/calculate")
        self._post(f"/api/v1/finance/payroll/{run_id}/submit")

        rejected = self._post(
            f"/api/v1/finance/payroll/{run_id}/reject",
            {"reason": "Bank details require correction."},
        )
        self.assertEqual(rejected.status_code, 200)
        self.assertEqual(rejected.json()["status"], "rejected")

        run = PayrollRun.objects.get(id=run_id)
        self.assertEqual(run.lines.count(), 1)
        self.assertFalse(
            PayrollLineItem.objects.filter(
                payroll_line__payroll_run=run,
                source_type="manual",
            ).exists()
        )

        cancelled = self._post(
            f"/api/v1/finance/payroll/{run_id}/cancel",
            {"reason": "Superseded after payroll review."},
        )
        self.assertEqual(cancelled.status_code, 200)
        self.assertEqual(cancelled.json()["status"], "cancelled")
        self.assertEqual(
            cancelled.json()["cancellation_reason"],
            "Superseded after payroll review.",
        )

        replacement = self._create_run(
            period_month=10,
            scheduled_payment_date="2026-10-31",
            branch_id=self.enugu.id,
        )
        self.assertEqual(replacement.status_code, 201)
        self.assertIn("-R2", replacement.json()["run_number"])
