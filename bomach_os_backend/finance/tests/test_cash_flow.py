from datetime import date
from decimal import Decimal

from django.test import Client as DjangoClient
from django.test import TestCase

from finance.models import (
    FinanceAccount,
    FinanceVendor,
    PayrollRun,
    StatutoryObligation,
    VendorBill,
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
from user.models.role import Role
from user.models.user import User
from user.tests.helpers import RoleAPITestMixin


class FinanceCashFlowForecastAPITests(RoleAPITestMixin, TestCase):
    AS_OF = date(2026, 8, 18)

    def setUp(self):
        self.client = DjangoClient()
        self.role = self.create_role(
            "Cash Flow Viewer",
            {"cash_flow": ["view"]},
        )
        self.employee = self.create_user_with_employee(
            "cashflow@test.com",
            "cashflow",
            "EMP-CF-001",
            role=self.role,
        )
        self.headers = self.auth_headers(self.employee)

        self.enugu = self._branch("Enugu", "BR-CF-ENU")
        self.customer = self._customer(
            "client.cf@test.com",
            "Forecast",
            "Client",
            "Forecast Client Ltd",
        )
        self.service = self._service("Cash Flow Test Service")
        self.request_form = ServiceRequestForm.objects.create(
            service=self.service,
            name="Cash flow request form",
            version=1,
            status="active",
            is_active=True,
            created_by=self.employee.user,
        )
        self.request = ServiceRequest.objects.create(
            client=self.customer,
            service=self.service,
            request_form=self.request_form,
            contact_name="Forecast Contact",
            contact_email=self.customer.user.email,
            status="quoted",
            branch=self.enugu,
            created_by=self.employee.user,
        )

        self.account = self._account(
            self.enugu,
            "Enugu Operating",
            "10000.00",
            date(2026, 8, 1),
        )

        paid_invoice = self._invoice(
            subtotal="2000.00",
            due_date=date(2026, 8, 10),
            status="sent",
        )
        Payment.objects.create(
            invoice=paid_invoice,
            amount=Decimal("2000.00"),
            payment_method="bank_transfer",
            payment_date=date(2026, 8, 10),
            transaction_reference="CF-ACTUAL-2000",
            finance_account=self.account,
            proof_of_payment="https://example.com/cf-actual.png",
            created_by=self.employee.user,
        )

        self.current_receivable = self._invoice(
            subtotal="3000.00",
            due_date=date(2026, 8, 20),
            status="sent",
        )
        self.overdue_receivable = self._invoice(
            subtotal="1000.00",
            due_date=date(2026, 8, 15),
            status="sent",
        )
        self.draft_invoice = self._invoice(
            subtotal="800.00",
            due_date=date(2026, 8, 19),
            status="draft",
        )

        self.vendor = FinanceVendor.objects.create(
            name="BuildMart Forecast",
            default_category=FinanceVendor.CATEGORY.MATERIALS,
            created_by=self.employee.user,
        )
        self.week_one_bill = self._bill(
            gross="1800.00",
            due_date=date(2026, 8, 21),
            status=VendorBill.STATUS.APPROVED,
            description="Week one materials",
        )
        self.week_two_bill = self._bill(
            gross="900.00",
            due_date=date(2026, 8, 28),
            status=VendorBill.STATUS.SCHEDULED,
            description="Week two supplier payment",
        )
        self.void_bill = self._bill(
            gross="700.00",
            due_date=date(2026, 8, 19),
            status=VendorBill.STATUS.VOID,
            description="Voided obligation",
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

    def _customer(self, email, first_name, last_name, company_name):
        user = User.objects.create_user(
            email=email,
            username=email.split("@")[0],
            password="password123",
            first_name=first_name,
            last_name=last_name,
        )
        return CustomerClient.objects.create(
            user=user,
            phone="+2348012345678",
            company_name=company_name,
        )

    def _service(self, name):
        category, _ = ServiceCategory.objects.get_or_create(
            name=ServiceCategory.CategoryChoices.CONSTRUCTION,
        )
        return Service.objects.create(
            name=name,
            category=category,
            description=f"{name} description",
            base_price=Decimal("100000.00"),
            delivery_time="2 weeks",
            status="active",
            created_by=self.employee.user,
        )

    def _account(self, branch, display_name, opening_balance, opening_balance_date):
        return FinanceAccount.objects.create(
            account_type=FinanceAccount.ACCOUNT_TYPE.BANK,
            display_name=display_name,
            branch=branch,
            bank_name="GTBank",
            account_number=f"CF-{branch.id}-{display_name[:4]}",
            account_name="Bomach Group",
            opening_balance=Decimal(opening_balance),
            opening_balance_date=opening_balance_date,
            created_by=self.employee.user,
        )

    def _invoice(
        self,
        subtotal,
        due_date,
        status,
        customer=None,
        service=None,
        service_request=None,
    ):
        customer = customer or self.customer
        service = service or self.service
        service_request = service_request or self.request
        amount = Decimal(subtotal)
        return Invoice.objects.create(
            client=customer,
            service=service,
            service_request=service_request,
            subtotal=amount,
            tax_rate=Decimal("0.00"),
            tax_amount=Decimal("0.00"),
            total_amount=amount,
            amount_paid=Decimal("0.00"),
            status=status,
            issue_date=date(2026, 8, 1),
            due_date=due_date,
            created_by=self.employee.user,
        )

    def _bill(self, gross, due_date, status, description, branch=None, vendor=None):
        return VendorBill.objects.create(
            vendor=vendor or self.vendor,
            branch=branch or self.enugu,
            category="Materials",
            description=description,
            gross_amount=Decimal(gross),
            withholding_tax=Decimal("0.00"),
            bill_date=date(2026, 8, 1),
            due_date=due_date,
            status=status,
            created_by=self.employee.user,
        )

    def _forecast(self, **params):
        query = {"as_of": self.AS_OF.isoformat()}
        query.update(params)
        return self.client.get(
            "/api/v1/finance/cash-flow/forecast",
            query,
            **self.headers,
        )

    def test_forecast_builds_screen_kpis_and_thirteen_week_liquidity(self):
        response = self._forecast()

        self.assertEqual(response.status_code, 200)
        body = response.json()

        self.assertEqual(body["horizon_weeks"], 13)
        self.assertEqual(len(body["weeks"]), 13)
        self.assertEqual(body["opening_cash"], "12000.00")
        self.assertEqual(body["expected_inflows_30d"], "4000.00")
        self.assertEqual(body["expected_outflows_30d"], "2700.00")
        self.assertEqual(body["forecast_closing_30d"], "13300.00")
        self.assertEqual(body["forecast_closing_horizon"], "13300.00")

        week_one = body["weeks"][0]
        self.assertEqual(week_one["opening_balance"], "12000.00")
        self.assertEqual(week_one["expected_inflows"], "4000.00")
        self.assertEqual(week_one["expected_outflows"], "1800.00")
        self.assertEqual(week_one["closing_balance"], "14200.00")

        week_two = body["weeks"][1]
        self.assertEqual(week_two["opening_balance"], "14200.00")
        self.assertEqual(week_two["expected_inflows"], "0.00")
        self.assertEqual(week_two["expected_outflows"], "900.00")
        self.assertEqual(week_two["closing_balance"], "13300.00")

        refs = {item["reference"] for item in body["upcoming_obligations"]}
        self.assertEqual(
            refs,
            {self.week_one_bill.bill_number, self.week_two_bill.bill_number},
        )

        item_refs = {item["reference"] for item in body["items"]}
        self.assertIn(self.current_receivable.invoice_number, item_refs)
        self.assertIn(self.overdue_receivable.invoice_number, item_refs)
        self.assertNotIn(self.draft_invoice.invoice_number, item_refs)
        self.assertNotIn(self.void_bill.bill_number, item_refs)

        overdue_item = next(
            item
            for item in body["items"]
            if item["reference"] == self.overdue_receivable.invoice_number
        )
        self.assertTrue(overdue_item["is_overdue"])
        self.assertEqual(overdue_item["due_date"], "2026-08-15")
        self.assertEqual(overdue_item["forecast_date"], "2026-08-18")

        self.overdue_receivable.refresh_from_db()
        self.assertEqual(self.overdue_receivable.status, "sent")

    def test_branch_scoped_user_only_forecasts_allowed_branch(self):
        lagos = self._branch("Lagos", "BR-CF-LAG")
        lagos_account = self._account(
            lagos,
            "Lagos Operating",
            "5000.00",
            date(2026, 8, 1),
        )
        lagos_customer = self._customer(
            "lagos.cf@test.com",
            "Lagos",
            "Client",
            "Lagos Client Ltd",
        )
        lagos_request = ServiceRequest.objects.create(
            client=lagos_customer,
            service=self.service,
            request_form=self.request_form,
            contact_name="Lagos Contact",
            contact_email=lagos_customer.user.email,
            status="quoted",
            branch=lagos,
            created_by=self.employee.user,
        )
        lagos_invoice = self._invoice(
            subtotal="6000.00",
            due_date=date(2026, 8, 22),
            status="sent",
            customer=lagos_customer,
            service_request=lagos_request,
        )
        lagos_vendor = FinanceVendor.objects.create(
            name="Lagos Supplier",
            default_category=FinanceVendor.CATEGORY.MATERIALS,
            created_by=self.employee.user,
        )
        lagos_bill = self._bill(
            gross="1000.00",
            due_date=date(2026, 8, 23),
            status=VendorBill.STATUS.APPROVED,
            description="Lagos obligation",
            branch=lagos,
            vendor=lagos_vendor,
        )

        self.role.branches.add(self.enugu)

        response = self._forecast()
        self.assertEqual(response.status_code, 200)
        body = response.json()

        self.assertEqual(body["opening_cash"], "12000.00")
        self.assertEqual(body["expected_inflows_30d"], "4000.00")
        self.assertEqual(body["expected_outflows_30d"], "2700.00")

        refs = {item["reference"] for item in body["items"]}
        self.assertNotIn(lagos_invoice.invoice_number, refs)
        self.assertNotIn(lagos_bill.bill_number, refs)
        self.assertEqual(lagos_account.opening_balance, Decimal("5000.00"))

    def test_explicit_branch_filter_matches_forecast_scope(self):
        response = self._forecast(branch_id=self.enugu.id)

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["opening_cash"], "12000.00")
        self.assertTrue(
            all(item["branch_id"] in {None, self.enugu.id} for item in body["items"])
        )

    def test_cash_flow_permission_is_required(self):
        denied_role = Role.objects.create(
            name="No Cash Flow Access",
            permissions={"payments": ["list"]},
        )
        denied_employee = self.create_user_with_employee(
            "no.cashflow@test.com",
            "nocashflow",
            "EMP-CF-DENY",
            role=denied_role,
        )

        response = self.client.get(
            "/api/v1/finance/cash-flow/forecast",
            {"as_of": self.AS_OF.isoformat()},
            **self.auth_headers(denied_employee),
        )
        self.assertEqual(response.status_code, 403)

    def test_weeks_parameter_is_bounded(self):
        response = self._forecast(weeks=2)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["weeks"]), 2)

        invalid = self._forecast(weeks=0)
        self.assertEqual(invalid.status_code, 400)

    def test_approved_payroll_and_statutory_obligations_join_forecast_without_double_counting_paid_items(
        self,
    ):
        payroll = PayrollRun.objects.create(
            period_month=8,
            period_year=2026,
            scheduled_payment_date=date(2026, 8, 25),
            branch=self.enugu,
            status=PayrollRun.STATUS.APPROVED,
            employee_count=2,
            gross_pay=Decimal("1600.00"),
            total_deductions=Decimal("100.00"),
            net_pay=Decimal("1500.00"),
            created_by=self.employee.user,
        )
        statutory = StatutoryObligation.objects.create(
            obligation_type=StatutoryObligation.OBLIGATION_TYPE.PAYE,
            source_type=StatutoryObligation.SOURCE_TYPE.PAYROLL,
            branch=self.enugu,
            period_label="August 2026",
            period_start=date(2026, 8, 1),
            period_end=date(2026, 8, 31),
            basis="Approved payroll PAYE",
            basis_amount=Decimal("1600.00"),
            amount=Decimal("200.00"),
            due_date=date(2026, 8, 30),
            status=StatutoryObligation.STATUS.APPROVED,
            created_by=self.employee.user,
        )

        paid_payroll = PayrollRun.objects.create(
            period_month=7,
            period_year=2026,
            scheduled_payment_date=date(2026, 8, 22),
            branch=self.enugu,
            finance_account=self.account,
            status=PayrollRun.STATUS.PAID,
            employee_count=1,
            gross_pay=Decimal("999.00"),
            total_deductions=Decimal("0.00"),
            net_pay=Decimal("999.00"),
            paid_by=self.employee.user,
            paid_at="2026-08-17T10:00:00+01:00",
            payment_reference="CF-PAID-PAYROLL",
            created_by=self.employee.user,
        )
        paid_statutory = StatutoryObligation.objects.create(
            obligation_type=StatutoryObligation.OBLIGATION_TYPE.WHT,
            source_type=StatutoryObligation.SOURCE_TYPE.VENDOR_BILL,
            branch=self.enugu,
            period_label="July 2026",
            period_start=date(2026, 7, 1),
            period_end=date(2026, 7, 31),
            basis="Already remitted WHT",
            basis_amount=Decimal("5000.00"),
            amount=Decimal("300.00"),
            due_date=date(2026, 8, 24),
            status=StatutoryObligation.STATUS.PAID,
            finance_account=self.account,
            paid_by=self.employee.user,
            paid_at="2026-08-17T11:00:00+01:00",
            payment_reference="CF-PAID-WHT",
            created_by=self.employee.user,
        )

        response = self._forecast()
        self.assertEqual(response.status_code, 200)
        body = response.json()

        # The paid July Payroll (999) and paid WHT (300) occurred on
        # 17 Aug, before AS_OF=18 Aug. They must therefore be reflected in
        # actual opening cash through Cashbook, while remaining excluded from
        # future forecast items.
        self.assertEqual(body["opening_cash"], "10701.00")
        self.assertEqual(body["expected_inflows_30d"], "4000.00")
        self.assertEqual(body["expected_outflows_30d"], "4400.00")
        self.assertEqual(body["forecast_closing_30d"], "10301.00")

        by_source = body["outflow_by_source_30d"]
        self.assertEqual(by_source["vendor_bill"], "2700.00")
        self.assertEqual(by_source["payroll"], "1500.00")
        self.assertEqual(by_source["statutory"], "200.00")

        refs = {item["reference"] for item in body["items"]}
        self.assertIn(payroll.run_number, refs)
        self.assertIn(statutory.obligation_number, refs)
        self.assertNotIn(paid_payroll.run_number, refs)
        self.assertNotIn(paid_statutory.obligation_number, refs)

        # Baseline opening cash was 12,000:
        # 12,000 - 999 paid Payroll - 300 paid statutory = 10,701.
        self.assertEqual(
            Decimal(body["opening_cash"]),
            Decimal("12000.00") - Decimal("999.00") - Decimal("300.00"),
        )

    def test_overdue_payroll_and_statutory_move_to_week_one_without_mutating_source_records(
        self,
    ):
        payroll = PayrollRun.objects.create(
            period_month=7,
            period_year=2026,
            scheduled_payment_date=date(2026, 8, 15),
            branch=self.enugu,
            status=PayrollRun.STATUS.APPROVED,
            employee_count=1,
            gross_pay=Decimal("800.00"),
            total_deductions=Decimal("0.00"),
            net_pay=Decimal("800.00"),
            created_by=self.employee.user,
        )
        statutory = StatutoryObligation.objects.create(
            obligation_type=StatutoryObligation.OBLIGATION_TYPE.OTHER,
            source_type=StatutoryObligation.SOURCE_TYPE.MANUAL,
            branch=self.enugu,
            period_label="July 2026",
            period_start=date(2026, 7, 1),
            period_end=date(2026, 7, 31),
            basis="Overdue filing obligation",
            basis_amount=Decimal("1000.00"),
            amount=Decimal("100.00"),
            due_date=date(2026, 8, 16),
            status=StatutoryObligation.STATUS.APPROVED,
            created_by=self.employee.user,
        )

        response = self._forecast(weeks=2)
        self.assertEqual(response.status_code, 200)
        body = response.json()

        payroll_item = next(
            item for item in body["items"] if item["reference"] == payroll.run_number
        )
        statutory_item = next(
            item
            for item in body["items"]
            if item["reference"] == statutory.obligation_number
        )
        self.assertTrue(payroll_item["is_overdue"])
        self.assertTrue(statutory_item["is_overdue"])
        self.assertEqual(payroll_item["forecast_date"], "2026-08-18")
        self.assertEqual(statutory_item["forecast_date"], "2026-08-18")

        payroll.refresh_from_db()
        statutory.refresh_from_db()
        self.assertEqual(payroll.status, PayrollRun.STATUS.APPROVED)
        self.assertEqual(statutory.status, StatutoryObligation.STATUS.APPROVED)

    def test_branch_scope_excludes_other_branch_people_compliance_outflows(self):
        lagos = self._branch("Lagos", "BR-CF-PC4-LAG")
        lagos_payroll = PayrollRun.objects.create(
            period_month=8,
            period_year=2026,
            scheduled_payment_date=date(2026, 8, 25),
            branch=lagos,
            status=PayrollRun.STATUS.APPROVED,
            employee_count=1,
            gross_pay=Decimal("700.00"),
            total_deductions=Decimal("0.00"),
            net_pay=Decimal("700.00"),
            created_by=self.employee.user,
        )
        lagos_statutory = StatutoryObligation.objects.create(
            obligation_type=StatutoryObligation.OBLIGATION_TYPE.OTHER,
            source_type=StatutoryObligation.SOURCE_TYPE.MANUAL,
            branch=lagos,
            period_label="August 2026",
            period_start=date(2026, 8, 1),
            period_end=date(2026, 8, 31),
            basis="Lagos statutory obligation",
            basis_amount=Decimal("500.00"),
            amount=Decimal("50.00"),
            due_date=date(2026, 8, 27),
            status=StatutoryObligation.STATUS.APPROVED,
            created_by=self.employee.user,
        )
        enugu_payroll = PayrollRun.objects.create(
            period_month=8,
            period_year=2026,
            scheduled_payment_date=date(2026, 8, 24),
            branch=self.enugu,
            status=PayrollRun.STATUS.APPROVED,
            employee_count=1,
            gross_pay=Decimal("600.00"),
            total_deductions=Decimal("0.00"),
            net_pay=Decimal("600.00"),
            created_by=self.employee.user,
        )

        self.role.branches.add(self.enugu)
        response = self._forecast()
        self.assertEqual(response.status_code, 200)
        refs = {item["reference"] for item in response.json()["items"]}

        self.assertIn(enugu_payroll.run_number, refs)
        self.assertNotIn(lagos_payroll.run_number, refs)
        self.assertNotIn(lagos_statutory.obligation_number, refs)
