from datetime import date, datetime
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import Client as DjangoClient, TestCase
from django.utils import timezone

from finance.models import (
    BankReconciliation,
    BankStatementLine,
    FinanceAccount,
    FixedAssetCategory,
    JournalEntry,
    LedgerAccount,
)
from finance.service import (
    add_bank_statement_lines,
    capitalize_fixed_asset,
    close_bank_reconciliation,
    create_bank_reconciliation,
    create_fixed_asset,
    create_manual_journal,
    discard_bank_reconciliation,
    dispose_fixed_asset,
    ensure_finance_account_ledger_account,
    match_bank_statement_line,
    post_expense_payment_journal,
    post_fixed_asset_depreciation,
    post_journal_entry,
    reconcile_bank_reconciliation,
    reconciliation_summary,
    reverse_journal_entry,
)
from services.models.expenses import Expense
from user.models.branch import Branch
from user.tests.helpers import RoleAPITestMixin


class AccountingSignoffFixTests(RoleAPITestMixin, TestCase):
    def setUp(self):
        self.client = DjangoClient()
        self.role = self.create_role(
            "FIN Signoff Tester",
            {
                "payments": ["list", "view", "create"],
                "bank_reconciliation": [
                    "create",
                    "view",
                    "list",
                    "update",
                    "match",
                    "reconcile",
                    "close",
                ],
                "fixed_asset_categories": [
                    "create",
                    "view",
                    "list",
                    "update",
                    "deactivate",
                ],
                "fixed_assets": [
                    "create",
                    "view",
                    "list",
                    "update",
                    "capitalize",
                    "depreciate",
                    "dispose",
                ],
                "journals": ["create", "view", "list", "update", "post", "reverse"],
                "general_ledger": ["view", "list"],
            },
        )
        self.employee = self.create_user_with_employee(
            "fin.signoff@test.com",
            "finsignoff",
            "EMP-FIN-SIGNOFF",
            role=self.role,
        )
        self.headers = self.auth_headers(self.employee)
        self.branch = Branch.objects.create(
            branch_name="FIN Signoff Enugu",
            branch_id="BR-FIN-SIGNOFF",
            country="Nigeria",
            state="Enugu",
            office_address="Finance signoff test office",
            contact_email="fin-signoff@test.com",
            contact_phone="+2348011111991",
        )
        self.finance_account = FinanceAccount.objects.create(
            account_type=FinanceAccount.ACCOUNT_TYPE.BANK,
            display_name="FIN Signoff Bank",
            currency="NGN",
            branch=self.branch,
            bank_name="Access Bank",
            account_number="9000112233",
            account_name="Bomach Group",
            opening_balance=Decimal("0.00"),
            created_by=self.employee.user,
        )
        self.bank_ledger = ensure_finance_account_ledger_account(
            self.finance_account,
            self.employee.user,
        )
        self.operating_expense = LedgerAccount.objects.get(
            system_role=LedgerAccount.SYSTEM_ROLE.OPERATING_EXPENSE
        )
        self.service_revenue = LedgerAccount.objects.get(
            system_role=LedgerAccount.SYSTEM_ROLE.SERVICE_REVENUE
        )

    def _bank_move(self, amount, money_in, day, reference=""):
        if money_in:
            lines = [
                {
                    "ledger_account_id": self.bank_ledger.id,
                    "debit": amount,
                    "credit": Decimal("0.00"),
                },
                {
                    "ledger_account_id": self.service_revenue.id,
                    "debit": Decimal("0.00"),
                    "credit": amount,
                },
            ]
        else:
            lines = [
                {
                    "ledger_account_id": self.operating_expense.id,
                    "debit": amount,
                    "credit": Decimal("0.00"),
                },
                {
                    "ledger_account_id": self.bank_ledger.id,
                    "debit": Decimal("0.00"),
                    "credit": amount,
                },
            ]
        entry = create_manual_journal(
            entry_date=day,
            currency="NGN",
            branch=self.branch,
            reference=reference,
            created_by=self.employee.user,
            lines=lines,
        )
        return post_journal_entry(entry, self.employee.user)

    def _category(self, life=12):
        return FixedAssetCategory.objects.create(
            code=f"SIGN-{life}",
            name=f"Signoff Assets {life}",
            asset_ledger_account=LedgerAccount.objects.get(code="1610"),
            accumulated_depreciation_ledger_account=LedgerAccount.objects.get(
                code="1690"
            ),
            depreciation_expense_ledger_account=LedgerAccount.objects.get(code="6300"),
            default_useful_life_months=life,
            default_residual_value_percent=Decimal("0.00"),
            created_by=self.employee.user,
        )

    def _capex(self, amount=Decimal("100.00"), paid_date=date(2026, 4, 1)):
        expense = Expense.objects.create(
            user=self.employee.user,
            branch=self.branch,
            finance_account=self.finance_account,
            date=paid_date,
            description="Signoff capital equipment purchase",
            amount=amount,
            cost_type=Expense.COST_TYPE.CAPITAL_EXPENDITURE,
            category=Expense.CATEGORY_CHOICES.EQUIPMENT,
            status=Expense.STATUS.PAID,
            paid_by=self.employee.user,
            paid_at=timezone.make_aware(
                datetime(paid_date.year, paid_date.month, paid_date.day, 12, 0, 0)
            ),
            payment_reference=f"SIGN-CAPEX-{amount}",
        )
        post_expense_payment_journal(expense, self.employee.user)
        return expense

    def test_account_book_balance_uses_posted_general_ledger_and_reversal(self):
        entry = self._bank_move(
            Decimal("100.00"),
            True,
            timezone.localdate(),
            "SIGN-BAL-100",
        )
        response = self.client.get(
            f"/api/v1/finance/accounts/{self.finance_account.id}/balance",
            **self.headers,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["book_balance"], "100.00")

        reverse_journal_entry(entry, self.employee.user)
        response = self.client.get(
            f"/api/v1/finance/accounts/{self.finance_account.id}/balance",
            **self.headers,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["book_balance"], "0.00")

    def test_fixed_asset_disposal_proceeds_are_in_account_book_balance(self):
        expense = self._capex(Decimal("100.00"))
        category = self._category(12)
        asset = create_fixed_asset(
            category=category,
            source_expense=expense,
            name="Signoff Disposal Asset",
            acquisition_date=expense.date,
            acquisition_cost=Decimal("100.00"),
            created_by=self.employee.user,
        )
        asset, _, _ = capitalize_fixed_asset(
            asset,
            self.employee.user,
            capitalization_date=date(2026, 4, 1),
        )
        dispose_fixed_asset(
            asset,
            disposal_date=date(2026, 5, 1),
            proceeds=Decimal("120.00"),
            finance_account=self.finance_account,
            reference="SIGN-SALE-120",
            disposed_by=self.employee.user,
        )

        response = self.client.get(
            f"/api/v1/finance/accounts/{self.finance_account.id}/balance?as_of=2026-05-01",
            **self.headers,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["book_balance"], "20.00")

    def test_branchless_journal_cannot_use_branch_specific_bank_ledger(self):
        with self.assertRaises(ValidationError):
            create_manual_journal(
                entry_date=timezone.localdate(),
                currency="NGN",
                branch=None,
                created_by=self.employee.user,
                lines=[
                    {
                        "ledger_account_id": self.operating_expense.id,
                        "debit": Decimal("10.00"),
                        "credit": Decimal("0.00"),
                    },
                    {
                        "ledger_account_id": self.bank_ledger.id,
                        "debit": Decimal("0.00"),
                        "credit": Decimal("10.00"),
                    },
                ],
            )

    def test_first_reconciliation_ignores_historical_items_already_in_opening_balance(
        self,
    ):
        self._bank_move(Decimal("100.00"), True, date(2026, 1, 5), "OLD-IN")
        self._bank_move(Decimal("20.00"), False, date(2026, 1, 6), "OLD-OUT")
        current = self._bank_move(Decimal("50.00"), True, date(2026, 8, 5), "AUG-IN")

        reconciliation = create_bank_reconciliation(
            finance_account=self.finance_account,
            statement_start_date=date(2026, 8, 1),
            statement_end_date=date(2026, 8, 19),
            statement_opening_balance=Decimal("80.00"),
            statement_closing_balance=Decimal("130.00"),
            created_by=self.employee.user,
        )
        statement_line = add_bank_statement_lines(
            reconciliation,
            [
                {
                    "transaction_date": date(2026, 8, 5),
                    "reference": "AUG-IN",
                    "amount": Decimal("50.00"),
                    "direction": BankStatementLine.DIRECTION.CREDIT,
                    "sequence_number": 1,
                }
            ],
        )[0]
        match_bank_statement_line(
            reconciliation=reconciliation,
            bank_statement_line=statement_line,
            journal_line=current.lines.get(ledger_account=self.bank_ledger),
            matched_amount=Decimal("50.00"),
            matched_by=self.employee.user,
        )

        summary = reconciliation_summary(reconciliation)
        self.assertEqual(summary["outstanding_gl_net"], Decimal("0.00"))
        self.assertEqual(summary["unexplained_difference"], Decimal("0.00"))
        self.assertEqual(
            reconcile_bank_reconciliation(reconciliation, self.employee.user).status,
            BankReconciliation.STATUS.RECONCILED,
        )

    def test_old_outstanding_item_can_clear_in_first_reconciliation(self):
        old = self._bank_move(
            Decimal("100.00"), True, date(2026, 1, 5), "OLD-OUTSTANDING"
        )
        reconciliation = create_bank_reconciliation(
            finance_account=self.finance_account,
            statement_start_date=date(2026, 8, 1),
            statement_end_date=date(2026, 8, 19),
            statement_opening_balance=Decimal("0.00"),
            statement_closing_balance=Decimal("100.00"),
            created_by=self.employee.user,
        )
        statement_line = add_bank_statement_lines(
            reconciliation,
            [
                {
                    "transaction_date": date(2026, 8, 5),
                    "reference": "OLD-OUTSTANDING",
                    "amount": Decimal("100.00"),
                    "direction": BankStatementLine.DIRECTION.CREDIT,
                    "sequence_number": 1,
                }
            ],
        )[0]
        match_bank_statement_line(
            reconciliation=reconciliation,
            bank_statement_line=statement_line,
            journal_line=old.lines.get(ledger_account=self.bank_ledger),
            matched_amount=Decimal("100.00"),
            matched_by=self.employee.user,
        )
        summary = reconciliation_summary(reconciliation)
        self.assertEqual(summary["outstanding_gl_net"], Decimal("0.00"))
        self.assertEqual(summary["unexplained_difference"], Decimal("0.00"))

    def test_only_one_draft_exists_and_draft_can_be_discarded(self):
        first = create_bank_reconciliation(
            finance_account=self.finance_account,
            statement_start_date=date(2026, 1, 1),
            statement_end_date=date(2026, 1, 31),
            statement_opening_balance=Decimal("0.00"),
            statement_closing_balance=Decimal("0.00"),
            created_by=self.employee.user,
        )
        add_bank_statement_lines(
            first,
            [
                {
                    "transaction_date": date(2026, 1, 10),
                    "amount": Decimal("1.00"),
                    "direction": BankStatementLine.DIRECTION.CREDIT,
                    "sequence_number": 1,
                }
            ],
        )
        with self.assertRaises(ValidationError):
            create_bank_reconciliation(
                finance_account=self.finance_account,
                statement_start_date=date(2026, 2, 1),
                statement_end_date=date(2026, 2, 28),
                statement_opening_balance=Decimal("0.00"),
                statement_closing_balance=Decimal("0.00"),
                created_by=self.employee.user,
            )

        discarded_id = discard_bank_reconciliation(first)
        self.assertFalse(BankReconciliation.objects.filter(id=discarded_id).exists())

        second = create_bank_reconciliation(
            finance_account=self.finance_account,
            statement_start_date=date(2026, 2, 1),
            statement_end_date=date(2026, 2, 28),
            statement_opening_balance=Decimal("0.00"),
            statement_closing_balance=Decimal("0.00"),
            created_by=self.employee.user,
        )
        self.assertEqual(second.status, BankReconciliation.STATUS.DRAFT)

    def test_reconciliation_periods_cannot_be_backfilled_behind_later_history(self):
        later = create_bank_reconciliation(
            finance_account=self.finance_account,
            statement_start_date=date(2026, 7, 1),
            statement_end_date=date(2026, 7, 31),
            statement_opening_balance=Decimal("0.00"),
            statement_closing_balance=Decimal("0.00"),
            created_by=self.employee.user,
        )
        reconcile_bank_reconciliation(later, self.employee.user)
        with self.assertRaises(ValidationError):
            create_bank_reconciliation(
                finance_account=self.finance_account,
                statement_start_date=date(2026, 6, 1),
                statement_end_date=date(2026, 6, 30),
                statement_opening_balance=Decimal("0.00"),
                statement_closing_balance=Decimal("0.00"),
                created_by=self.employee.user,
            )

    def test_closed_reconciliation_blocks_backdated_bank_posting(self):
        reconciliation = create_bank_reconciliation(
            finance_account=self.finance_account,
            statement_start_date=date(2026, 1, 1),
            statement_end_date=date(2026, 1, 31),
            statement_opening_balance=Decimal("0.00"),
            statement_closing_balance=Decimal("0.00"),
            created_by=self.employee.user,
        )
        reconciliation = reconcile_bank_reconciliation(
            reconciliation,
            self.employee.user,
        )
        close_bank_reconciliation(reconciliation, self.employee.user)

        draft = create_manual_journal(
            entry_date=date(2026, 1, 15),
            currency="NGN",
            branch=self.branch,
            created_by=self.employee.user,
            lines=[
                {
                    "ledger_account_id": self.bank_ledger.id,
                    "debit": Decimal("10.00"),
                    "credit": Decimal("0.00"),
                },
                {
                    "ledger_account_id": self.service_revenue.id,
                    "debit": Decimal("0.00"),
                    "credit": Decimal("10.00"),
                },
            ],
        )
        with self.assertRaises(ValidationError):
            post_journal_entry(draft, self.employee.user)

        later = create_manual_journal(
            entry_date=date(2026, 2, 1),
            currency="NGN",
            branch=self.branch,
            created_by=self.employee.user,
            lines=[
                {
                    "ledger_account_id": self.bank_ledger.id,
                    "debit": Decimal("10.00"),
                    "credit": Decimal("0.00"),
                },
                {
                    "ledger_account_id": self.service_revenue.id,
                    "debit": Decimal("0.00"),
                    "credit": Decimal("10.00"),
                },
            ],
        )
        self.assertEqual(
            post_journal_entry(later, self.employee.user).status,
            JournalEntry.STATUS.POSTED,
        )

    def test_depreciation_must_post_next_month_without_skipping(self):
        expense = self._capex(Decimal("120.00"))
        category = self._category(12)
        asset = create_fixed_asset(
            category=category,
            source_expense=expense,
            name="Monthly Depreciation Asset",
            acquisition_date=date(2026, 4, 1),
            acquisition_cost=Decimal("120.00"),
            created_by=self.employee.user,
        )
        asset, _, _ = capitalize_fixed_asset(
            asset,
            self.employee.user,
            capitalization_date=date(2026, 4, 1),
        )

        with self.assertRaises(ValidationError):
            post_fixed_asset_depreciation(
                asset,
                date(2026, 7, 31),
                self.employee.user,
            )

        post_fixed_asset_depreciation(
            asset,
            date(2026, 5, 31),
            self.employee.user,
        )
        asset.refresh_from_db()
        with self.assertRaises(ValidationError):
            post_fixed_asset_depreciation(
                asset,
                date(2026, 7, 31),
                self.employee.user,
            )

        _, journal, created = post_fixed_asset_depreciation(
            asset,
            date(2026, 6, 30),
            self.employee.user,
        )
        self.assertTrue(created)
        self.assertEqual(journal.entry_date, date(2026, 6, 30))

    def test_residual_value_equal_to_cost_is_rejected(self):
        expense = self._capex(Decimal("100.00"))
        category = self._category(12)
        with self.assertRaises(ValidationError):
            create_fixed_asset(
                category=category,
                source_expense=expense,
                name="Zero Depreciable Asset",
                acquisition_date=expense.date,
                acquisition_cost=Decimal("100.00"),
                residual_value=Decimal("100.00"),
                created_by=self.employee.user,
            )
