from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.test import Client as DjangoClient
from django.test import TestCase
from django.utils import timezone

from finance.models import FinanceAccount
from services.models.payment import Invoice, Payment
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
from user.models.client_service import PaymentSubmission
from user.models.estate_property_invoice import EstatePropertyInvoice
from user.models.role import Role
from user.models.user import User
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

        list_response = self.client.get("/api/v1/finance/accounts", **self.headers)
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(list_response.json()["count"], 1)

        update_response = self.client.patch(
            f"/api/v1/finance/accounts/{account_id}",
            data={"display_name": "GTBank Main Operating"},
            content_type="application/json",
            **self.headers,
        )
        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(
            update_response.json()["display_name"], "GTBank Main Operating"
        )

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

    def _create_account(self, branch):
        return FinanceAccount.objects.create(
            account_type=FinanceAccount.ACCOUNT_TYPE.BANK,
            display_name=f"{branch.branch_name} Collections",
            branch=branch,
            bank_name="GTBank",
            account_number=f"01234567{branch.id}",
            account_name="Bomach Group",
            created_by=self.employee.user,
        )

    def _client_auth_headers(self, user):
        token = JWTService.create_tokens(user.id)["access"]
        return {"HTTP_AUTHORIZATION": f"Bearer {token}"}
