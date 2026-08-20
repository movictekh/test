from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import Client as DjangoClient
from django.test import TestCase
from django.utils import timezone

from finance.models import FinanceAccount, FinanceVendor, JournalEntry, JournalLine, LedgerAccount, VendorBill
from finance.service import (
    create_manual_journal,
    ensure_finance_account_ledger_account,
    map_finance_account_ledger,
    post_client_payment_journal,
    post_journal_entry,
    post_opening_balance_journal,
    post_vendor_bill_payment_journal,
    reverse_journal_entry,
)
from services.models.payment import Invoice, Payment
from services.models.service import Service, ServiceCategory
from user.models.branch import Branch
from user.models.client import Client as CustomerClient
from user.models.user import User
from user.tests.helpers import RoleAPITestMixin


class AccountingGLPassTests(RoleAPITestMixin, TestCase):
    def setUp(self):
        self.client = DjangoClient()
        self.role = self.create_role(
            "FIN AT2-3 Accounting Tester",
            {
                "chart_of_accounts": ["create", "view", "list", "update", "deactivate"],
                "journals": ["create", "view", "list", "update", "post", "reverse"],
                "general_ledger": ["view", "list"],
                "payments": ["create", "view", "list"],
            },
        )
        self.employee = self.create_user_with_employee("fin.at23@test.com", "finat23", "EMP-FIN-AT23", role=self.role)
        self.headers = self.auth_headers(self.employee)
        self.branch = Branch.objects.create(
            branch_name="FIN AT23 Enugu", branch_id="BR-FIN-AT23", country="Nigeria", state="Enugu",
            office_address="Accounting test office", contact_email="fin-at23@test.com", contact_phone="+2348011111188",
        )
        self.finance_account = FinanceAccount.objects.create(
            account_type=FinanceAccount.ACCOUNT_TYPE.BANK,
            display_name="FIN AT23 Test Bank", currency="NGN", branch=self.branch,
            bank_name="GTBank", account_number="7788990011", account_name="Bomach Group",
            opening_balance=Decimal("1000.00"), opening_balance_date=timezone.localdate(), created_by=self.employee.user,
        )

    def _bank(self):
        return ensure_finance_account_ledger_account(self.finance_account, self.employee.user)

    def test_canonical_chart_is_seeded(self):
        roles = set(LedgerAccount.objects.exclude(system_role__isnull=True).values_list("system_role", flat=True))
        for role in ["service_revenue", "operating_expense", "statutory_payable", "employee_receivables", "opening_balance_equity"]:
            self.assertIn(role, roles)
        self.assertTrue(LedgerAccount.objects.filter(code="1100", is_postable=False).exists())

    def test_finance_account_gets_dedicated_asset_ledger(self):
        ledger = self._bank(); self.finance_account.refresh_from_db()
        self.assertEqual(self.finance_account.ledger_account_id, ledger.id)
        self.assertEqual(ledger.account_type, LedgerAccount.ACCOUNT_TYPE.ASSET)
        self.assertTrue(ledger.is_postable)

    def test_opening_balance_posts_once_and_locks_historical_identity(self):
        first, created1 = post_opening_balance_journal(self.finance_account, self.employee.user)
        second, created2 = post_opening_balance_journal(self.finance_account, self.employee.user)
        self.assertTrue(created1); self.assertFalse(created2); self.assertEqual(first.id, second.id)
        self.assertEqual(first.total_debit, Decimal("1000.00")); self.assertEqual(first.total_credit, Decimal("1000.00"))
        self.finance_account.opening_balance = Decimal("999.00")
        with self.assertRaises(ValidationError): self.finance_account.save()

    def test_parent_must_be_non_postable_and_hierarchy_cannot_cycle(self):
        parent = LedgerAccount.objects.create(code="6990", name="Temporary Parent", account_type="expense", normal_balance="debit", is_postable=False, created_by=self.employee.user)
        child = LedgerAccount.objects.create(code="6991", name="Temporary Child", account_type="expense", normal_balance="debit", parent=parent, is_postable=False, created_by=self.employee.user)
        parent.parent = child
        with self.assertRaises(ValidationError): parent.save()

    def test_unbalanced_manual_journal_cannot_post(self):
        revenue = LedgerAccount.objects.get(system_role="service_revenue"); bank = self._bank()
        entry = create_manual_journal(entry_date=timezone.localdate(), currency="NGN", branch=self.branch, created_by=self.employee.user, lines=[
            {"ledger_account_id": bank.id, "debit": Decimal("100.00"), "credit": Decimal("0.00")},
            {"ledger_account_id": revenue.id, "debit": Decimal("0.00"), "credit": Decimal("90.00")},
        ])
        with self.assertRaises(ValidationError): post_journal_entry(entry, self.employee.user)
        entry.refresh_from_db(); self.assertEqual(entry.status, JournalEntry.STATUS.DRAFT)

    def test_posted_journal_and_lines_are_immutable(self):
        expense = LedgerAccount.objects.get(system_role="operating_expense"); bank = self._bank()
        entry = create_manual_journal(entry_date=timezone.localdate(), currency="NGN", branch=self.branch, created_by=self.employee.user, lines=[
            {"ledger_account_id": expense.id, "debit": Decimal("25.00"), "credit": Decimal("0.00")},
            {"ledger_account_id": bank.id, "debit": Decimal("0.00"), "credit": Decimal("25.00")},
        ])
        posted = post_journal_entry(entry, self.employee.user)
        posted.memo = "changed"
        with self.assertRaises(ValidationError): posted.save()
        line = posted.lines.first(); line.description = "changed"
        with self.assertRaises(ValidationError): line.save()

    def test_status_cannot_bypass_posting_service(self):
        expense = LedgerAccount.objects.get(system_role="operating_expense"); bank = self._bank()
        entry = create_manual_journal(entry_date=timezone.localdate(), currency="NGN", branch=self.branch, created_by=self.employee.user, lines=[
            {"ledger_account_id": expense.id, "debit": Decimal("5.00"), "credit": Decimal("0.00")},
            {"ledger_account_id": bank.id, "debit": Decimal("0.00"), "credit": Decimal("5.00")},
        ])
        entry.status = JournalEntry.STATUS.POSTED; entry.posted_at = timezone.now()
        with self.assertRaises(ValidationError): entry.save()

    def test_reversal_swaps_debits_and_credits(self):
        expense = LedgerAccount.objects.get(system_role="operating_expense"); bank = self._bank()
        entry = create_manual_journal(entry_date=timezone.localdate(), currency="NGN", branch=self.branch, created_by=self.employee.user, lines=[
            {"ledger_account_id": expense.id, "debit": Decimal("250.00"), "credit": Decimal("0.00")},
            {"ledger_account_id": bank.id, "debit": Decimal("0.00"), "credit": Decimal("250.00")},
        ])
        posted = post_journal_entry(entry, self.employee.user); reversal = reverse_journal_entry(posted, self.employee.user)
        self.assertEqual(reversal.entry_type, JournalEntry.ENTRY_TYPE.REVERSAL)
        self.assertEqual(reversal.total_debit, Decimal("250.00")); self.assertEqual(reversal.total_credit, Decimal("250.00"))
        self.assertEqual(reversal.reversal_of_id, posted.id)

    def test_cash_ledger_rejects_wrong_currency_journal(self):
        bank = self._bank(); expense = LedgerAccount.objects.get(system_role="operating_expense")
        with self.assertRaises(ValidationError):
            create_manual_journal(entry_date=timezone.localdate(), currency="USD", branch=self.branch, created_by=self.employee.user, lines=[
                {"ledger_account_id": expense.id, "debit": Decimal("10.00"), "credit": Decimal("0.00")},
                {"ledger_account_id": bank.id, "debit": Decimal("0.00"), "credit": Decimal("10.00")},
            ])

    def test_vendor_bill_posting_is_idempotent_and_splits_wht(self):
        vendor = FinanceVendor.objects.create(name="FIN AT23 Vendor", created_by=self.employee.user)
        bill = VendorBill.objects.create(
            vendor=vendor, branch=self.branch, finance_account=self.finance_account, category="Testing", description="GL vendor bill",
            gross_amount=Decimal("1000.00"), withholding_tax=Decimal("50.00"), bill_date=timezone.localdate(), due_date=timezone.localdate(),
            status=VendorBill.STATUS.PAID, paid_at=timezone.now(), payment_reference="AT23-VENDOR-001", paid_by=self.employee.user, created_by=self.employee.user,
        )
        first, c1 = post_vendor_bill_payment_journal(bill, self.employee.user); second, c2 = post_vendor_bill_payment_journal(bill, self.employee.user)
        self.assertTrue(c1); self.assertFalse(c2); self.assertEqual(first.id, second.id)
        self.assertEqual(first.total_debit, Decimal("1000.00")); self.assertEqual(first.total_credit, Decimal("1000.00"))
        self.assertEqual(first.lines.get(ledger_account__system_role="statutory_payable").credit, Decimal("50.00"))

    def test_manual_journal_api_posts_and_trial_balance_balances(self):
        bank = self._bank(); expense = LedgerAccount.objects.get(system_role="operating_expense")
        response = self.client.post("/api/v1/finance/journals", data={
            "entry_date": timezone.localdate().isoformat(), "currency": "NGN", "branch_id": self.branch.id, "reference": "API-JRN-1",
            "lines": [
                {"ledger_account_id": expense.id, "debit": "75.00", "credit": "0.00"},
                {"ledger_account_id": bank.id, "debit": "0.00", "credit": "75.00"},
            ],
        }, content_type="application/json", **self.headers)
        self.assertEqual(response.status_code, 201)
        journal_id = response.json()["id"]
        posted = self.client.post(f"/api/v1/finance/journals/{journal_id}/post", **self.headers)
        self.assertEqual(posted.status_code, 200); self.assertEqual(posted.json()["status"], "posted")
        trial = self.client.get("/api/v1/finance/trial-balance?currency=NGN", **self.headers)
        self.assertEqual(trial.status_code, 200); self.assertTrue(trial.json()["balanced"])
        self.assertEqual(trial.json()["total_debit"], "75.00"); self.assertEqual(trial.json()["total_credit"], "75.00")

    def test_finance_account_api_posts_dated_opening_balance(self):
        response = self.client.post("/api/v1/finance/accounts", data={
            "account_type": "bank", "display_name": "Opening API Bank", "currency": "NGN", "branch_id": self.branch.id,
            "bank_name": "Access Bank", "account_number": "6677889900", "account_name": "Bomach Group",
            "opening_balance": "300.00", "opening_balance_date": timezone.localdate().isoformat(),
        }, content_type="application/json", **self.headers)
        self.assertEqual(response.status_code, 201)
        account_id = response.json()["id"]
        self.assertTrue(JournalEntry.objects.filter(source_type="finance_account", source_id=str(account_id), source_event="opening_balance", status="posted").exists())

    def test_parent_with_children_cannot_be_made_postable(self):
        parent = LedgerAccount.objects.get(code="6000")
        self.assertTrue(parent.children.exists())
        parent.is_postable = True
        with self.assertRaises(ValidationError):
            parent.save()

    def test_system_role_rejects_wrong_account_type(self):
        revenue = LedgerAccount.objects.get(system_role=LedgerAccount.SYSTEM_ROLE.SERVICE_REVENUE)
        revenue.account_type = LedgerAccount.ACCOUNT_TYPE.ASSET
        revenue.normal_balance = LedgerAccount.NORMAL_BALANCE.DEBIT
        with self.assertRaises(ValidationError):
            revenue.save()

    def test_finance_account_mapping_must_stay_inside_cash_bank_tree(self):
        unrelated_asset = LedgerAccount.objects.create(
            code="1999",
            name="Unrelated Asset",
            account_type=LedgerAccount.ACCOUNT_TYPE.ASSET,
            normal_balance=LedgerAccount.NORMAL_BALANCE.DEBIT,
            is_postable=True,
            created_by=self.employee.user,
        )
        with self.assertRaises(ValidationError):
            map_finance_account_ledger(self.finance_account, unrelated_asset, self.employee.user)

    def test_reversal_cannot_predate_original(self):
        expense = LedgerAccount.objects.get(system_role="operating_expense")
        bank = self._bank()
        original_date = timezone.localdate()
        entry = create_manual_journal(
            entry_date=original_date,
            currency="NGN",
            branch=self.branch,
            created_by=self.employee.user,
            lines=[
                {"ledger_account_id": expense.id, "debit": Decimal("20.00"), "credit": Decimal("0.00")},
                {"ledger_account_id": bank.id, "debit": Decimal("0.00"), "credit": Decimal("20.00")},
            ],
        )
        posted = post_journal_entry(entry, self.employee.user)
        with self.assertRaises(ValidationError):
            reverse_journal_entry(posted, self.employee.user, entry_date=original_date - timedelta(days=1))

    def test_partial_payment_tax_rounding_reconciles_to_invoice_tax(self):
        customer_user = User.objects.create_user(
            email="tax.rounding@test.com", username="taxrounding", password="password123"
        )
        customer = CustomerClient.objects.create(
            user=customer_user, phone="+2348011111199", company_name="Tax Rounding Ltd"
        )
        category, _ = ServiceCategory.objects.get_or_create(
            name=ServiceCategory.CategoryChoices.CONSTRUCTION,
        )
        service = Service.objects.create(
            name="Tax Rounding Service",
            category=category,
            description="Tax allocation test",
            base_price=Decimal("1.15"),
            delivery_time="1 day",
            status="active",
            created_by=self.employee.user,
        )
        invoice = Invoice.objects.create(
            client=customer,
            service=service,
            issue_date=timezone.localdate(),
            due_date=timezone.localdate(),
            subtotal=Decimal("1.15"),
            tax_rate=Decimal("7.50"),
            tax_amount=Decimal("0.00"),
            total_amount=Decimal("0.00"),
            amount_paid=Decimal("0.00"),
            status="sent",
            created_by=self.employee.user,
        )
        invoice.refresh_from_db()
        self.assertEqual(invoice.tax_amount, Decimal("0.09"))
        self.assertEqual(invoice.total_amount, Decimal("1.24"))

        entries = []
        for amount in [Decimal("0.62"), Decimal("0.62")]:
            payment = Payment.objects.create(
                invoice=invoice,
                amount=amount,
                payment_method="bank_transfer",
                payment_date=timezone.localdate(),
                finance_account=self.finance_account,
                created_by=self.employee.user,
            )
            entry, created = post_client_payment_journal(payment, self.employee.user)
            self.assertTrue(created)
            entries.append(entry)
            invoice.refresh_from_db()

        tax_credit = sum(
            (
                line.credit
                for entry in entries
                for line in entry.lines.filter(
                    ledger_account__system_role=LedgerAccount.SYSTEM_ROLE.STATUTORY_PAYABLE
                )
            ),
            Decimal("0.00"),
        )
        self.assertEqual(tax_credit, invoice.tax_amount)
