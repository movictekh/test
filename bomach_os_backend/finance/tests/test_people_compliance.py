# ---- migrated from tests_payroll.py ----
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


# ---- migrated from tests_commissions.py ----
from datetime import date
from decimal import Decimal

from django.test import Client as DjangoClient
from django.test import TestCase

from finance.models import (
    CommissionRule,
    FinanceAccount,
    IncentiveAward,
)
from services.models.payment import Invoice, Payment
from services.models.service import (
    Service,
    ServiceCategory,
    ServiceRequest,
    ServiceRequestForm,
)
from user.models.branch import Branch
from user.models.client import Client as CustomerClient
from user.models.employee import Employee
from user.models.role import Role
from user.models.user import User
from user.tests.helpers import RoleAPITestMixin


class FinanceCommissionsAPITests(RoleAPITestMixin, TestCase):
    def setUp(self):
        self.client = DjangoClient()
        self.role = self.create_role(
            "Finance Incentive Manager",
            {
                "commissions": [
                    "list",
                    "view",
                    "create",
                    "update",
                    "calculate",
                    "approve",
                    "reject",
                ],
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
            },
        )
        self.manager = self.create_user_with_employee(
            "incentive.manager@test.com",
            "incentivemanager",
            "EMP-INC-MGR",
            role=self.role,
        )
        self.headers = self.auth_headers(self.manager)

        self.enugu = self._branch("Enugu", "BR-INC-ENU")
        self.lagos = self._branch("Lagos", "BR-INC-LAG")

        self.sales_employee = self._employee(
            "sales.employee@test.com",
            "salesemployee",
            "EMP-SALES-001",
            "Sales",
            "Officer",
            self.enugu,
            "300000.00",
        )
        self.lagos_employee = self._employee(
            "lagos.employee@test.com",
            "lagosemployee",
            "EMP-SALES-002",
            "Lagos",
            "Officer",
            self.lagos,
            "300000.00",
        )

        self.customer = self._customer(
            "commission.client@test.com",
            "Commission",
            "Client",
            "Commission Client Ltd",
        )
        self.service = self._service("Estate Plot Sales")
        self.other_service = self._service("Software Development")

        self.request_form = ServiceRequestForm.objects.create(
            service=self.service,
            name="Commission request form",
            version=1,
            status="active",
            is_active=True,
            created_by=self.manager.user,
        )
        self.request = ServiceRequest.objects.create(
            client=self.customer,
            service=self.service,
            request_form=self.request_form,
            contact_name="Commission Contact",
            contact_email=self.customer.user.email,
            status="quoted",
            branch=self.enugu,
            created_by=self.manager.user,
        )

        self.account = FinanceAccount.objects.create(
            account_type=FinanceAccount.ACCOUNT_TYPE.BANK,
            display_name="Enugu Collections",
            branch=self.enugu,
            bank_name="GTBank",
            account_number="0011223344",
            account_name="Bomach Group",
            opening_balance=Decimal("2000000.00"),
            opening_balance_date=date(2026, 8, 1),
            created_by=self.manager.user,
        )

        self.invoice = Invoice.objects.create(
            client=self.customer,
            service=self.service,
            service_request=self.request,
            subtotal=Decimal("4500000.00"),
            tax_rate=Decimal("0.00"),
            tax_amount=Decimal("0.00"),
            total_amount=Decimal("4500000.00"),
            amount_paid=Decimal("0.00"),
            status="sent",
            issue_date=date(2026, 8, 1),
            due_date=date(2026, 8, 15),
            created_by=self.manager.user,
        )
        self.payment = Payment.objects.create(
            invoice=self.invoice,
            amount=Decimal("4500000.00"),
            payment_method="bank_transfer",
            payment_date=date(2026, 8, 15),
            transaction_reference="INC-VERIFIED-001",
            finance_account=self.account,
            proof_of_payment="https://example.com/inc-proof.png",
            created_by=self.manager.user,
        )

        self.rule = CommissionRule.objects.create(
            name="Estate Sales 5 Percent",
            service=self.service,
            branch=self.enugu,
            rate_percent=Decimal("5.0000"),
            minimum_verified_revenue=Decimal("100000.00"),
            effective_from=date(2026, 1, 1),
            status=CommissionRule.STATUS.ACTIVE,
            created_by=self.manager.user,
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

    def _employee(
        self,
        email,
        username,
        employee_id,
        first_name,
        last_name,
        branch,
        salary,
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
            designation="Sales Officer",
            gross_salary=Decimal(salary),
            salary_frequency="monthly",
            employment_status="active",
            bank_name="GTBank",
            account_number="1234567890",
            is_active=True,
        )

    def _customer(self, email, first, last, company):
        user = User.objects.create_user(
            email=email,
            username=email.split("@")[0],
            password="password123",
            first_name=first,
            last_name=last,
        )
        return CustomerClient.objects.create(
            user=user,
            phone="+2348012345678",
            company_name=company,
        )

    def _service(self, name):
        category, _ = ServiceCategory.objects.get_or_create(
            name=ServiceCategory.CategoryChoices.CONSTRUCTION,
        )
        return Service.objects.create(
            name=name,
            category=category,
            description=f"{name} service",
            base_price=Decimal("100000.00"),
            delivery_time="2 weeks",
            status="active",
            created_by=self.manager.user,
        )

    def _post(self, path, payload=None):
        return self.client.post(
            path,
            data=payload or {},
            content_type="application/json",
            **self.headers,
        )

    def test_commission_uses_confirmed_payment_and_rule_snapshot(self):
        response = self._post(
            "/api/v1/finance/commissions/calculate",
            {
                "employee_id": self.sales_employee.id,
                "payment_id": self.payment.id,
                "commission_rule_id": self.rule.id,
                "payout_month": 8,
                "payout_year": 2026,
            },
        )
        self.assertEqual(response.status_code, 201)
        body = response.json()

        self.assertEqual(body["award_type"], "commission")
        self.assertEqual(body["status"], "pending_review")
        self.assertEqual(body["verified_revenue"], "4500000.00")
        self.assertEqual(body["rate_percent"], "5.0000")
        self.assertEqual(body["amount"], "225000.00")
        self.assertEqual(body["payment_reference"], self.payment.payment_reference)
        self.assertEqual(body["employee_number"], self.sales_employee.employee_id)
        self.assertEqual(body["branch_id"], self.enugu.id)

        duplicate = self._post(
            "/api/v1/finance/commissions/calculate",
            {
                "employee_id": self.sales_employee.id,
                "payment_id": self.payment.id,
                "commission_rule_id": self.rule.id,
                "payout_month": 8,
                "payout_year": 2026,
            },
        )
        self.assertEqual(duplicate.status_code, 400)
        self.assertEqual(IncentiveAward.objects.count(), 1)

    def test_bonus_is_manual_and_does_not_fake_verified_revenue(self):
        response = self._post(
            "/api/v1/finance/bonuses",
            {
                "employee_id": self.sales_employee.id,
                "amount": "75000.00",
                "payout_month": 8,
                "payout_year": 2026,
                "reason": "Exceptional project delivery",
            },
        )
        self.assertEqual(response.status_code, 201)
        body = response.json()

        self.assertEqual(body["award_type"], "bonus")
        self.assertEqual(body["verified_revenue"], "0.00")
        self.assertEqual(body["rate_percent"], "0.0000")
        self.assertEqual(body["amount"], "75000.00")
        self.assertEqual(body["reason"], "Exceptional project delivery")

    def test_approved_commission_and_bonus_are_picked_up_by_payroll(self):
        commission = self._post(
            "/api/v1/finance/commissions/calculate",
            {
                "employee_id": self.sales_employee.id,
                "payment_id": self.payment.id,
                "commission_rule_id": self.rule.id,
                "payout_month": 8,
                "payout_year": 2026,
            },
        ).json()
        bonus = self._post(
            "/api/v1/finance/bonuses",
            {
                "employee_id": self.sales_employee.id,
                "amount": "75000.00",
                "payout_month": 8,
                "payout_year": 2026,
                "reason": "Exceptional project delivery",
            },
        ).json()

        self._post(f"/api/v1/finance/commissions/{commission['id']}/approve")
        self._post(f"/api/v1/finance/commissions/{bonus['id']}/approve")

        payroll = self._post(
            "/api/v1/finance/payroll",
            {
                "period_month": 8,
                "period_year": 2026,
                "scheduled_payment_date": "2026-08-31",
            },
        )
        self.assertEqual(payroll.status_code, 201)
        run_id = payroll.json()["id"]

        calculated = self._post(
            f"/api/v1/finance/payroll/{run_id}/calculate"
        )
        self.assertEqual(calculated.status_code, 200)
        body = calculated.json()

        sales_line = next(
            line for line in body["lines"]
            if line["employee_number"] == self.sales_employee.employee_id
        )
        incentive_items = [
            item for item in sales_line["items"]
            if item["source_type"] == "commission"
        ]

        self.assertEqual(len(incentive_items), 2)
        self.assertEqual(
            {item["category"] for item in incentive_items},
            {"commission", "bonus"},
        )
        self.assertEqual(sales_line["gross_pay"], "600000.00")

        statuses = set(
            IncentiveAward.objects.filter(
                id__in=[commission["id"], bonus["id"]]
            ).values_list("status", flat=True)
        )
        self.assertEqual(statuses, {"included_in_payroll"})

    def test_payroll_payment_marks_incentives_paid_without_separate_cashbook_rows(self):
        commission = self._post(
            "/api/v1/finance/commissions/calculate",
            {
                "employee_id": self.sales_employee.id,
                "payment_id": self.payment.id,
                "commission_rule_id": self.rule.id,
                "payout_month": 9,
                "payout_year": 2026,
            },
        ).json()
        self._post(f"/api/v1/finance/commissions/{commission['id']}/approve")

        payroll = self._post(
            "/api/v1/finance/payroll",
            {
                "period_month": 9,
                "period_year": 2026,
                "scheduled_payment_date": "2026-09-30",
            },
        ).json()
        run_id = payroll["id"]

        self._post(f"/api/v1/finance/payroll/{run_id}/calculate")
        self._post(f"/api/v1/finance/payroll/{run_id}/submit")
        self._post(f"/api/v1/finance/payroll/{run_id}/approve")
        paid = self._post(
            f"/api/v1/finance/payroll/{run_id}/pay",
            {
                "finance_account_id": self.account.id,
                "paid_at": "2026-09-30T10:00:00+01:00",
                "payment_reference": "PAYROLL-INC-SEP",
            },
        )
        self.assertEqual(paid.status_code, 200)

        award = IncentiveAward.objects.get(id=commission["id"])
        self.assertEqual(award.status, IncentiveAward.STATUS.PAID)
        self.assertIsNotNone(award.paid_at)

        cashbook = self.client.get(
            "/api/v1/finance/cashbook",
            {
                "date_from": "2026-09-30",
                "date_to": "2026-09-30",
            },
            **self.headers,
        )
        self.assertEqual(cashbook.status_code, 200)
        rows = cashbook.json()["items"]
        payroll_rows = [row for row in rows if row["source"] == "payroll"]
        commission_rows = [row for row in rows if row["source"] == "commission"]

        self.assertEqual(len(payroll_rows), 1)
        self.assertEqual(commission_rows, [])

    def test_service_or_branch_mismatch_is_rejected(self):
        other_rule = CommissionRule.objects.create(
            name="Software Rule",
            service=self.other_service,
            rate_percent=Decimal("2.5000"),
            effective_from=date(2026, 1, 1),
            created_by=self.manager.user,
        )

        wrong_service = self._post(
            "/api/v1/finance/commissions/calculate",
            {
                "employee_id": self.sales_employee.id,
                "payment_id": self.payment.id,
                "commission_rule_id": other_rule.id,
                "payout_month": 8,
                "payout_year": 2026,
            },
        )
        self.assertEqual(wrong_service.status_code, 400)

        wrong_employee = self._post(
            "/api/v1/finance/commissions/calculate",
            {
                "employee_id": self.lagos_employee.id,
                "payment_id": self.payment.id,
                "commission_rule_id": self.rule.id,
                "payout_month": 8,
                "payout_year": 2026,
            },
        )
        self.assertEqual(wrong_employee.status_code, 400)

    def test_branch_scoping_hides_other_branch_incentives(self):
        bonus = IncentiveAward.objects.create(
            award_type=IncentiveAward.AWARD_TYPE.BONUS,
            employee=self.lagos_employee,
            branch=self.lagos,
            amount=Decimal("50000.00"),
            payout_month=8,
            payout_year=2026,
            reason="Lagos performance bonus",
            created_by=self.manager.user,
        )

        branch_role = Role.objects.create(
            name="Enugu Incentive Viewer",
            permissions={"commissions": ["list", "view"]},
        )
        branch_role.branches.add(self.enugu)
        branch_employee = self.create_user_with_employee(
            "enugu.incentive@test.com",
            "enuguincentive",
            "EMP-INC-ENU",
            role=branch_role,
        )
        headers = self.auth_headers(branch_employee)

        response = self.client.get(
            "/api/v1/finance/commissions",
            **headers,
        )
        self.assertEqual(response.status_code, 200)
        ids = {item["id"] for item in response.json()["items"]}
        self.assertNotIn(bonus.id, ids)

    def test_commissions_permission_is_required(self):
        denied_role = Role.objects.create(
            name="No Incentive Access",
            permissions={"finance_payroll": ["list"]},
        )
        denied_employee = self.create_user_with_employee(
            "no.incentive@test.com",
            "noincentive",
            "EMP-INC-DENY",
            role=denied_role,
        )

        response = self.client.get(
            "/api/v1/finance/commissions",
            **self.auth_headers(denied_employee),
        )
        self.assertEqual(response.status_code, 403)


# ---- migrated from tests_statutory.py ----
from datetime import date
from decimal import Decimal
from django.test import Client as DjangoClient, TestCase
from finance.models import FinanceAccount,FinanceVendor,StatutoryObligation,VendorBill
from user.models.branch import Branch
from user.models.role import Role
from user.tests.helpers import RoleAPITestMixin
class FinanceStatutoryAPITests(RoleAPITestMixin,TestCase):
    def setUp(self):
        self.client=DjangoClient(); self.role=self.create_role("Statutory Manager",{"statutory":["list","view","create","update","generate","submit","approve","reject","pay","void"],"finance_payroll":["list","view","create","update","calculate","submit","approve","reject","pay","cancel"],"payments":["list"]})
        self.employee=self.create_user_with_employee("stat.manager@test.com","statmanager","EMP-STAT-MGR",role=self.role); self.headers=self.auth_headers(self.employee)
        self.branch=Branch.objects.create(branch_name="Enugu",branch_id="BR-STAT-ENU",country="Nigeria",state="Enugu",office_address="Enugu office",contact_email="stat-enugu@test.com",contact_phone="+2348010000001")
        # Payroll calculation only includes active monthly employees with positive salary.
        # Give the statutory test manager a real payroll configuration so the PAYE
        # source-generation test exercises the actual Finance Payroll workflow.
        self.employee.branch=self.branch
        self.employee.gross_salary=Decimal("300000.00")
        self.employee.salary_frequency="monthly"
        self.employee.employment_status="active"
        self.employee.bank_name="GTBank"
        self.employee.account_number="1234567890"
        self.employee.is_active=True
        self.employee.save()
        self.account=FinanceAccount.objects.create(account_type="bank",display_name="Statutory Account",bank_name="GTBank",account_number="2222333344",account_name="Bomach Group",opening_balance=Decimal("2000000.00"),opening_balance_date=date(2026,8,1),branch=self.branch,created_by=self.employee.user)
        self.vendor=FinanceVendor.objects.create(name="BuildMart",default_category="materials",created_by=self.employee.user)
    def post(self,path,payload=None): return self.client.post(path,data=payload or {},content_type="application/json",**self.headers)
    def test_manual_vat_drives_summary(self):
        r=self.post("/api/v1/finance/statutory/obligations",{"obligation_type":"vat","period_label":"July 2026","period_start":"2026-07-01","period_end":"2026-07-31","basis":"Reviewed VAT return","basis_amount":"12000000.00","amount":"918750.00","due_date":"2026-08-21","branch_id":self.branch.id}); self.assertEqual(r.status_code,201)
        s=self.client.get("/api/v1/finance/statutory/summary",**self.headers); self.assertEqual(s.status_code,200); self.assertEqual(s.json()["vat_payable"],"918750.00")
    def test_wht_generation_and_cashbook_split(self):
        bill=VendorBill.objects.create(vendor=self.vendor,branch=self.branch,finance_account=self.account,category="Materials",description="Cement",gross_amount=Decimal("1000000.00"),withholding_tax=Decimal("50000.00"),bill_date=date(2026,8,1),due_date=date(2026,8,10),status="paid",paid_by=self.employee.user,paid_at="2026-08-10T10:00:00+01:00",payment_reference="VEN-NET-001",created_by=self.employee.user)
        g=self.post("/api/v1/finance/statutory/generate/wht",{"period_start":"2026-08-01","period_end":"2026-08-31","due_date":"2026-09-21","branch_id":self.branch.id,"period_label":"August 2026"}); self.assertEqual(g.status_code,201); self.assertEqual(g.json()["amount"],"50000.00")
        self.assertEqual(self.post("/api/v1/finance/statutory/generate/wht",{"period_start":"2026-08-01","period_end":"2026-08-31","due_date":"2026-09-21","branch_id":self.branch.id}).status_code,400)
        oid=g.json()["id"]; self.post(f"/api/v1/finance/statutory/obligations/{oid}/submit"); self.post(f"/api/v1/finance/statutory/obligations/{oid}/approve"); self.assertEqual(self.post(f"/api/v1/finance/statutory/obligations/{oid}/pay",{"finance_account_id":self.account.id,"paid_at":"2026-09-21T10:00:00+01:00","payment_reference":"WHT-REM-001"}).status_code,200)
        v=self.client.get("/api/v1/finance/cashbook",{"date_from":"2026-08-10","date_to":"2026-08-10","source":"vendor_bill"},**self.headers); self.assertEqual(v.json()["items"][0]["money_out"],"950000.00")
        st=self.client.get("/api/v1/finance/cashbook",{"date_from":"2026-09-21","date_to":"2026-09-21","source":"statutory"},**self.headers); self.assertEqual(st.json()["items"][0]["money_out"],"50000.00")
    def test_payroll_paye_uses_explicit_deduction(self):
        p=self.post("/api/v1/finance/payroll",{"period_month":8,"period_year":2026,"scheduled_payment_date":"2026-08-31","branch_id":self.branch.id}); self.assertEqual(p.status_code,201); rid=p.json()["id"]
        c=self.post(f"/api/v1/finance/payroll/{rid}/calculate")
        self.assertEqual(c.status_code,200)
        self.assertEqual(len(c.json()["lines"]),1)
        line=c.json()["lines"][0]
        a=self.client.put(f"/api/v1/finance/payroll/{rid}/lines/{line['id']}/manual-items",data={"items":[{"item_type":"deduction","category":"paye","name":"PAYE","amount":"25000.00"}]},content_type="application/json",**self.headers); self.assertEqual(a.status_code,200)
        self.post(f"/api/v1/finance/payroll/{rid}/submit"); self.post(f"/api/v1/finance/payroll/{rid}/approve")
        g=self.post("/api/v1/finance/statutory/generate/payroll",{"payroll_run_id":rid,"category":"paye","due_date":"2026-09-10"}); self.assertEqual(g.status_code,201); self.assertEqual(g.json()["amount"],"25000.00")
        self.assertEqual(self.post("/api/v1/finance/statutory/generate/payroll",{"payroll_run_id":rid,"category":"paye","due_date":"2026-09-10"}).status_code,400)
    def test_permission_is_separate(self):
        role=Role.objects.create(name="No Stat",permissions={"finance_payroll":["list"]}); emp=self.create_user_with_employee("nostat@test.com","nostat","EMP-NOSTAT",role=role)
        self.assertEqual(self.client.get("/api/v1/finance/statutory/obligations",**self.auth_headers(emp)).status_code,403)
    def test_paid_cannot_be_voided(self):
        o=StatutoryObligation.objects.create(obligation_type="other",source_type="manual",branch=self.branch,period_label="Aug 2026",period_start=date(2026,8,1),period_end=date(2026,8,31),basis="Filing",basis_amount=Decimal("100000.00"),amount=Decimal("10000.00"),due_date=date(2026,9,15),status="approved",created_by=self.employee.user)
        self.assertEqual(self.post(f"/api/v1/finance/statutory/obligations/{o.id}/pay",{"finance_account_id":self.account.id,"payment_reference":"STAT-001"}).status_code,200)
        self.assertEqual(self.post(f"/api/v1/finance/statutory/obligations/{o.id}/void").status_code,400)
