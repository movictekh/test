from datetime import date, timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from domains.real_estate.api.v1.schemas.estate_property_invoice import InvoiceCreateSchema
from domains.real_estate.models.estate import Estate, Property
from domains.real_estate.services.invoices import (
    create_estate_invoice,
    decide_estate_invoice_approval,
    record_estate_invoice_payment,
    submit_estate_invoice,
)
from finance.models import FinanceAccount, JournalEntry
from user.models.user import User
from user.tests.helpers import RoleAPITestMixin


class RealEstateInvoiceHardeningTests(RoleAPITestMixin, TestCase):
    def setUp(self):
        creator_role = self.create_role("RE Creator", {})
        manager_role = self.create_role("RE Manager", {})
        final_role = self.create_role("RE Final Approver", {})
        self.creator = self.create_user_with_employee(
            "re-creator@example.com", "recreator", "EMP-RE-CREATOR", creator_role
        )
        self.manager = self.create_user_with_employee(
            "re-manager@example.com", "remanager", "EMP-RE-MANAGER", manager_role
        )
        self.final = self.create_user_with_employee(
            "re-final@example.com", "refinal", "EMP-RE-FINAL", final_role
        )
        self.creator.reporting_to = self.manager
        self.creator.save(update_fields=["reporting_to", "updated_at"])
        self.client_user = User.objects.create_user(
            email="estate-client@example.com",
            username="estateclient",
            password="password123",
            first_name="Estate",
            last_name="Client",
        )
        self.account = FinanceAccount.objects.create(
            account_type=FinanceAccount.ACCOUNT_TYPE.BANK,
            display_name="Real Estate Collections",
            currency="NGN",
            bank_name="Bomach Test Bank",
            account_number="0123456789",
            account_name="Bomach Real Estate Collections",
            created_by=self.creator.user,
        )
        self.estate = Estate.objects.create(
            estate_name="Phase Three Estate",
            estate_code="RE-PHASE-3",
            estate_type="residential",
            developer_company_name="Bomach Group",
            estate_description="Phase 3 regression estate",
            country="Nigeria",
            state="Enugu",
            city_town="Enugu",
            precise_address="Enugu",
            price_per_sqm=Decimal("1000.00"),
            estate_status="available",
        )
        self.property_one = self._property("Plot A", 1, "100000.00")
        self.property_two = self._property("Plot B", 2, "200000.00")
        self.property_three = self._property("Plot C", 3, "300000.00")

    def _property(self, name, number, price):
        return Property.objects.create(
            estate=self.estate,
            property_type="plot",
            property_name=name,
            plot_number=number,
            price=Decimal(price),
            plot_size=Decimal("450.00"),
            status="available",
        )

    def _payload(self, items):
        return InvoiceCreateSchema(
            client_id=self.client_user.id,
            invoice_type="full-payment",
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=14),
            tax_rate=Decimal("7.50"),
            notes="Phase 3 test",
            items=items,
        )

    def test_multi_item_payloads_stay_aligned_and_invoice_starts_draft(self):
        invoice = create_estate_invoice(
            created_by=self.creator.user,
            payload=self._payload(
                [
                    {
                        "property_id": self.property_one.id,
                        "description": "First property",
                        "unit_price": Decimal("110000.00"),
                    },
                    {
                        "property_id": self.property_two.id,
                        "description": "Second property",
                        "unit_price": Decimal("220000.00"),
                    },
                ]
            ),
        )
        items = list(invoice.estate_invoice_items.order_by("id"))
        self.assertEqual(invoice.status, "draft")
        self.assertEqual(invoice.approvals.count(), 0)
        self.assertEqual(items[0].property_id, self.property_one.id)
        self.assertEqual(items[0].description, "First property")
        self.assertEqual(items[0].unit_price, Decimal("110000.00"))
        self.assertEqual(items[1].property_id, self.property_two.id)
        self.assertEqual(items[1].description, "Second property")
        self.assertEqual(items[1].unit_price, Decimal("220000.00"))
        self.assertEqual(invoice.subtotal, Decimal("330000.00"))

    def test_submit_assigns_approvers_reserves_inventory_and_uses_finance_bank(self):
        invoice = create_estate_invoice(
            created_by=self.creator.user,
            payload=self._payload([{"property_id": self.property_one.id}]),
        )
        invoice = submit_estate_invoice(invoice, submitted_by=self.creator.user)
        approvals = list(invoice.approvals.order_by("step"))
        self.assertEqual(approvals[0].assigned_to_id, self.manager.user_id)
        self.assertEqual(approvals[1].assigned_to_id, self.final.user_id)
        self.property_one.refresh_from_db()
        self.assertEqual(self.property_one.status, "reserved")
        self.assertEqual(invoice.bank_name, self.account.bank_name)
        self.assertEqual(invoice.account_number, self.account.account_number)
        self.assertEqual(invoice.account_name, self.account.account_name)
        self.assertNotIn("Placeholder", invoice.bank_name)

    def test_rejection_releases_invoice_reservation(self):
        invoice = create_estate_invoice(
            created_by=self.creator.user,
            payload=self._payload([{"property_id": self.property_three.id}]),
        )
        invoice = submit_estate_invoice(invoice, submitted_by=self.creator.user)
        invoice, should_email = decide_estate_invoice_approval(
            invoice,
            step=1,
            decision="rejected",
            comment="Reject",
            decided_by=self.manager.user,
        )
        self.assertFalse(should_email)
        self.assertEqual(invoice.status, "cancelled")
        self.property_three.refresh_from_db()
        self.assertEqual(self.property_three.status, "available")
        self.assertEqual(self.property_three.client_name, "")

    def test_payment_is_journal_backed_idempotent_and_sells_on_full_payment(self):
        invoice = create_estate_invoice(
            created_by=self.creator.user,
            payload=self._payload([{"property_id": self.property_one.id}]),
        )
        invoice = submit_estate_invoice(invoice, submitted_by=self.creator.user)
        invoice, _ = decide_estate_invoice_approval(
            invoice,
            step=1,
            decision="approved",
            comment="Manager approved",
            decided_by=self.manager.user,
        )
        invoice, should_email = decide_estate_invoice_approval(
            invoice,
            step=2,
            decision="approved",
            comment="Final approved",
            decided_by=self.final.user,
        )
        self.assertTrue(should_email)
        self.assertEqual(invoice.status, "sent")

        first_amount = Decimal("50000.00")
        invoice = record_estate_invoice_payment(
            invoice,
            amount=first_amount,
            recorded_by=self.creator.user,
            finance_account_id=self.account.id,
            payment_reference="RECEIPT-001",
        )
        self.assertEqual(invoice.amount_paid, first_amount)
        self.assertEqual(invoice.status, "partially_paid")
        self.assertEqual(
            JournalEntry.objects.filter(
                source_type="real_estate_payment",
                reference="RECEIPT-001",
                status=JournalEntry.STATUS.POSTED,
            ).count(),
            1,
        )

        invoice = record_estate_invoice_payment(
            invoice,
            amount=first_amount,
            recorded_by=self.creator.user,
            finance_account_id=self.account.id,
            payment_reference="RECEIPT-001",
        )
        self.assertEqual(invoice.amount_paid, first_amount)
        self.assertEqual(
            JournalEntry.objects.filter(
                source_type="real_estate_payment", reference="RECEIPT-001"
            ).count(),
            1,
        )

        with self.assertRaises(ValidationError):
            record_estate_invoice_payment(
                invoice,
                amount=invoice.balance + Decimal("1.00"),
                recorded_by=self.creator.user,
                finance_account_id=self.account.id,
                payment_reference="OVERPAY",
            )

        invoice = record_estate_invoice_payment(
            invoice,
            amount=invoice.balance,
            recorded_by=self.creator.user,
            finance_account_id=self.account.id,
            payment_reference="RECEIPT-002",
        )
        self.assertEqual(invoice.status, "paid")
        self.assertEqual(invoice.balance, Decimal("0.00"))
        self.property_one.refresh_from_db()
        self.assertEqual(self.property_one.status, "sold")
        self.assertEqual(self.property_one.owner_id, self.client_user.id)
        self.assertEqual(
            JournalEntry.objects.filter(
                source_type="real_estate_payment", status=JournalEntry.STATUS.POSTED
            ).count(),
            2,
        )
