from datetime import timedelta
from decimal import Decimal

from django.test import Client as DjangoClient
from django.test import TestCase
from django.utils import timezone

from finance.models import (
    FinanceAccount,
    FinanceVendor,
    PayrollRun,
    PettyCashAdvance,
    StatutoryObligation,
    VendorBill,
)
from services.models.expenses import Expense
from services.models.payment import Invoice, Payment
from services.models.service import (
    Service,
    ServiceCategory,
    ServiceOrder,
    ServiceRequest,
    ServiceRequestForm,
)
from user.models.branch import Branch
from user.models.client import Client as CustomerClient
from user.models.client_service import PaymentSubmission
from user.models.user import User
from user.tests.helpers import RoleAPITestMixin


class FinanceCommandCenterTests(RoleAPITestMixin, TestCase):
    def setUp(self):
        self.client = DjangoClient()
        self.role = self.create_role(
            "Finance Command Center Viewer",
            {
                "financial_reports": ["view"],
            },
        )
        self.employee = self.create_user_with_employee(
            "finance.cc@test.com",
            "financecc",
            "EMP-FIN-CC-001",
            role=self.role,
        )
        self.headers = self.auth_headers(self.employee)
        self.branch = Branch.objects.create(
            branch_name="Finance CC Enugu",
            branch_id="BR-FIN-CC-ENU",
            country="Nigeria",
            state="Enugu",
            office_address="Finance CC office",
            contact_email="finance-cc@test.com",
            contact_phone="+2348012222201",
        )
        self.role.branches.add(self.branch)
        self.customer = self._create_customer(
            "customer.command@test.com",
            "Command",
            "Client",
            "Command Client Ltd",
        )
        self.service = self._create_service("Estate Delivery")
        self.request_form = ServiceRequestForm.objects.create(
            service=self.service,
            name="Finance command center form",
            version=1,
            status="active",
            is_active=True,
            created_by=self.employee.user,
        )
        self.request = ServiceRequest.objects.create(
            client=self.customer,
            service=self.service,
            request_form=self.request_form,
            contact_name="Command Contact",
            contact_email=self.customer.user.email,
            status="quoted",
            branch=self.branch,
            created_by=self.employee.user,
        )
        self.order = ServiceOrder.objects.create(
            client=self.customer,
            service=self.service,
            service_request=self.request,
            description="Command center order",
            amount=Decimal("5000.00"),
            valid_until=timezone.localdate() + timedelta(days=15),
            due_date=timezone.localdate() + timedelta(days=20),
            created_by=self.employee.user,
            branch=self.branch,
            progress=45,
            stage="Execution",
        )
        self.finance_account = FinanceAccount.objects.create(
            display_name="Command Center Bank",
            account_number="0123456789",
            bank_name="Bomach Bank",
            account_name="Bomach Command Center",
            account_type=FinanceAccount.ACCOUNT_TYPE.BANK,
            currency="NGN",
            opening_balance=Decimal("1000.00"),
            is_active=True,
            branch=self.branch,
            created_by=self.employee.user,
        )
        self.cash_account = FinanceAccount.objects.create(
            display_name="Command Center Cash",
            account_type=FinanceAccount.ACCOUNT_TYPE.CASH,
            currency="NGN",
            opening_balance=Decimal("0.00"),
            is_active=True,
            branch=self.branch,
            created_by=self.employee.user,
        )
        self.vendor = FinanceVendor.objects.create(
            name="CC Vendor",
            default_category=FinanceVendor.CATEGORY.PROFESSIONAL_SERVICES,
            created_by=self.employee.user,
        )
        self.invoice = Invoice.objects.create(
            client=self.customer,
            service=self.service,
            service_request=self.request,
            order=self.order,
            subtotal=Decimal("5000.00"),
            tax_rate=Decimal("0.00"),
            amount_paid=Decimal("1000.00"),
            status="partially_paid",
            issue_date=timezone.localdate() - timedelta(days=5),
            due_date=timezone.localdate() - timedelta(days=2),
            created_by=self.employee.user,
        )
        Payment.objects.create(
            invoice=self.invoice,
            amount=Decimal("1000.00"),
            payment_date=timezone.localdate() - timedelta(days=1),
            payment_method="bank_transfer",
            finance_account=self.finance_account,
            transaction_reference="CC-PAY-001",
            proof_of_payment="https://example.com/command-center-payment.png",
            created_by=self.employee.user,
        )
        PaymentSubmission.objects.create(
            invoice=self.invoice,
            client=self.customer,
            amount=Decimal("1000.00"),
            payment_method="bank_transfer",
            payment_date=timezone.localdate(),
            proof_of_payment="https://example.com/proof.pdf",
            status=PaymentSubmission.STATUS.PENDING,
            submitted_by=self.employee.user,
            submitted_by_type=PaymentSubmission.SUBMITTED_BY_TYPE.STAFF,
        )
        Expense.objects.create(
            user=self.employee.user,
            branch=self.branch,
            finance_account=self.finance_account,
            service_order=self.order,
            date=timezone.localdate(),
            description="Field logistics",
            amount=Decimal("400.00"),
            vendor="Ops Vendor",
            beneficiary="Delivery team",
            stage="Execution",
            status=Expense.STATUS.PENDING,
        )
        Expense.objects.create(
            user=self.employee.user,
            branch=self.branch,
            finance_account=self.finance_account,
            service_order=self.order,
            date=timezone.localdate(),
            description="Approved payout",
            amount=Decimal("300.00"),
            vendor="Ops Vendor",
            beneficiary="Delivery team",
            stage="Execution",
            status=Expense.STATUS.PAID,
            paid_at=timezone.now(),
            paid_by=self.employee.user,
        )
        VendorBill.objects.create(
            vendor=self.vendor,
            branch=self.branch,
            finance_account=self.finance_account,
            category="Professional Services",
            description="Vendor approval queue",
            gross_amount=Decimal("600.00"),
            withholding_tax=Decimal("0.00"),
            bill_date=timezone.localdate() - timedelta(days=10),
            due_date=timezone.localdate() - timedelta(days=1),
            status=VendorBill.STATUS.AWAITING_APPROVAL,
            created_by=self.employee.user,
        )
        PettyCashAdvance.objects.create(
            requester=self.employee.user,
            branch=self.branch,
            finance_account=self.cash_account,
            service_order=self.order,
            purpose="Field transport",
            amount_requested=Decimal("150.00"),
            due_date=timezone.localdate() + timedelta(days=3),
            status=PettyCashAdvance.STATUS.REQUESTED,
        )
        PayrollRun.objects.create(
            period_month=timezone.localdate().month,
            period_year=timezone.localdate().year,
            scheduled_payment_date=timezone.localdate() + timedelta(days=4),
            branch=self.branch,
            finance_account=self.finance_account,
            status=PayrollRun.STATUS.AWAITING_APPROVAL,
            calculated_by=self.employee.user,
            created_by=self.employee.user,
        )
        StatutoryObligation.objects.create(
            obligation_type=StatutoryObligation.OBLIGATION_TYPE.VAT,
            source_type=StatutoryObligation.SOURCE_TYPE.MANUAL,
            branch=self.branch,
            period_label="Aug 2026",
            period_start=timezone.localdate().replace(day=1),
            period_end=timezone.localdate(),
            basis="VAT on service delivery",
            basis_amount=Decimal("5000.00"),
            amount=Decimal("375.00"),
            due_date=timezone.localdate() + timedelta(days=5),
            status=StatutoryObligation.STATUS.PENDING_APPROVAL,
            submitted_by=self.employee.user,
            created_by=self.employee.user,
        )

    def _create_customer(self, email, first_name, last_name, company_name=""):
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

    def _create_service(self, name):
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
            created_by=self.employee.user,
        )

    def test_command_center_returns_finance_overview_payload(self):
        response = self.client.get("/api/v1/finance/command-center", **self.headers)
        self.assertEqual(response.status_code, 200)
        body = response.json()

        self.assertEqual(body["currency"], "NGN")
        self.assertEqual(Decimal(body["kpis"]["money_received"]), Decimal("1000.00"))
        self.assertEqual(Decimal(body["kpis"]["money_spent"]), Decimal("300.00"))
        self.assertEqual(
            Decimal(body["kpis"]["net_cash_movement"]),
            Decimal("700.00"),
        )
        self.assertEqual(
            Decimal(body["kpis"]["outstanding_receivables"]),
            Decimal("4000.00"),
        )
        self.assertEqual(body["kpis"]["overdue_receivable_count"], 1)
        self.assertEqual(
            Decimal(body["kpis"]["cash_and_bank_position"]),
            Decimal("1700.00"),
        )

        approvals = {item["key"]: item["count"] for item in body["approvals"]}
        self.assertEqual(approvals["payment_submissions"], 1)
        self.assertEqual(approvals["expenses"], 1)
        self.assertEqual(approvals["vendor_bills"], 1)
        self.assertEqual(approvals["petty_cash"], 1)
        self.assertEqual(approvals["payroll"], 1)
        self.assertEqual(approvals["statutory"], 1)

        self.assertEqual(len(body["profitability_preview"]), 1)
        self.assertEqual(body["profitability_preview"][0]["order_number"], self.order.order_number)
        self.assertEqual(len(body["service_performance"]), 1)
        self.assertEqual(body["service_performance"][0]["service_name"], self.service.name)
        self.assertGreaterEqual(len(body["feature_availability"]), 2)

    def test_command_center_requires_financial_report_permission(self):
        employee = self.create_user_with_employee(
            "finance.cc.none@test.com",
            "financeccnone",
            "EMP-FIN-CC-002",
        )
        headers = self.auth_headers(employee)
        response = self.client.get("/api/v1/finance/command-center", **headers)
        self.assertEqual(response.status_code, 403)
