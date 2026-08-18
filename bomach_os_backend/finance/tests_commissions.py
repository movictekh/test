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
