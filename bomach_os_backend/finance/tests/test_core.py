from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.test import Client as DjangoClient
from django.test import TestCase
from django.utils import timezone

from finance.models import (
    FinanceAccount,
    FinanceVendor,
    FinanceWallet,
    FinanceWalletEntry,
    PettyCashAdvance,
    PettyCashRetirementLine,
    VendorBill,
)
from services.models.expenses import Expense
from services.models.payment import Payment
from services.models.payment import Invoice
from services.models.service import (
    Service,
    ServiceCategory,
    ServiceOrder,
    ServiceRequest,
    ServiceRequestActivity,
    ServiceRequestForm,
)
from user.models.branch import Branch
from user.models.client import Client as CustomerClient
from user.models.estate_property_invoice import EstatePropertyInvoice
from user.models.role import Role
from user.models.user import User
from user.models.client_service import PaymentSubmission
from user.services.jwt_service import JWTService
from user.tests.helpers import RoleAPITestMixin


class FinanceInvoiceAPITests(RoleAPITestMixin, TestCase):
    def setUp(self):
        self.client = DjangoClient()
        self.role = self.create_role(
            "Finance Invoice Viewer",
            {
                "service_invoices": ["list", "update"],
                "payments": ["list", "create", "view"],
                "expenses": [
                    "list",
                    "create",
                    "view",
                    "update",
                    "delete",
                    "approve",
                    "reject",
                    "pay",
                ],
                "finance_vendors": ["list", "create", "view", "update", "deactivate"],
                "vendor_bills": [
                    "list",
                    "create",
                    "view",
                    "update",
                    "approve",
                    "reject",
                    "pay",
                    "void",
                ],
                "petty_cash": [
                    "list",
                    "create",
                    "view",
                    "update",
                    "approve",
                    "reject",
                    "issue",
                    "retire",
                    "cancel",
                ],
            },
        )
        self.employee = self.create_user_with_employee(
            "finance@test.com",
            "finance",
            "EMP-FIN-001",
            role=self.role,
        )
        self.headers = self.auth_headers(self.employee)

        self.enugu = Branch.objects.create(
            branch_name="Enugu",
            branch_id="BR-FIN-ENU",
            country="Nigeria",
            state="Enugu",
            office_address="Enugu office",
            contact_email="enugu-fin@test.com",
            contact_phone="+2348010000001",
        )
        self.lagos = Branch.objects.create(
            branch_name="Lagos",
            branch_id="BR-FIN-LAG",
            country="Nigeria",
            state="Lagos",
            office_address="Lagos office",
            contact_email="lagos-fin@test.com",
            contact_phone="+2348010000002",
        )

        self.customer = self._create_customer(
            "apex@test.com",
            "Apex",
            "Retail",
            company_name="Apex Retail Ltd",
        )
        self.other_customer = self._create_customer(
            "greenview@test.com",
            "Greenview",
            "Cooperative",
            company_name="Greenview Cooperative",
        )
        self.service = self._create_service("Software Development")
        self.other_service = self._create_service("Cadastral Survey")
        self.request_form = ServiceRequestForm.objects.create(
            service=self.service,
            name="Finance test form",
            version=1,
            status="active",
            is_active=True,
            created_by=self.employee.user,
        )
        self.other_request_form = ServiceRequestForm.objects.create(
            service=self.other_service,
            name="Survey finance test form",
            version=1,
            status="active",
            is_active=True,
            created_by=self.employee.user,
        )
        self.enugu_request = self._create_request(
            self.customer,
            self.service,
            self.request_form,
            self.enugu,
            "Apex finance contact",
        )
        self.lagos_request = self._create_request(
            self.other_customer,
            self.other_service,
            self.other_request_form,
            self.lagos,
            "Greenview finance contact",
        )
        self.lagos_order = ServiceOrder.objects.create(
            client=self.other_customer,
            service=self.other_service,
            service_request=self.lagos_request,
            description="Greenview survey",
            amount=Decimal("300000.00"),
            valid_until=timezone.localdate() + timedelta(days=30),
            due_date=timezone.localdate() + timedelta(days=30),
            created_by=self.employee.user,
            branch=self.lagos,
        )

        self.sent_invoice = self._create_invoice(
            client=self.customer,
            service=self.service,
            service_request=self.enugu_request,
            subtotal=Decimal("1000.00"),
            amount_paid=Decimal("250.00"),
            status="partially_paid",
            issue_date=timezone.localdate(),
            due_date=timezone.localdate() + timedelta(days=10),
        )
        self.overdue_invoice = self._create_invoice(
            client=self.other_customer,
            service=self.other_service,
            service_request=self.lagos_request,
            order=self.lagos_order,
            subtotal=Decimal("3000.00"),
            amount_paid=Decimal("1000.00"),
            status="sent",
            issue_date=timezone.localdate() - timedelta(days=20),
            due_date=timezone.localdate() - timedelta(days=3),
        )
        self.paid_invoice = self._create_invoice(
            client=self.customer,
            service=self.service,
            service_request=self.enugu_request,
            subtotal=Decimal("500.00"),
            amount_paid=Decimal("500.00"),
            status="paid",
            issue_date=timezone.localdate() - timedelta(days=5),
            due_date=timezone.localdate() - timedelta(days=1),
        )
        EstatePropertyInvoice.objects.create(
            client=self.customer.user,
            issue_date=timezone.localdate(),
            due_date=timezone.localdate() + timedelta(days=7),
            subtotal=Decimal("9000.00"),
            tax_rate=Decimal("0.00"),
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

    def _create_request(self, customer, service, request_form, branch, contact_name):
        return ServiceRequest.objects.create(
            client=customer,
            service=service,
            request_form=request_form,
            contact_name=contact_name,
            contact_email=customer.user.email,
            status="quoted",
            branch=branch,
            created_by=self.employee.user,
        )

    def _create_invoice(
        self,
        client,
        service,
        service_request,
        subtotal,
        amount_paid,
        status,
        issue_date,
        due_date,
        order=None,
    ):
        return Invoice.objects.create(
            client=client,
            service=service,
            service_request=service_request,
            order=order,
            subtotal=subtotal,
            tax_rate=Decimal("0.00"),
            tax_amount=Decimal("0.00"),
            total_amount=subtotal,
            amount_paid=amount_paid,
            status=status,
            issue_date=issue_date,
            due_date=due_date,
            created_by=self.employee.user,
        )

    def test_finance_invoice_list_returns_service_invoices_only(self):
        response = self.client.get("/api/v1/finance/invoices", **self.headers)

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["count"], 3)
        self.assertEqual(
            {item["id"] for item in body["items"]},
            {self.sent_invoice.id, self.overdue_invoice.id, self.paid_invoice.id},
        )
        overdue_row = next(
            item for item in body["items"] if item["id"] == self.overdue_invoice.id
        )
        self.assertEqual(overdue_row["status"], "sent")
        self.assertEqual(overdue_row["display_status"], "overdue")
        self.assertTrue(overdue_row["is_overdue"])
        self.assertTrue(overdue_row["can_record_payment"])

        self.overdue_invoice.refresh_from_db()
        self.assertEqual(self.overdue_invoice.status, "sent")

    def test_finance_invoice_filters_and_search(self):
        search_response = self.client.get(
            "/api/v1/finance/invoices",
            {"search": "Greenview"},
            **self.headers,
        )
        self.assertEqual(search_response.status_code, 200)
        self.assertEqual(search_response.json()["count"], 1)
        self.assertEqual(
            search_response.json()["items"][0]["id"], self.overdue_invoice.id
        )

        branch_response = self.client.get(
            "/api/v1/finance/invoices",
            {"branch_id": self.enugu.id},
            **self.headers,
        )
        self.assertEqual(branch_response.status_code, 200)
        self.assertEqual(branch_response.json()["count"], 2)

        overdue_response = self.client.get(
            "/api/v1/finance/invoices",
            {"status": "overdue"},
            **self.headers,
        )
        self.assertEqual(overdue_response.status_code, 200)
        self.assertEqual(overdue_response.json()["count"], 1)
        self.assertEqual(
            overdue_response.json()["items"][0]["id"], self.overdue_invoice.id
        )

        due_response = self.client.get(
            "/api/v1/finance/invoices",
            {
                "due_from": (timezone.localdate() + timedelta(days=1)).isoformat(),
                "due_to": (timezone.localdate() + timedelta(days=20)).isoformat(),
            },
            **self.headers,
        )
        self.assertEqual(due_response.status_code, 200)
        self.assertEqual(due_response.json()["count"], 1)
        self.assertEqual(due_response.json()["items"][0]["id"], self.sent_invoice.id)

    def test_finance_invoice_summary_uses_filtered_queryset(self):
        response = self.client.get("/api/v1/finance/invoices/summary", **self.headers)

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["invoice_count"], 3)
        self.assertEqual(body["total_invoiced"], "4500.00")
        self.assertEqual(body["total_paid"], "1750.00")
        self.assertEqual(body["outstanding_balance"], "2750.00")
        self.assertEqual(body["current_balance"], "750.00")
        self.assertEqual(body["overdue_balance"], "2000.00")
        self.assertEqual(body["overdue_count"], 1)
        self.assertEqual(body["status_counts"]["partially_paid"], 1)
        self.assertEqual(body["status_counts"]["overdue"], 1)
        self.assertEqual(body["status_counts"]["paid"], 1)

        filtered = self.client.get(
            "/api/v1/finance/invoices/summary",
            {"branch_id": self.enugu.id},
            **self.headers,
        )
        self.assertEqual(filtered.status_code, 200)
        self.assertEqual(filtered.json()["invoice_count"], 2)
        self.assertEqual(filtered.json()["outstanding_balance"], "750.00")

    def test_branch_scoped_finance_user_sees_only_allowed_branches(self):
        scoped_role = Role.objects.create(
            name="Enugu Finance Invoice Viewer",
            permissions={"service_invoices": ["list"]},
        )
        scoped_role.branches.add(self.enugu)
        scoped_employee = self.create_user_with_employee(
            "enugu.finance@test.com",
            "enugufinance",
            "EMP-FIN-ENU",
            role=scoped_role,
        )

        response = self.client.get(
            "/api/v1/finance/invoices",
            **self.auth_headers(scoped_employee),
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 2)
        self.assertEqual(
            {item["id"] for item in response.json()["items"]},
            {self.sent_invoice.id, self.paid_invoice.id},
        )

    def test_receivables_list_excludes_paid_draft_cancelled_and_derives_ageing(self):
        self._create_invoice(
            client=self.customer,
            service=self.service,
            service_request=self.enugu_request,
            subtotal=Decimal("800.00"),
            amount_paid=Decimal("0.00"),
            status="draft",
            issue_date=timezone.localdate(),
            due_date=timezone.localdate() + timedelta(days=7),
        )
        self._create_invoice(
            client=self.customer,
            service=self.service,
            service_request=self.enugu_request,
            subtotal=Decimal("900.00"),
            amount_paid=Decimal("0.00"),
            status="cancelled",
            issue_date=timezone.localdate(),
            due_date=timezone.localdate() + timedelta(days=7),
        )

        response = self.client.get("/api/v1/finance/receivables", **self.headers)

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["count"], 2)
        rows = {item["invoice_id"]: item for item in body["items"]}
        self.assertEqual(rows[self.sent_invoice.id]["balance"], "750.00")
        self.assertEqual(rows[self.sent_invoice.id]["ageing_bucket"], "current")
        self.assertEqual(rows[self.overdue_invoice.id]["balance"], "2000.00")
        self.assertEqual(rows[self.overdue_invoice.id]["ageing_bucket"], "1_30")
        self.assertEqual(rows[self.overdue_invoice.id]["display_status"], "overdue")

    def test_receivables_summary_totals_and_buckets(self):
        response = self.client.get(
            "/api/v1/finance/receivables/summary", **self.headers
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["receivable_count"], 2)
        self.assertEqual(body["total_receivables"], "2750.00")
        self.assertEqual(body["current"], "750.00")
        self.assertEqual(body["bucket_1_30"], "2000.00")
        self.assertEqual(body["overdue_total"], "2000.00")
        self.assertEqual(body["overdue_count"], 1)
        self.assertEqual(body["bucket_counts"]["current"], 1)
        self.assertEqual(body["bucket_counts"]["1_30"], 1)

    def test_branch_scoped_user_only_sees_allowed_receivables(self):
        scoped_role = Role.objects.create(
            name="Scoped Enugu Receivables",
            permissions={"service_invoices": ["list"]},
        )
        scoped_role.branches.add(self.enugu)
        scoped_employee = self.create_user_with_employee(
            "scoped.receivables@test.com",
            "scopedreceivables",
            "EMP-FIN-REC",
            role=scoped_role,
        )

        response = self.client.get(
            "/api/v1/finance/receivables",
            **self.auth_headers(scoped_employee),
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 1)
        self.assertEqual(
            response.json()["items"][0]["invoice_id"], self.sent_invoice.id
        )

    @patch("finance.api.v1.receivables.send_mail")
    def test_send_receivable_reminder_emails_logs_activity_and_does_not_mutate_invoice(
        self, send_mail_mock
    ):
        response = self.client.post(
            f"/api/v1/finance/receivables/{self.sent_invoice.id}/send-reminder",
            data={"message": "Please settle this balance."},
            content_type="application/json",
            **self.headers,
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["sent"])
        self.assertEqual(
            response.json()["recipient"],
            self.sent_invoice.service_request.contact_email,
        )
        send_mail_mock.assert_called_once()
        activity = ServiceRequestActivity.objects.get(id=response.json()["activity_id"])
        self.assertEqual(activity.activity_type, "email")
        self.assertIn("Receivables reminder", activity.note)

        self.sent_invoice.refresh_from_db()
        self.assertEqual(self.sent_invoice.amount_paid, Decimal("250.00"))
        self.assertEqual(self.sent_invoice.balance, Decimal("750.00"))
        self.assertEqual(self.sent_invoice.status, "partially_paid")

    def test_send_receivable_reminder_requires_client_email(self):
        no_email_user = User.objects.create_user(
            email="no-email-placeholder@test.com",
            username="noemailclient",
            password="password123",
        )
        User.objects.filter(id=no_email_user.id).update(email="")
        no_email_user.refresh_from_db()
        no_email_client = CustomerClient.objects.create(
            user=no_email_user,
            phone="+2348012345600",
            company_name="No Email Ltd",
        )
        service_request = ServiceRequest.objects.create(
            client=no_email_client,
            service=self.service,
            request_form=self.request_form,
            contact_name="No Email Contact",
            contact_email="",
            status="quoted",
            branch=self.enugu,
            created_by=self.employee.user,
        )
        invoice = self._create_invoice(
            client=no_email_client,
            service=self.service,
            service_request=service_request,
            subtotal=Decimal("500.00"),
            amount_paid=Decimal("0.00"),
            status="sent",
            issue_date=timezone.localdate(),
            due_date=timezone.localdate() + timedelta(days=7),
        )

        response = self.client.post(
            f"/api/v1/finance/receivables/{invoice.id}/send-reminder",
            data={},
            content_type="application/json",
            **self.headers,
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "Client email is not available.")

    def test_finance_account_crud_and_deactivation(self):
        create_response = self.client.post(
            "/api/v1/finance/accounts",
            data={
                "account_type": "bank",
                "display_name": "GTBank Operating",
                "currency": "NGN",
                "branch_id": self.enugu.id,
                "bank_name": "GTBank",
                "account_number": "0123456789",
                "account_name": "Bomach Group",
            },
            content_type="application/json",
            **self.headers,
        )
        self.assertEqual(create_response.status_code, 201)
        account_id = create_response.json()["id"]
        self.assertEqual(create_response.json()["opening_balance"], "0.00")

        list_response = self.client.get("/api/v1/finance/accounts", **self.headers)
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(list_response.json()["count"], 1)

        update_response = self.client.patch(
            f"/api/v1/finance/accounts/{account_id}",
            data={
                "display_name": "GTBank Main Operating",
                "opening_balance": "2500.00",
                "opening_balance_date": timezone.localdate().isoformat(),
            },
            content_type="application/json",
            **self.headers,
        )
        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(
            update_response.json()["display_name"], "GTBank Main Operating"
        )
        self.assertEqual(update_response.json()["opening_balance"], "2500.00")

        deactivate_response = self.client.post(
            f"/api/v1/finance/accounts/{account_id}/deactivate",
            **self.headers,
        )
        self.assertEqual(deactivate_response.status_code, 200)
        self.assertFalse(deactivate_response.json()["is_active"])

        active_list = self.client.get("/api/v1/finance/accounts", **self.headers)
        self.assertEqual(active_list.status_code, 200)
        self.assertEqual(active_list.json()["count"], 0)

    def test_client_submission_does_not_change_balance_until_approved(self):
        invoice = self._create_invoice(
            client=self.customer,
            service=self.service,
            service_request=self.enugu_request,
            subtotal=Decimal("1000.00"),
            amount_paid=Decimal("0.00"),
            status="sent",
            issue_date=timezone.localdate(),
            due_date=timezone.localdate() + timedelta(days=14),
        )
        client_headers = self._client_auth_headers(self.customer.user)

        response = self.client.post(
            f"/api/v1/service-requests/invoices/{invoice.id}/payment-submissions",
            data={
                "invoice_id": invoice.id,
                "amount": "300.00",
                "payment_method": "bank_transfer",
                "payment_date": timezone.localdate().isoformat(),
                "transaction_reference": "CLIENT-TXN-001",
                "receiving_account_text": "GTBank 0123456789",
                "proof_of_payment": "https://example.com/client-proof.png",
                "notes": "Client transfer",
            },
            content_type="application/json",
            **client_headers,
        )

        self.assertEqual(response.status_code, 201)
        invoice.refresh_from_db()
        self.assertEqual(invoice.amount_paid, Decimal("0.00"))
        self.assertEqual(invoice.balance, Decimal("1000.00"))
        submission = PaymentSubmission.objects.get(id=response.json()["id"])
        self.assertEqual(submission.submitted_by, self.customer.user)
        self.assertEqual(
            submission.submitted_by_type, PaymentSubmission.SUBMITTED_BY_TYPE.CLIENT
        )
        self.assertEqual(submission.receiving_account_text, "GTBank 0123456789")
        self.assertIsNone(submission.finance_account_id)

    def test_staff_submission_requires_account_and_approval_updates_balance(self):
        invoice = self._create_invoice(
            client=self.customer,
            service=self.service,
            service_request=self.enugu_request,
            subtotal=Decimal("1000.00"),
            amount_paid=Decimal("0.00"),
            status="sent",
            issue_date=timezone.localdate(),
            due_date=timezone.localdate() + timedelta(days=14),
        )
        account = self._create_account(self.enugu)

        submit_response = self.client.post(
            "/api/v1/finance/payments/submissions",
            data={
                "invoice_id": invoice.id,
                "finance_account_id": account.id,
                "amount": "400.00",
                "payment_method": "bank_transfer",
                "payment_date": timezone.localdate().isoformat(),
                "transaction_reference": "STAFF-TXN-001",
                "proof_of_payment": "https://example.com/staff-proof.png",
                "notes": "Recorded by AR",
            },
            content_type="application/json",
            **self.headers,
        )

        self.assertEqual(submit_response.status_code, 201)
        invoice.refresh_from_db()
        self.assertEqual(invoice.amount_paid, Decimal("0.00"))
        self.assertEqual(invoice.balance, Decimal("1000.00"))

        submission_id = submit_response.json()["id"]
        approve_response = self.client.post(
            f"/api/v1/finance/payments/submissions/{submission_id}/review",
            data={"status": "confirmed"},
            content_type="application/json",
            **self.headers,
        )

        self.assertEqual(approve_response.status_code, 200)
        invoice.refresh_from_db()
        self.assertEqual(invoice.amount_paid, Decimal("400.00"))
        self.assertEqual(invoice.balance, Decimal("600.00"))
        payment = Payment.objects.get(invoice=invoice)
        self.assertEqual(payment.finance_account, account)
        self.assertEqual(
            payment.proof_of_payment, "https://example.com/staff-proof.png"
        )
        self.assertEqual(payment.transaction_reference, "STAFF-TXN-001")
        self.assertEqual(approve_response.json()["confirmed_payment_id"], payment.id)
        self.assertFalse(FinanceWalletEntry.objects.filter(payment=payment).exists())

    def test_wallet_balances_use_posted_entries_only(self):
        wallet = FinanceWallet.objects.create(
            client=self.customer,
            wallet_type=FinanceWallet.WALLET_TYPE.CLIENT,
            name="Apex Client Wallet",
            purpose="General client funds",
            created_by=self.employee.user,
        )
        FinanceWalletEntry.objects.create(
            wallet=wallet,
            entry_type=FinanceWalletEntry.ENTRY_TYPE.FUNDING,
            amount=Decimal("1000.00"),
            description="Opening funding",
            created_by=self.employee.user,
        )
        FinanceWalletEntry.objects.create(
            wallet=wallet,
            entry_type=FinanceWalletEntry.ENTRY_TYPE.SPEND,
            amount=Decimal("250.00"),
            description="Project spend",
            created_by=self.employee.user,
        )
        FinanceWalletEntry.objects.create(
            wallet=wallet,
            entry_type=FinanceWalletEntry.ENTRY_TYPE.COMMITMENT,
            amount=Decimal("400.00"),
            description="Vendor commitment",
            created_by=self.employee.user,
        )
        FinanceWalletEntry.objects.create(
            wallet=wallet,
            entry_type=FinanceWalletEntry.ENTRY_TYPE.COMMITMENT_RELEASE,
            amount=Decimal("100.00"),
            description="Released commitment",
            created_by=self.employee.user,
        )
        FinanceWalletEntry.objects.create(
            wallet=wallet,
            entry_type=FinanceWalletEntry.ENTRY_TYPE.SPEND,
            status=FinanceWalletEntry.STATUS.PENDING,
            amount=Decimal("900.00"),
            description="Pending spend",
            created_by=self.employee.user,
        )
        FinanceWalletEntry.objects.create(
            wallet=wallet,
            entry_type=FinanceWalletEntry.ENTRY_TYPE.SPEND,
            status=FinanceWalletEntry.STATUS.VOID,
            amount=Decimal("900.00"),
            description="Voided spend",
            created_by=self.employee.user,
        )

        summary = wallet.balance_summary()

        self.assertEqual(summary["funded"], Decimal("1000.00"))
        self.assertEqual(summary["spent"], Decimal("250.00"))
        self.assertEqual(summary["committed"], Decimal("300.00"))
        self.assertEqual(summary["available"], Decimal("450.00"))

    def test_wallet_api_create_list_entry_and_void(self):
        create_response = self.client.post(
            "/api/v1/finance/wallets",
            data={
                "client_id": self.other_customer.id,
                "service_order_id": self.lagos_order.id,
                "wallet_type": "project",
                "name": "Greenview Survey Wallet",
                "purpose": "Survey project funds",
            },
            content_type="application/json",
            **self.headers,
        )
        self.assertEqual(create_response.status_code, 201)
        wallet_id = create_response.json()["id"]
        self.assertEqual(create_response.json()["funded"], "0.00")
        self.assertEqual(create_response.json()["available"], "0.00")

        entry_response = self.client.post(
            f"/api/v1/finance/wallets/{wallet_id}/entries",
            data={
                "entry_type": "funding",
                "amount": "1500.00",
                "description": "Manual opening funding",
                "reference": "OPENING-FUNDING",
            },
            content_type="application/json",
            **self.headers,
        )
        self.assertEqual(entry_response.status_code, 201)

        spend_response = self.client.post(
            f"/api/v1/finance/wallets/{wallet_id}/entries",
            data={
                "entry_type": "spend",
                "amount": "200.00",
                "description": "Site transport",
            },
            content_type="application/json",
            **self.headers,
        )
        self.assertEqual(spend_response.status_code, 201)

        list_response = self.client.get("/api/v1/finance/wallets", **self.headers)
        self.assertEqual(list_response.status_code, 200)
        row = next(
            item for item in list_response.json()["items"] if item["id"] == wallet_id
        )
        self.assertEqual(row["funded"], "1500.00")
        self.assertEqual(row["spent"], "200.00")
        self.assertEqual(row["available"], "1300.00")

        void_response = self.client.post(
            f"/api/v1/finance/wallets/{wallet_id}/entries/{spend_response.json()['id']}/void",
            **self.headers,
        )
        self.assertEqual(void_response.status_code, 200)
        self.assertEqual(void_response.json()["status"], "void")

        detail_response = self.client.get(
            f"/api/v1/finance/wallets/{wallet_id}", **self.headers
        )
        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(detail_response.json()["spent"], "0.00")
        self.assertEqual(detail_response.json()["available"], "1500.00")

    def test_project_wallet_requires_service_order(self):
        response = self.client.post(
            "/api/v1/finance/wallets",
            data={
                "client_id": self.customer.id,
                "wallet_type": "project",
                "name": "Missing Order Wallet",
            },
            content_type="application/json",
            **self.headers,
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("service_order", response.json()["detail"])

    def test_finance_expense_crud_and_filters(self):
        account = self._create_account(self.lagos)

        create_response = self.client.post(
            "/api/v1/finance/expenses",
            data={
                "user_id": self.employee.user.id,
                "branch_id": self.lagos.id,
                "finance_account_id": account.id,
                "service_order_id": self.lagos_order.id,
                "date": timezone.localdate().isoformat(),
                "description": "Survey field logistics",
                "amount": "285000.00",
                "vendor": "Field Team",
                "beneficiary": "Survey Field Team",
                "category": "travel",
                "cost_type": "direct_cost",
                "stage": "Fieldwork",
                "billable": True,
                "client_visible": True,
                "attachment": "https://example.com/expense-proof.png",
            },
            content_type="application/json",
            **self.headers,
        )

        self.assertEqual(create_response.status_code, 201)
        expense_id = create_response.json()["id"]
        self.assertTrue(create_response.json()["expense_number"].startswith("EXP-"))
        self.assertEqual(
            create_response.json()["service_order_id"], self.lagos_order.id
        )
        self.assertEqual(
            create_response.json()["project_name"], self.lagos_order.description
        )
        self.assertEqual(create_response.json()["cost_type"], "direct_cost")

        filter_response = self.client.get(
            "/api/v1/finance/expenses",
            {
                "service_order_id": self.lagos_order.id,
                "cost_type": "direct_cost",
                "search": "field",
            },
            **self.headers,
        )
        self.assertEqual(filter_response.status_code, 200)
        self.assertEqual(filter_response.json()["count"], 1)
        self.assertEqual(filter_response.json()["items"][0]["id"], expense_id)

        patch_response = self.client.patch(
            f"/api/v1/finance/expenses/{expense_id}",
            data={"status": "paid", "paid_at": timezone.now().isoformat()},
            content_type="application/json",
            **self.headers,
        )
        self.assertEqual(patch_response.status_code, 400)
        self.assertIn("approve, reject, or pay", patch_response.json()["detail"])

        detail_response = self.client.get(
            f"/api/v1/finance/expenses/{expense_id}", **self.headers
        )
        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(detail_response.json()["finance_account_id"], account.id)
        self.assertEqual(detail_response.json()["status"], Expense.STATUS.PENDING)

    def test_finance_expense_approve_and_pay_posts_wallet_movements(self):
        requester = self.create_user_with_employee(
            "expense.requester@test.com",
            "expenserequester",
            "EMP-EXP-REQ",
        )
        account = self._create_account(self.lagos)
        wallet = FinanceWallet.objects.create(
            client=self.lagos_order.client,
            service_order=self.lagos_order,
            wallet_type=FinanceWallet.WALLET_TYPE.PROJECT,
            name="Greenview Expense Wallet",
            purpose="Expense workflow test",
            created_by=self.employee.user,
        )
        create_response = self.client.post(
            "/api/v1/finance/expenses",
            data={
                "user_id": requester.user.id,
                "branch_id": self.lagos.id,
                "service_order_id": self.lagos_order.id,
                "date": timezone.localdate().isoformat(),
                "description": "Approved field logistics",
                "amount": "285000.00",
                "category": "travel",
                "cost_type": "direct_cost",
                "beneficiary": "Survey Field Team",
            },
            content_type="application/json",
            **self.headers,
        )
        self.assertEqual(create_response.status_code, 201)
        expense_id = create_response.json()["id"]

        approve_response = self.client.post(
            f"/api/v1/finance/expenses/{expense_id}/approve",
            data={},
            content_type="application/json",
            **self.headers,
        )
        self.assertEqual(approve_response.status_code, 200)
        self.assertEqual(approve_response.json()["status"], Expense.STATUS.APPROVED)
        self.assertEqual(
            approve_response.json()["approved_by_id"], self.employee.user.id
        )

        commitment = FinanceWalletEntry.objects.get(
            expense_id=expense_id,
            entry_type=FinanceWalletEntry.ENTRY_TYPE.COMMITMENT,
        )
        self.assertEqual(commitment.wallet, wallet)
        self.assertEqual(commitment.amount, Decimal("285000.00"))
        self.assertEqual(wallet.balance_summary()["committed"], Decimal("285000.00"))

        approved_patch = self.client.patch(
            f"/api/v1/finance/expenses/{expense_id}",
            data={"description": "Changed after approval"},
            content_type="application/json",
            **self.headers,
        )
        self.assertEqual(approved_patch.status_code, 400)

        pay_response = self.client.post(
            f"/api/v1/finance/expenses/{expense_id}/pay",
            data={
                "finance_account_id": account.id,
                "payment_reference": "EXP-PAY-001",
            },
            content_type="application/json",
            **self.headers,
        )
        self.assertEqual(pay_response.status_code, 200)
        self.assertEqual(pay_response.json()["status"], Expense.STATUS.PAID)
        self.assertEqual(pay_response.json()["paid_by_id"], self.employee.user.id)
        self.assertEqual(pay_response.json()["finance_account_id"], account.id)
        self.assertEqual(pay_response.json()["payment_reference"], "EXP-PAY-001")

        release = FinanceWalletEntry.objects.get(
            expense_id=expense_id,
            entry_type=FinanceWalletEntry.ENTRY_TYPE.COMMITMENT_RELEASE,
        )
        spend = FinanceWalletEntry.objects.get(
            expense_id=expense_id,
            entry_type=FinanceWalletEntry.ENTRY_TYPE.SPEND,
        )
        self.assertEqual(release.amount, Decimal("285000.00"))
        self.assertEqual(spend.amount, Decimal("285000.00"))
        wallet = FinanceWallet.objects.get(id=wallet.id)
        self.assertEqual(wallet.balance_summary()["committed"], Decimal("0.00"))
        self.assertEqual(wallet.balance_summary()["spent"], Decimal("285000.00"))

        duplicate_pay = self.client.post(
            f"/api/v1/finance/expenses/{expense_id}/pay",
            data={"finance_account_id": account.id},
            content_type="application/json",
            **self.headers,
        )
        self.assertEqual(duplicate_pay.status_code, 400)
        self.assertEqual(
            FinanceWalletEntry.objects.filter(expense_id=expense_id).count(), 3
        )

    def test_finance_expense_reject_records_reason(self):
        requester = self.create_user_with_employee(
            "expense.rejecter@test.com",
            "expenserejecter",
            "EMP-EXP-REJ",
        )
        expense = Expense.objects.create(
            user=requester.user,
            branch=self.lagos,
            service_order=self.lagos_order,
            date=timezone.localdate(),
            description="Rejected field logistics",
            amount=Decimal("50000.00"),
            category=Expense.CATEGORY_CHOICES.TRAVEL,
            cost_type=Expense.COST_TYPE.DIRECT_COST,
            beneficiary="Survey Field Team",
        )

        response = self.client.post(
            f"/api/v1/finance/expenses/{expense.id}/reject",
            data={"rejection_reason": "Receipt is unclear"},
            content_type="application/json",
            **self.headers,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], Expense.STATUS.REJECTED)
        self.assertEqual(response.json()["rejected_by_id"], self.employee.user.id)
        self.assertEqual(response.json()["rejection_reason"], "Receipt is unclear")

    def test_finance_vendor_crud_and_deactivation(self):
        create_response = self.client.post(
            "/api/v1/finance/vendors",
            data={
                "name": "BuildMart Nigeria",
                "email": "accounts@buildmart.test",
                "phone": "+2348011112222",
                "tax_id": "TIN-BUILD-001",
                "default_category": "materials",
            },
            content_type="application/json",
            **self.headers,
        )
        self.assertEqual(create_response.status_code, 201)
        vendor_id = create_response.json()["id"]
        self.assertTrue(create_response.json()["vendor_number"].startswith("VEN-"))

        list_response = self.client.get(
            "/api/v1/finance/vendors",
            {"search": "BuildMart", "default_category": "materials"},
            **self.headers,
        )
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(list_response.json()["count"], 1)

        update_response = self.client.patch(
            f"/api/v1/finance/vendors/{vendor_id}",
            data={"phone": "+2348099990000"},
            content_type="application/json",
            **self.headers,
        )
        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(update_response.json()["phone"], "+2348099990000")

        deactivate_response = self.client.post(
            f"/api/v1/finance/vendors/{vendor_id}/deactivate",
            data={},
            content_type="application/json",
            **self.headers,
        )
        self.assertEqual(deactivate_response.status_code, 200)
        self.assertEqual(
            deactivate_response.json()["status"], FinanceVendor.STATUS.INACTIVE
        )

    def test_vendor_bill_workflow_posts_payable_wallet_cashbook_and_order_costs(self):
        account = self._create_account(self.lagos, opening_balance=Decimal("0.00"))
        wallet = FinanceWallet.objects.create(
            client=self.lagos_order.client,
            service_order=self.lagos_order,
            wallet_type=FinanceWallet.WALLET_TYPE.PROJECT,
            name="Greenview Vendor Wallet",
            purpose="Vendor payable test",
            created_by=self.employee.user,
        )
        vendor = FinanceVendor.objects.create(
            name="BuildMart Nigeria",
            default_category=FinanceVendor.CATEGORY.MATERIALS,
            created_by=self.employee.user,
        )

        create_response = self.client.post(
            "/api/v1/finance/vendor-bills",
            data={
                "vendor_id": vendor.id,
                "service_order_id": self.lagos_order.id,
                "category": "Construction Materials",
                "description": "Gypsum boards and ceiling accessories",
                "gross_amount": "1850000.00",
                "withholding_tax": "92500.00",
                "bill_date": timezone.localdate().isoformat(),
                "due_date": (timezone.localdate() + timedelta(days=7)).isoformat(),
                "attachment": "https://example.com/vendor-bill.pdf",
            },
            content_type="application/json",
            **self.headers,
        )
        self.assertEqual(create_response.status_code, 201)
        bill_id = create_response.json()["id"]
        self.assertTrue(create_response.json()["bill_number"].startswith("BILL-"))
        self.assertEqual(create_response.json()["branch_id"], self.lagos.id)
        self.assertEqual(create_response.json()["net_amount"], "1757500.00")

        status_patch = self.client.patch(
            f"/api/v1/finance/vendor-bills/{bill_id}",
            data={"status": "paid"},
            content_type="application/json",
            **self.headers,
        )
        self.assertEqual(status_patch.status_code, 400)

        approve_response = self.client.post(
            f"/api/v1/finance/vendor-bills/{bill_id}/approve",
            data={},
            content_type="application/json",
            **self.headers,
        )
        self.assertEqual(approve_response.status_code, 200)
        self.assertEqual(approve_response.json()["status"], VendorBill.STATUS.APPROVED)
        commitment = FinanceWalletEntry.objects.get(
            vendor_bill_id=bill_id,
            entry_type=FinanceWalletEntry.ENTRY_TYPE.COMMITMENT,
        )
        self.assertEqual(commitment.wallet, wallet)
        self.assertEqual(commitment.amount, Decimal("1850000.00"))

        summary_response = self.client.get(
            "/api/v1/finance/vendor-bills/summary", **self.headers
        )
        self.assertEqual(summary_response.status_code, 200)
        self.assertEqual(summary_response.json()["total_payable"], "1757500.00")
        self.assertEqual(summary_response.json()["approved_unpaid"], "1757500.00")

        pay_response = self.client.post(
            f"/api/v1/finance/vendor-bills/{bill_id}/pay",
            data={
                "finance_account_id": account.id,
                "payment_reference": "VB-PAY-001",
            },
            content_type="application/json",
            **self.headers,
        )
        self.assertEqual(pay_response.status_code, 200)
        self.assertEqual(pay_response.json()["status"], VendorBill.STATUS.PAID)
        self.assertEqual(pay_response.json()["finance_account_id"], account.id)
        self.assertEqual(pay_response.json()["payment_reference"], "VB-PAY-001")

        release = FinanceWalletEntry.objects.get(
            vendor_bill_id=bill_id,
            entry_type=FinanceWalletEntry.ENTRY_TYPE.COMMITMENT_RELEASE,
        )
        spend = FinanceWalletEntry.objects.get(
            vendor_bill_id=bill_id,
            entry_type=FinanceWalletEntry.ENTRY_TYPE.SPEND,
        )
        self.assertEqual(release.amount, Decimal("1850000.00"))
        self.assertEqual(spend.amount, Decimal("1850000.00"))
        wallet = FinanceWallet.objects.get(id=wallet.id)
        self.assertEqual(wallet.balance_summary()["committed"], Decimal("0.00"))
        self.assertEqual(wallet.balance_summary()["spent"], Decimal("1850000.00"))

        cashbook_response = self.client.get(
            "/api/v1/finance/cashbook",
            {"source": "vendor_bill"},
            **self.headers,
        )
        self.assertEqual(cashbook_response.status_code, 200)
        self.assertEqual(cashbook_response.json()["count"], 1)
        cashbook_row = cashbook_response.json()["items"][0]
        self.assertEqual(cashbook_row["source"], "vendor_bill")
        self.assertEqual(cashbook_row["money_out"], "1757500.00")

        costs_response = self.client.get(
            f"/api/v1/finance/service-orders/{self.lagos_order.id}/costs",
            {"search": "BuildMart"},
            **self.headers,
        )
        self.assertEqual(costs_response.status_code, 200)
        self.assertEqual(costs_response.json()["count"], 1)
        self.assertEqual(costs_response.json()["items"][0]["source"], "vendor_bill")

        profitability_response = self.client.get(
            f"/api/v1/finance/service-orders/{self.lagos_order.id}/profitability",
            **self.headers,
        )
        self.assertEqual(profitability_response.status_code, 200)
        self.assertEqual(profitability_response.json()["paid_costs"], "1850000.00")

        transactions_response = self.client.get(
            f"/api/v1/finance/service-orders/{self.lagos_order.id}/transactions",
            {"source": "vendor_bill"},
            **self.headers,
        )
        self.assertEqual(transactions_response.status_code, 200)
        self.assertEqual(transactions_response.json()["count"], 1)
        self.assertEqual(
            transactions_response.json()["items"][0]["money_out"], "1757500.00"
        )

        duplicate_pay = self.client.post(
            f"/api/v1/finance/vendor-bills/{bill_id}/pay",
            data={"finance_account_id": account.id},
            content_type="application/json",
            **self.headers,
        )
        self.assertEqual(duplicate_pay.status_code, 400)

        void_paid = self.client.post(
            f"/api/v1/finance/vendor-bills/{bill_id}/void",
            data={},
            content_type="application/json",
            **self.headers,
        )
        self.assertEqual(void_paid.status_code, 400)

    def test_vendor_bill_reject_and_void_unpaid_commitment(self):
        vendor = FinanceVendor.objects.create(
            name="Prime Survey Supplies",
            default_category=FinanceVendor.CATEGORY.MATERIALS,
            created_by=self.employee.user,
        )
        rejected_bill = VendorBill.objects.create(
            vendor=vendor,
            branch=self.lagos,
            category="Survey Equipment",
            description="Unclear supplier invoice",
            gross_amount=Decimal("2350000.00"),
            withholding_tax=Decimal("117500.00"),
            bill_date=timezone.localdate(),
            due_date=timezone.localdate() + timedelta(days=3),
            created_by=self.employee.user,
        )

        reject_response = self.client.post(
            f"/api/v1/finance/vendor-bills/{rejected_bill.id}/reject",
            data={"rejection_reason": "Duplicate supplier bill"},
            content_type="application/json",
            **self.headers,
        )
        self.assertEqual(reject_response.status_code, 200)
        self.assertEqual(reject_response.json()["status"], VendorBill.STATUS.REJECTED)
        self.assertEqual(
            reject_response.json()["rejection_reason"], "Duplicate supplier bill"
        )
        self.assertFalse(
            FinanceWalletEntry.objects.filter(vendor_bill=rejected_bill).exists()
        )

        wallet = FinanceWallet.objects.create(
            client=self.lagos_order.client,
            service_order=self.lagos_order,
            wallet_type=FinanceWallet.WALLET_TYPE.PROJECT,
            name="Void Vendor Wallet",
            purpose="Vendor void test",
            created_by=self.employee.user,
        )
        bill = VendorBill.objects.create(
            vendor=vendor,
            service_order=self.lagos_order,
            category="Survey Equipment",
            description="Beacon supplies",
            gross_amount=Decimal("500000.00"),
            withholding_tax=Decimal("25000.00"),
            bill_date=timezone.localdate(),
            due_date=timezone.localdate() + timedelta(days=5),
            created_by=self.employee.user,
        )
        approve_response = self.client.post(
            f"/api/v1/finance/vendor-bills/{bill.id}/approve",
            data={},
            content_type="application/json",
            **self.headers,
        )
        self.assertEqual(approve_response.status_code, 200)
        self.assertEqual(wallet.balance_summary()["committed"], Decimal("500000.00"))

        void_response = self.client.post(
            f"/api/v1/finance/vendor-bills/{bill.id}/void",
            data={},
            content_type="application/json",
            **self.headers,
        )
        self.assertEqual(void_response.status_code, 200)
        self.assertEqual(void_response.json()["status"], VendorBill.STATUS.VOID)
        entry = FinanceWalletEntry.objects.get(vendor_bill=bill)
        self.assertEqual(entry.status, FinanceWalletEntry.STATUS.VOID)
        wallet = FinanceWallet.objects.get(id=wallet.id)
        self.assertEqual(wallet.balance_summary()["committed"], Decimal("0.00"))

    def test_petty_cash_issue_retire_posts_cashbook_wallet_and_order_costs(self):
        requester = self.create_user_with_employee(
            "petty.requester@test.com",
            "pettyrequester",
            "EMP-PETTY-REQ",
        )
        account = self._create_cash_account(
            self.lagos, opening_balance=Decimal("1000000.00")
        )
        wallet = FinanceWallet.objects.create(
            client=self.lagos_order.client,
            service_order=self.lagos_order,
            wallet_type=FinanceWallet.WALLET_TYPE.PROJECT,
            name="Greenview Petty Cash Wallet",
            purpose="Petty cash retirement test",
            created_by=self.employee.user,
        )

        create_response = self.client.post(
            "/api/v1/finance/petty-cash/advances",
            data={
                "requester_id": requester.user.id,
                "finance_account_id": account.id,
                "service_order_id": self.lagos_order.id,
                "purpose": "Survey field logistics advance",
                "amount_requested": "285000.00",
                "due_date": (timezone.localdate() + timedelta(days=3)).isoformat(),
                "attachment": "https://example.com/petty-request.pdf",
                "notes": "Field transport and local supplies",
            },
            content_type="application/json",
            **self.headers,
        )
        self.assertEqual(create_response.status_code, 201)
        advance_id = create_response.json()["id"]
        self.assertTrue(create_response.json()["advance_number"].startswith("PC-"))
        self.assertEqual(create_response.json()["branch_id"], self.lagos.id)

        approve_response = self.client.post(
            f"/api/v1/finance/petty-cash/advances/{advance_id}/approve",
            data={},
            content_type="application/json",
            **self.headers,
        )
        self.assertEqual(approve_response.status_code, 200)
        self.assertEqual(
            approve_response.json()["status"], PettyCashAdvance.STATUS.APPROVED
        )

        issue_response = self.client.post(
            f"/api/v1/finance/petty-cash/advances/{advance_id}/issue",
            data={"amount_issued": "285000.00"},
            content_type="application/json",
            **self.headers,
        )
        self.assertEqual(issue_response.status_code, 200)
        self.assertEqual(
            issue_response.json()["status"], PettyCashAdvance.STATUS.ISSUED
        )
        self.assertEqual(issue_response.json()["amount_issued"], "285000.00")

        cashbook_issue = self.client.get(
            "/api/v1/finance/cashbook",
            {"finance_account_id": account.id, "source": "petty_cash_advance"},
            **self.headers,
        )
        self.assertEqual(cashbook_issue.status_code, 200)
        self.assertEqual(cashbook_issue.json()["count"], 1)
        self.assertEqual(cashbook_issue.json()["items"][0]["money_out"], "285000.00")
        self.assertEqual(
            cashbook_issue.json()["items"][0]["running_balance"], "715000.00"
        )

        retire_response = self.client.post(
            f"/api/v1/finance/petty-cash/advances/{advance_id}/retire",
            data={
                "lines": [
                    {
                        "category": "travel",
                        "cost_type": "direct_cost",
                        "stage": "Fieldwork",
                        "description": "Survey transport",
                        "amount_spent": "250000.00",
                        "attachment": "https://example.com/petty-receipt.png",
                        "billable": True,
                        "client_visible": True,
                    },
                    {
                        "description": "Returned unused cash",
                        "amount_returned": "35000.00",
                    },
                ]
            },
            content_type="application/json",
            **self.headers,
        )
        self.assertEqual(retire_response.status_code, 200)
        self.assertEqual(
            retire_response.json()["status"], PettyCashAdvance.STATUS.RETIRED
        )
        self.assertEqual(retire_response.json()["amount_retired"], "250000.00")
        self.assertEqual(retire_response.json()["amount_returned"], "35000.00")
        self.assertEqual(retire_response.json()["unretired_amount"], "0.00")

        spend_line = PettyCashRetirementLine.objects.get(
            amount_spent=Decimal("250000.00")
        )
        spend_entry = FinanceWalletEntry.objects.get(
            petty_cash_retirement_line=spend_line
        )
        self.assertEqual(spend_entry.wallet, wallet)
        self.assertEqual(spend_entry.entry_type, FinanceWalletEntry.ENTRY_TYPE.SPEND)
        self.assertEqual(spend_entry.amount, Decimal("250000.00"))
        wallet = FinanceWallet.objects.get(id=wallet.id)
        self.assertEqual(wallet.balance_summary()["spent"], Decimal("250000.00"))

        cashbook_return = self.client.get(
            "/api/v1/finance/cashbook",
            {"finance_account_id": account.id, "source": "petty_cash_return"},
            **self.headers,
        )
        self.assertEqual(cashbook_return.status_code, 200)
        self.assertEqual(cashbook_return.json()["count"], 1)
        self.assertEqual(cashbook_return.json()["items"][0]["money_in"], "35000.00")

        cashbook_full = self.client.get(
            "/api/v1/finance/cashbook",
            {"finance_account_id": account.id},
            **self.headers,
        )
        self.assertEqual(cashbook_full.status_code, 200)
        self.assertEqual(
            [row["source"] for row in cashbook_full.json()["items"]],
            ["petty_cash_advance", "petty_cash_return"],
        )
        self.assertEqual(
            cashbook_full.json()["items"][-1]["running_balance"], "750000.00"
        )

        summary_response = self.client.get(
            "/api/v1/finance/petty-cash/summary",
            {"finance_account_id": account.id},
            **self.headers,
        )
        self.assertEqual(summary_response.status_code, 200)
        summary = summary_response.json()
        self.assertEqual(summary["issued_total"], "285000.00")
        self.assertEqual(summary["retired_total"], "250000.00")
        self.assertEqual(summary["returned_total"], "35000.00")
        self.assertEqual(summary["unretired_total"], "0.00")
        self.assertEqual(summary["accounts"][0]["calculated_balance"], "750000.00")

        costs_response = self.client.get(
            f"/api/v1/finance/service-orders/{self.lagos_order.id}/costs",
            {"search": "Survey transport"},
            **self.headers,
        )
        self.assertEqual(costs_response.status_code, 200)
        self.assertEqual(costs_response.json()["count"], 1)
        self.assertEqual(costs_response.json()["items"][0]["source"], "petty_cash")
        self.assertEqual(costs_response.json()["items"][0]["amount"], "250000.00")

        profitability_response = self.client.get(
            f"/api/v1/finance/service-orders/{self.lagos_order.id}/profitability",
            **self.headers,
        )
        self.assertEqual(profitability_response.status_code, 200)
        self.assertEqual(profitability_response.json()["paid_costs"], "250000.00")

        transactions_response = self.client.get(
            f"/api/v1/finance/service-orders/{self.lagos_order.id}/transactions",
            {"source": "petty_cash"},
            **self.headers,
        )
        self.assertEqual(transactions_response.status_code, 200)
        self.assertEqual(transactions_response.json()["count"], 1)
        self.assertEqual(
            transactions_response.json()["items"][0]["money_out"], "250000.00"
        )

    def test_petty_cash_issue_blocks_requester_with_overdue_unretired_advance(self):
        requester = self.create_user_with_employee(
            "petty.overdue@test.com",
            "pettyoverdue",
            "EMP-PETTY-OVERDUE",
        )
        account = self._create_cash_account(
            self.lagos, opening_balance=Decimal("500000.00")
        )
        PettyCashAdvance.objects.create(
            requester=requester.user,
            branch=self.lagos,
            finance_account=account,
            purpose="Previous unretired advance",
            amount_requested=Decimal("50000.00"),
            amount_issued=Decimal("50000.00"),
            due_date=timezone.localdate() - timedelta(days=1),
            issued_at=timezone.now() - timedelta(days=3),
            status=PettyCashAdvance.STATUS.ISSUED,
            created_by=self.employee.user,
        )
        new_advance = PettyCashAdvance.objects.create(
            requester=requester.user,
            branch=self.lagos,
            finance_account=account,
            purpose="New advance",
            amount_requested=Decimal("25000.00"),
            due_date=timezone.localdate() + timedelta(days=2),
            status=PettyCashAdvance.STATUS.APPROVED,
            approved_by=self.employee.user,
            approved_at=timezone.now(),
            created_by=self.employee.user,
        )

        response = self.client.post(
            f"/api/v1/finance/petty-cash/advances/{new_advance.id}/issue",
            data={},
            content_type="application/json",
            **self.headers,
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("overdue unretired", response.json()["detail"])
        new_advance.refresh_from_db()
        self.assertEqual(new_advance.status, PettyCashAdvance.STATUS.APPROVED)

    def test_cashbook_lists_payments_and_paid_expense_outflows_with_running_balance(
        self,
    ):
        account = self._create_account(
            self.lagos,
            opening_balance=Decimal("1000.00"),
            opening_balance_date=timezone.localdate() - timedelta(days=5),
        )
        invoice = self._create_invoice(
            client=self.other_customer,
            service=self.other_service,
            service_request=self.lagos_request,
            order=self.lagos_order,
            subtotal=Decimal("1000.00"),
            amount_paid=Decimal("0.00"),
            status="sent",
            issue_date=timezone.localdate(),
            due_date=timezone.localdate() + timedelta(days=14),
        )
        payment = Payment.objects.create(
            invoice=invoice,
            amount=Decimal("400.00"),
            payment_method="bank_transfer",
            payment_date=timezone.localdate(),
            transaction_reference="CASHBOOK-PAYMENT",
            finance_account=account,
            proof_of_payment="https://example.com/cashbook-payment.png",
            created_by=self.employee.user,
        )
        service_cost = Expense.objects.create(
            user=self.employee.user,
            branch=self.lagos,
            finance_account=account,
            service_order=self.lagos_order,
            date=timezone.localdate() + timedelta(days=1),
            description="Paid field logistics",
            amount=Decimal("150.00"),
            category=Expense.CATEGORY_CHOICES.TRAVEL,
            cost_type=Expense.COST_TYPE.DIRECT_COST,
            status=Expense.STATUS.PAID,
            project_name="Greenview Layout Survey",
            beneficiary="Survey Field Team",
            paid_at=timezone.now(),
        )
        operating_expense = Expense.objects.create(
            user=self.employee.user,
            branch=self.lagos,
            finance_account=account,
            date=timezone.localdate() + timedelta(days=2),
            description="Paid office supplies",
            amount=Decimal("50.00"),
            category=Expense.CATEGORY_CHOICES.OTHER,
            cost_type=Expense.COST_TYPE.OPERATING_EXPENSE,
            status=Expense.STATUS.PAID,
            project_name="General Operations",
            beneficiary="Office Vendor",
            paid_at=timezone.now(),
        )

        response = self.client.get(
            "/api/v1/finance/cashbook",
            {"finance_account_id": account.id},
            **self.headers,
        )

        self.assertEqual(response.status_code, 200)
        rows = response.json()["items"]
        self.assertEqual(
            [row["reference"] for row in rows],
            [
                payment.payment_reference,
                service_cost.expense_number,
                operating_expense.expense_number,
            ],
        )
        self.assertEqual(rows[0]["source"], "client_payment")
        self.assertEqual(rows[0]["money_in"], "400.00")
        self.assertEqual(rows[0]["running_balance"], "1400.00")
        self.assertEqual(rows[1]["source"], "service_cost")
        self.assertEqual(rows[1]["money_out"], "150.00")
        self.assertEqual(rows[1]["running_balance"], "1250.00")
        self.assertEqual(rows[2]["source"], "operating_expense")
        self.assertEqual(rows[2]["money_out"], "50.00")
        self.assertEqual(rows[2]["running_balance"], "1200.00")

        summary_response = self.client.get(
            "/api/v1/finance/cashbook/summary",
            {"finance_account_id": account.id},
            **self.headers,
        )
        self.assertEqual(summary_response.status_code, 200)
        summary = summary_response.json()
        self.assertEqual(summary["opening_balance"], "1000.00")
        self.assertEqual(summary["period_inflow"], "400.00")
        self.assertEqual(summary["period_outflow"], "200.00")
        self.assertEqual(summary["net_movement"], "200.00")
        self.assertEqual(summary["closing_balance"], "1200.00")
        self.assertEqual(summary["posted_count"], 3)
        self.assertEqual(summary["pending_count"], 0)
        self.assertEqual(summary["inflow_by_source"]["client_payment"], "400.00")
        self.assertEqual(summary["outflow_by_source"]["service_cost"], "150.00")
        self.assertEqual(summary["outflow_by_source"]["operating_expense"], "50.00")

    def test_cashbook_source_filter_returns_service_costs(self):
        account = self._create_account(self.lagos, opening_balance=Decimal("0.00"))
        Expense.objects.create(
            user=self.employee.user,
            branch=self.lagos,
            finance_account=account,
            service_order=self.lagos_order,
            date=timezone.localdate(),
            description="Service-linked paid cost",
            amount=Decimal("75.00"),
            category=Expense.CATEGORY_CHOICES.OTHER,
            cost_type=Expense.COST_TYPE.DIRECT_COST,
            status=Expense.STATUS.PAID,
            paid_at=timezone.now(),
        )
        Expense.objects.create(
            user=self.employee.user,
            branch=self.lagos,
            finance_account=account,
            date=timezone.localdate(),
            description="Unlinked capex",
            amount=Decimal("60.00"),
            category=Expense.CATEGORY_CHOICES.EQUIPMENT,
            cost_type=Expense.COST_TYPE.CAPITAL_EXPENDITURE,
            status=Expense.STATUS.PAID,
            paid_at=timezone.now(),
        )

        response = self.client.get(
            "/api/v1/finance/cashbook",
            {"finance_account_id": account.id, "source": "service_cost"},
            **self.headers,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 1)
        self.assertEqual(response.json()["items"][0]["source"], "service_cost")

    def test_service_order_profitability_list_and_detail_values(self):
        payment, paid_cost, approved_cost, wallet = self._seed_profitability_activity()

        response = self.client.get(
            "/api/v1/finance/service-orders/profitability",
            {"service_order_id": self.lagos_order.id},
            **self.headers,
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["count"], 1)
        row = body["items"][0]
        self.assertEqual(row["order_id"], self.lagos_order.id)
        self.assertEqual(row["order_number"], self.lagos_order.order_number)
        self.assertEqual(row["source_reference"], self.lagos_request.request_number)
        self.assertEqual(row["client_name"], "Greenview Cooperative")
        self.assertEqual(row["service_name"], self.other_service.name)
        self.assertEqual(row["branch_id"], self.lagos.id)
        self.assertEqual(row["project_name"], self.lagos_order.description)
        self.assertIsNone(row["contract_type"])
        self.assertEqual(row["contract_value"], "300000.00")
        self.assertIsNone(row["cost_budget"])
        self.assertIsNone(row["overhead_amount"])
        self.assertIsNone(row["expected_gross_profit"])
        self.assertIsNone(row["expected_margin_pct"])
        self.assertEqual(row["invoiced_total"], "3000.00")
        self.assertEqual(row["collected_total"], "500.00")
        self.assertEqual(row["outstanding_invoice_balance"], "2500.00")
        self.assertEqual(row["paid_costs"], "150.00")
        self.assertEqual(row["committed_costs"], "80.00")
        self.assertEqual(row["cash_contribution"], "350.00")
        self.assertEqual(row["accrued_profit"], "2850.00")
        self.assertEqual(row["wallet_id"], wallet.id)
        self.assertEqual(row["wallet_funded"], "500.00")
        self.assertEqual(row["wallet_spent"], "100.00")
        self.assertEqual(row["wallet_committed"], "80.00")
        self.assertEqual(row["wallet_available"], "320.00")

        detail_response = self.client.get(
            f"/api/v1/finance/service-orders/{self.lagos_order.id}/profitability",
            **self.headers,
        )
        self.assertEqual(detail_response.status_code, 200)
        detail = detail_response.json()
        self.assertEqual(detail["order_id"], self.lagos_order.id)
        self.assertEqual(
            detail["collected_total"],
            payment.amount.quantize(Decimal("0.01")).to_eng_string(),
        )
        self.assertEqual(
            detail["paid_costs"],
            paid_cost.amount.quantize(Decimal("0.01")).to_eng_string(),
        )
        self.assertEqual(
            detail["committed_costs"],
            approved_cost.amount.quantize(Decimal("0.01")).to_eng_string(),
        )

    def test_service_order_profitability_summary_totals(self):
        self._seed_profitability_activity()

        response = self.client.get(
            "/api/v1/finance/service-orders/profitability/summary",
            {"service_order_id": self.lagos_order.id},
            **self.headers,
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["order_count"], 1)
        self.assertEqual(body["total_contract_value"], "300000.00")
        self.assertEqual(body["total_invoiced"], "3000.00")
        self.assertEqual(body["total_collected"], "500.00")
        self.assertEqual(body["total_outstanding"], "2500.00")
        self.assertEqual(body["total_paid_costs"], "150.00")
        self.assertEqual(body["total_committed_costs"], "80.00")
        self.assertEqual(body["total_cash_contribution"], "350.00")
        self.assertEqual(body["total_accrued_profit"], "2850.00")
        self.assertEqual(body["profitable_order_count"], 1)
        self.assertEqual(body["loss_making_order_count"], 0)
        self.assertEqual(body["cash_positive_order_count"], 1)
        self.assertEqual(body["cash_negative_order_count"], 0)

    def test_service_order_costs_endpoint_filters_cost_ledger(self):
        _, paid_cost, approved_cost, _ = self._seed_profitability_activity()

        approved_response = self.client.get(
            f"/api/v1/finance/service-orders/{self.lagos_order.id}/costs",
            {"status": "approved"},
            **self.headers,
        )

        self.assertEqual(approved_response.status_code, 200)
        self.assertEqual(approved_response.json()["count"], 1)
        row = approved_response.json()["items"][0]
        self.assertEqual(row["id"], approved_cost.id)
        self.assertEqual(row["expense_number"], approved_cost.expense_number)
        self.assertEqual(row["category"], Expense.CATEGORY_CHOICES.EQUIPMENT)
        self.assertEqual(row["cost_type"], Expense.COST_TYPE.DIRECT_COST)
        self.assertEqual(row["stage"], "Fieldwork")
        self.assertEqual(row["beneficiary"], "Approved Suppliers")
        self.assertFalse(row["billable"])
        self.assertTrue(row["client_visible"])

        billable_response = self.client.get(
            f"/api/v1/finance/service-orders/{self.lagos_order.id}/costs",
            {"billable": "true"},
            **self.headers,
        )
        self.assertEqual(billable_response.status_code, 200)
        self.assertEqual(billable_response.json()["count"], 1)
        self.assertEqual(billable_response.json()["items"][0]["id"], paid_cost.id)

    def test_service_order_transactions_running_contribution(self):
        payment, paid_cost, _, _ = self._seed_profitability_activity()

        response = self.client.get(
            f"/api/v1/finance/service-orders/{self.lagos_order.id}/transactions",
            **self.headers,
        )

        self.assertEqual(response.status_code, 200)
        rows = response.json()["items"]
        self.assertEqual(
            [row["reference"] for row in rows],
            [payment.payment_reference, paid_cost.expense_number],
        )
        self.assertEqual(rows[0]["source"], "client_payment")
        self.assertEqual(rows[0]["money_in"], "500.00")
        self.assertEqual(rows[0]["money_out"], "0.00")
        self.assertEqual(rows[0]["running_contribution"], "500.00")
        self.assertEqual(rows[1]["source"], "service_cost")
        self.assertEqual(rows[1]["money_in"], "0.00")
        self.assertEqual(rows[1]["money_out"], "150.00")
        self.assertEqual(rows[1]["running_contribution"], "350.00")

        filtered = self.client.get(
            f"/api/v1/finance/service-orders/{self.lagos_order.id}/transactions",
            {"source": "service_cost"},
            **self.headers,
        )
        self.assertEqual(filtered.status_code, 200)
        self.assertEqual(filtered.json()["count"], 1)
        self.assertEqual(filtered.json()["items"][0]["source"], "service_cost")

    def test_branch_scoped_user_only_sees_allowed_profitability_orders(self):
        self._seed_profitability_activity()
        scoped_role = Role.objects.create(
            name="Scoped Enugu Profitability Viewer",
            permissions={
                "service_invoices": ["list"],
                "payments": ["list"],
                "expenses": ["list"],
            },
        )
        scoped_role.branches.add(self.enugu)
        scoped_employee = self.create_user_with_employee(
            "scoped.profitability@test.com",
            "scopedprofitability",
            "EMP-FIN-PROFIT",
            role=scoped_role,
        )

        response = self.client.get(
            "/api/v1/finance/service-orders/profitability",
            **self.auth_headers(scoped_employee),
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 0)

        detail_response = self.client.get(
            f"/api/v1/finance/service-orders/{self.lagos_order.id}/profitability",
            **self.auth_headers(scoped_employee),
        )
        self.assertEqual(detail_response.status_code, 404)

    def test_finance_does_not_expose_service_order_create_endpoint(self):
        response = self.client.post(
            "/api/v1/finance/service-orders",
            data={},
            content_type="application/json",
            **self.headers,
        )

        self.assertIn(response.status_code, [404, 405])

    def test_approved_payment_posts_wallet_funding_when_order_has_wallet(self):
        wallet = FinanceWallet.objects.create(
            client=self.overdue_invoice.client,
            service_order=self.lagos_order,
            wallet_type=FinanceWallet.WALLET_TYPE.PROJECT,
            name="Greenview Survey Wallet",
            purpose="Survey project funds",
            created_by=self.employee.user,
        )
        account = self._create_account(self.lagos)
        submission = PaymentSubmission.objects.create(
            invoice=self.overdue_invoice,
            client=self.overdue_invoice.client,
            finance_account=account,
            amount=Decimal("200.00"),
            payment_method="bank_transfer",
            payment_date=timezone.localdate(),
            transaction_reference="WALLET-FUNDING-TXN",
            proof_of_payment="https://example.com/wallet-funding.png",
            submitted_by=self.employee.user,
            submitted_by_type=PaymentSubmission.SUBMITTED_BY_TYPE.STAFF,
        )

        response = self.client.post(
            f"/api/v1/finance/payments/submissions/{submission.id}/review",
            data={"status": "confirmed"},
            content_type="application/json",
            **self.headers,
        )

        self.assertEqual(response.status_code, 200)
        payment = Payment.objects.get(id=response.json()["confirmed_payment_id"])
        entry = FinanceWalletEntry.objects.get(payment=payment)
        self.assertEqual(entry.wallet, wallet)
        self.assertEqual(entry.invoice, self.overdue_invoice)
        self.assertEqual(entry.service_order, self.lagos_order)
        self.assertEqual(entry.entry_type, FinanceWalletEntry.ENTRY_TYPE.FUNDING)
        self.assertEqual(entry.status, FinanceWalletEntry.STATUS.POSTED)
        self.assertEqual(entry.amount, Decimal("200.00"))
        self.assertEqual(wallet.balance_summary()["funded"], Decimal("200.00"))

    def test_get_payment_submission_detail(self):
        account = self._create_account(self.enugu)
        submission = PaymentSubmission.objects.create(
            invoice=self.sent_invoice,
            client=self.sent_invoice.client,
            finance_account=account,
            amount=Decimal("100.00"),
            payment_method="bank_transfer",
            payment_date=timezone.localdate(),
            transaction_reference="SUB-DETAIL-TXN",
            proof_of_payment="https://example.com/sub-detail-proof.png",
            submitted_by=self.employee.user,
            submitted_by_type=PaymentSubmission.SUBMITTED_BY_TYPE.STAFF,
        )

        response = self.client.get(
            f"/api/v1/finance/payments/submissions/{submission.id}",
            **self.headers,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["id"], submission.id)
        self.assertEqual(response.json()["invoice_id"], self.sent_invoice.id)
        self.assertEqual(response.json()["finance_account_id"], account.id)
        self.assertEqual(response.json()["transaction_reference"], "SUB-DETAIL-TXN")

    def test_get_confirmed_payment_detail(self):
        invoice = self._create_invoice(
            client=self.customer,
            service=self.service,
            service_request=self.enugu_request,
            subtotal=Decimal("1000.00"),
            amount_paid=Decimal("0.00"),
            status="sent",
            issue_date=timezone.localdate(),
            due_date=timezone.localdate() + timedelta(days=14),
        )
        account = self._create_account(self.enugu)
        payment = Payment.objects.create(
            invoice=invoice,
            amount=Decimal("250.00"),
            payment_method="bank_transfer",
            payment_date=timezone.localdate(),
            transaction_reference="PAY-DETAIL-TXN",
            finance_account=account,
            proof_of_payment="https://example.com/pay-detail-proof.png",
            created_by=self.employee.user,
        )

        response = self.client.get(
            f"/api/v1/finance/payments/confirmed/{payment.id}",
            **self.headers,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["id"], payment.id)
        self.assertEqual(response.json()["invoice_id"], invoice.id)
        self.assertEqual(response.json()["finance_account_id"], account.id)
        self.assertEqual(
            response.json()["proof_of_payment"],
            "https://example.com/pay-detail-proof.png",
        )

    def test_rejection_leaves_balance_unchanged_and_allows_resubmission(self):
        invoice = self._create_invoice(
            client=self.customer,
            service=self.service,
            service_request=self.enugu_request,
            subtotal=Decimal("1000.00"),
            amount_paid=Decimal("0.00"),
            status="sent",
            issue_date=timezone.localdate(),
            due_date=timezone.localdate() + timedelta(days=14),
        )
        account = self._create_account(self.enugu)
        submission = PaymentSubmission.objects.create(
            invoice=invoice,
            client=invoice.client,
            finance_account=account,
            amount=Decimal("200.00"),
            payment_method="bank_transfer",
            payment_date=timezone.localdate(),
            transaction_reference="BAD-TXN",
            proof_of_payment="https://example.com/bad-proof.png",
            submitted_by=self.employee.user,
            submitted_by_type=PaymentSubmission.SUBMITTED_BY_TYPE.STAFF,
        )

        reject_response = self.client.post(
            f"/api/v1/finance/payments/submissions/{submission.id}/review",
            data={"status": "rejected", "rejection_reason": "Unclear proof"},
            content_type="application/json",
            **self.headers,
        )

        self.assertEqual(reject_response.status_code, 200)
        invoice.refresh_from_db()
        self.assertEqual(invoice.amount_paid, Decimal("0.00"))
        self.assertFalse(Payment.objects.filter(invoice=invoice).exists())

        retry_response = self.client.post(
            "/api/v1/finance/payments/submissions",
            data={
                "invoice_id": invoice.id,
                "finance_account_id": account.id,
                "amount": "200.00",
                "payment_method": "bank_transfer",
                "payment_date": timezone.localdate().isoformat(),
                "transaction_reference": "GOOD-TXN",
                "proof_of_payment": "https://example.com/good-proof.png",
            },
            content_type="application/json",
            **self.headers,
        )
        self.assertEqual(retry_response.status_code, 201)

    def test_approval_fails_when_submission_exceeds_current_balance(self):
        invoice = self._create_invoice(
            client=self.customer,
            service=self.service,
            service_request=self.enugu_request,
            subtotal=Decimal("100.00"),
            amount_paid=Decimal("0.00"),
            status="sent",
            issue_date=timezone.localdate(),
            due_date=timezone.localdate() + timedelta(days=14),
        )
        account = self._create_account(self.enugu)
        submission = PaymentSubmission.objects.create(
            invoice=invoice,
            client=invoice.client,
            finance_account=account,
            amount=Decimal("150.00"),
            payment_method="bank_transfer",
            payment_date=timezone.localdate(),
            transaction_reference="OVERPAY",
            proof_of_payment="https://example.com/overpay.png",
            submitted_by=self.employee.user,
            submitted_by_type=PaymentSubmission.SUBMITTED_BY_TYPE.STAFF,
        )

        response = self.client.post(
            f"/api/v1/finance/payments/submissions/{submission.id}/review",
            data={"status": "confirmed"},
            content_type="application/json",
            **self.headers,
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("exceeds outstanding balance", response.json()["detail"])
        invoice.refresh_from_db()
        self.assertEqual(invoice.amount_paid, Decimal("0.00"))

    def test_branch_scoped_user_cannot_review_other_branch_submission(self):
        account = self._create_account(self.lagos)
        submission = PaymentSubmission.objects.create(
            invoice=self.overdue_invoice,
            client=self.overdue_invoice.client,
            finance_account=account,
            amount=Decimal("200.00"),
            payment_method="bank_transfer",
            payment_date=timezone.localdate(),
            transaction_reference="LAGOS-TXN",
            proof_of_payment="https://example.com/lagos-proof.png",
            submitted_by=self.employee.user,
            submitted_by_type=PaymentSubmission.SUBMITTED_BY_TYPE.STAFF,
        )
        scoped_role = Role.objects.create(
            name="Scoped Enugu Payment Reviewer",
            permissions={
                "payments": ["list", "create", "view"],
                "service_invoices": ["list"],
            },
        )
        scoped_role.branches.add(self.enugu)
        scoped_employee = self.create_user_with_employee(
            "scoped.payments@test.com",
            "scopedpayments",
            "EMP-FIN-PAY",
            role=scoped_role,
        )
        scoped_headers = self.auth_headers(scoped_employee)

        list_response = self.client.get(
            "/api/v1/finance/payments/submissions", **scoped_headers
        )
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(list_response.json()["count"], 0)

        review_response = self.client.post(
            f"/api/v1/finance/payments/submissions/{submission.id}/review",
            data={"status": "confirmed"},
            content_type="application/json",
            **scoped_headers,
        )
        self.assertEqual(review_response.status_code, 400)
        self.overdue_invoice.refresh_from_db()
        self.assertEqual(self.overdue_invoice.amount_paid, Decimal("1000.00"))

        detail_response = self.client.get(
            f"/api/v1/finance/payments/submissions/{submission.id}",
            **scoped_headers,
        )
        self.assertEqual(detail_response.status_code, 404)

    def test_branch_scoped_user_cannot_get_other_branch_payment_detail(self):
        invoice = self._create_invoice(
            client=self.other_customer,
            service=self.other_service,
            service_request=self.lagos_request,
            subtotal=Decimal("1000.00"),
            amount_paid=Decimal("0.00"),
            status="sent",
            issue_date=timezone.localdate(),
            due_date=timezone.localdate() + timedelta(days=14),
        )
        account = self._create_account(self.lagos)
        payment = Payment.objects.create(
            invoice=invoice,
            amount=Decimal("250.00"),
            payment_method="bank_transfer",
            payment_date=timezone.localdate(),
            transaction_reference="LAGOS-PAY-DETAIL",
            finance_account=account,
            proof_of_payment="https://example.com/lagos-pay-detail.png",
            created_by=self.employee.user,
        )
        scoped_role = Role.objects.create(
            name="Scoped Enugu Payment Detail Viewer",
            permissions={"payments": ["list", "view"], "service_invoices": ["list"]},
        )
        scoped_role.branches.add(self.enugu)
        scoped_employee = self.create_user_with_employee(
            "scoped.payment.detail@test.com",
            "scopedpaymentdetail",
            "EMP-FIN-PAY-DETAIL",
            role=scoped_role,
        )

        response = self.client.get(
            f"/api/v1/finance/payments/confirmed/{payment.id}",
            **self.auth_headers(scoped_employee),
        )

        self.assertEqual(response.status_code, 404)

    def _seed_profitability_activity(self):
        account = self._create_account(self.lagos)
        payment = Payment.objects.create(
            invoice=self.overdue_invoice,
            amount=Decimal("500.00"),
            payment_method="bank_transfer",
            payment_date=timezone.localdate(),
            transaction_reference="PROFIT-PAYMENT",
            finance_account=account,
            proof_of_payment="https://example.com/profit-payment.png",
            created_by=self.employee.user,
        )
        paid_cost = Expense.objects.create(
            user=self.employee.user,
            branch=self.lagos,
            finance_account=account,
            service_order=self.lagos_order,
            date=timezone.localdate() + timedelta(days=1),
            description="Paid field logistics",
            amount=Decimal("150.00"),
            category=Expense.CATEGORY_CHOICES.TRAVEL,
            cost_type=Expense.COST_TYPE.DIRECT_COST,
            status=Expense.STATUS.PAID,
            stage="Fieldwork",
            beneficiary="Survey Field Team",
            project_name=self.lagos_order.description,
            billable=True,
            client_visible=True,
            paid_at=timezone.now(),
        )
        approved_cost = Expense.objects.create(
            user=self.employee.user,
            branch=self.lagos,
            finance_account=account,
            service_order=self.lagos_order,
            date=timezone.localdate() + timedelta(days=2),
            description="Committed equipment",
            amount=Decimal("80.00"),
            category=Expense.CATEGORY_CHOICES.EQUIPMENT,
            cost_type=Expense.COST_TYPE.DIRECT_COST,
            status=Expense.STATUS.APPROVED,
            stage="Fieldwork",
            beneficiary="Approved Suppliers",
            project_name=self.lagos_order.description,
            billable=False,
            client_visible=True,
        )
        Expense.objects.create(
            user=self.employee.user,
            branch=self.lagos,
            finance_account=account,
            service_order=self.lagos_order,
            date=timezone.localdate() + timedelta(days=3),
            description="Pending cost request",
            amount=Decimal("70.00"),
            category=Expense.CATEGORY_CHOICES.OTHER,
            cost_type=Expense.COST_TYPE.DIRECT_COST,
            status=Expense.STATUS.PENDING,
            stage="Fieldwork",
            beneficiary="Pending Vendor",
            project_name=self.lagos_order.description,
        )
        wallet = FinanceWallet.objects.create(
            client=self.lagos_order.client,
            service_order=self.lagos_order,
            wallet_type=FinanceWallet.WALLET_TYPE.PROJECT,
            name="Greenview Survey Wallet",
            purpose="Survey project funds",
            created_by=self.employee.user,
        )
        FinanceWalletEntry.objects.create(
            wallet=wallet,
            entry_type=FinanceWalletEntry.ENTRY_TYPE.FUNDING,
            amount=Decimal("500.00"),
            description="Funding for profitability test",
            created_by=self.employee.user,
        )
        FinanceWalletEntry.objects.create(
            wallet=wallet,
            entry_type=FinanceWalletEntry.ENTRY_TYPE.SPEND,
            amount=Decimal("100.00"),
            description="Wallet spend for profitability test",
            created_by=self.employee.user,
        )
        FinanceWalletEntry.objects.create(
            wallet=wallet,
            entry_type=FinanceWalletEntry.ENTRY_TYPE.COMMITMENT,
            amount=Decimal("80.00"),
            description="Wallet commitment for profitability test",
            created_by=self.employee.user,
        )
        return payment, paid_cost, approved_cost, wallet

    def _create_account(
        self, branch, opening_balance=Decimal("0.00"), opening_balance_date=None
    ):
        return FinanceAccount.objects.create(
            account_type=FinanceAccount.ACCOUNT_TYPE.BANK,
            display_name=f"{branch.branch_name} Collections",
            branch=branch,
            bank_name="GTBank",
            account_number=f"01234567{branch.id}",
            account_name="Bomach Group",
            opening_balance=opening_balance,
            opening_balance_date=opening_balance_date,
            created_by=self.employee.user,
        )

    def _create_cash_account(
        self, branch, opening_balance=Decimal("0.00"), opening_balance_date=None
    ):
        return FinanceAccount.objects.create(
            account_type=FinanceAccount.ACCOUNT_TYPE.CASH,
            display_name=f"{branch.branch_name} Petty Cash",
            branch=branch,
            opening_balance=opening_balance,
            opening_balance_date=opening_balance_date,
            created_by=self.employee.user,
        )

    def _client_auth_headers(self, user):
        token = JWTService.create_tokens(user.id)["access"]
        return {"HTTP_AUTHORIZATION": f"Bearer {token}"}
