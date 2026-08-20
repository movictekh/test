from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import Client as DjangoClient
from django.test import TestCase
from django.utils import timezone

from finance.models import FinanceSettings, JournalEntry, LedgerAccount
from finance.service.accounting import create_manual_journal, post_journal_entry
from finance.service.reporting import (
    balance_sheet,
    expense_report,
    financial_year_start,
    profit_and_loss,
    revenue_report,
)
from user.api import api
from user.models.branch import Branch
from user.models.company import CompanyPreferences
from user.models.role import PERMISSIONS_MAP
from user.tests.helpers import RoleAPITestMixin


class FinanceSettingsReportsTests(RoleAPITestMixin, TestCase):
    def setUp(self):
        self.client = DjangoClient()
        self.role = self.create_role(
            "FIN IC1-2 Tester",
            {
                "finance_settings": ["view", "update"],
                "financial_reports": ["view"],
                "journals": ["create", "view", "list", "update", "post", "reverse"],
            },
        )
        self.employee = self.create_user_with_employee(
            "fin.ic12@test.com",
            "finic12",
            "EMP-FIN-IC12",
            role=self.role,
        )
        self.headers = self.auth_headers(self.employee)
        self.branch = Branch.objects.create(
            branch_name="FIN IC Lagos",
            branch_id="BR-FIN-IC12",
            country="Nigeria",
            state="Lagos",
            office_address="Finance intelligence test office",
            contact_email="fin-ic12@test.com",
            contact_phone="+2348011111299",
        )

        asset_parent = LedgerAccount.objects.get(code="1000")
        self.asset = LedgerAccount.objects.create(
            code="1998",
            name="IC Report Test Asset",
            account_type=LedgerAccount.ACCOUNT_TYPE.ASSET,
            normal_balance=LedgerAccount.NORMAL_BALANCE.DEBIT,
            parent=asset_parent,
            is_postable=True,
            created_by=self.employee.user,
        )
        self.contra_asset = LedgerAccount.objects.create(
            code="1999",
            name="IC Report Test Contra Asset",
            account_type=LedgerAccount.ACCOUNT_TYPE.ASSET,
            normal_balance=LedgerAccount.NORMAL_BALANCE.CREDIT,
            parent=asset_parent,
            is_postable=True,
            created_by=self.employee.user,
        )
        self.revenue = LedgerAccount.objects.get(system_role="service_revenue")
        self.expense = LedgerAccount.objects.get(system_role="operating_expense")
        self.depreciation_expense = LedgerAccount.objects.get(code="6300")

    def _post(self, entry_date, lines, *, currency="NGN", branch=None):
        entry = create_manual_journal(
            entry_date=entry_date,
            currency=currency,
            branch=branch or self.branch,
            created_by=self.employee.user,
            lines=lines,
        )
        return post_journal_entry(entry, self.employee.user)

    def _seed_report_activity(self, entry_date=None):
        entry_date = entry_date or timezone.localdate()

        self._post(
            entry_date,
            [
                {
                    "ledger_account_id": self.asset.id,
                    "debit": Decimal("1000.00"),
                    "credit": Decimal("0.00"),
                },
                {
                    "ledger_account_id": self.revenue.id,
                    "debit": Decimal("0.00"),
                    "credit": Decimal("1000.00"),
                },
            ],
        )
        self._post(
            entry_date,
            [
                {
                    "ledger_account_id": self.expense.id,
                    "debit": Decimal("200.00"),
                    "credit": Decimal("0.00"),
                },
                {
                    "ledger_account_id": self.asset.id,
                    "debit": Decimal("0.00"),
                    "credit": Decimal("200.00"),
                },
            ],
        )
        self._post(
            entry_date,
            [
                {
                    "ledger_account_id": self.depreciation_expense.id,
                    "debit": Decimal("100.00"),
                    "credit": Decimal("0.00"),
                },
                {
                    "ledger_account_id": self.contra_asset.id,
                    "debit": Decimal("0.00"),
                    "credit": Decimal("100.00"),
                },
            ],
        )

    def test_finance_settings_is_singleton(self):
        settings = FinanceSettings.get_settings()
        self.assertEqual(settings.pk, 1)

        with self.assertRaises(ValidationError):
            FinanceSettings.objects.create(journal_prefix="ALT")

    def test_close_date_is_monotonic_and_not_future(self):
        settings = FinanceSettings.get_settings()
        settings.closed_through_date = timezone.localdate() - timedelta(days=10)
        settings.save()

        settings.closed_through_date = timezone.localdate() - timedelta(days=11)
        with self.assertRaises(ValidationError):
            settings.save()

        settings.refresh_from_db()
        settings.closed_through_date = None
        with self.assertRaises(ValidationError):
            settings.save()

        settings.refresh_from_db()
        settings.closed_through_date = timezone.localdate() + timedelta(days=1)
        with self.assertRaises(ValidationError):
            settings.save()

    def test_journal_prefix_applies_only_to_new_journals(self):
        settings = FinanceSettings.get_settings()
        first = create_manual_journal(
            entry_date=timezone.localdate(),
            currency="NGN",
            branch=self.branch,
            created_by=self.employee.user,
            lines=[
                {
                    "ledger_account_id": self.asset.id,
                    "debit": Decimal("1.00"),
                    "credit": Decimal("0.00"),
                },
                {
                    "ledger_account_id": self.revenue.id,
                    "debit": Decimal("0.00"),
                    "credit": Decimal("1.00"),
                },
            ],
        )
        self.assertTrue(first.journal_number.startswith("JRN-"))

        settings.journal_prefix = "FIN-JRN"
        settings.save()

        second = create_manual_journal(
            entry_date=timezone.localdate(),
            currency="NGN",
            branch=self.branch,
            created_by=self.employee.user,
            lines=[
                {
                    "ledger_account_id": self.asset.id,
                    "debit": Decimal("2.00"),
                    "credit": Decimal("0.00"),
                },
                {
                    "ledger_account_id": self.revenue.id,
                    "debit": Decimal("0.00"),
                    "credit": Decimal("2.00"),
                },
            ],
        )
        self.assertTrue(second.journal_number.startswith("FIN-JRN-"))
        self.assertTrue(first.journal_number.startswith("JRN-"))

    def test_closed_books_block_posting_but_later_date_posts(self):
        close_date = timezone.localdate() - timedelta(days=1)
        settings = FinanceSettings.get_settings()
        settings.closed_through_date = close_date
        settings.save()

        blocked = create_manual_journal(
            entry_date=close_date,
            currency="NGN",
            branch=self.branch,
            created_by=self.employee.user,
            lines=[
                {
                    "ledger_account_id": self.asset.id,
                    "debit": Decimal("10.00"),
                    "credit": Decimal("0.00"),
                },
                {
                    "ledger_account_id": self.revenue.id,
                    "debit": Decimal("0.00"),
                    "credit": Decimal("10.00"),
                },
            ],
        )
        with self.assertRaises(ValidationError):
            post_journal_entry(blocked, self.employee.user)

        allowed = create_manual_journal(
            entry_date=timezone.localdate(),
            currency="NGN",
            branch=self.branch,
            created_by=self.employee.user,
            lines=[
                {
                    "ledger_account_id": self.asset.id,
                    "debit": Decimal("11.00"),
                    "credit": Decimal("0.00"),
                },
                {
                    "ledger_account_id": self.revenue.id,
                    "debit": Decimal("0.00"),
                    "credit": Decimal("11.00"),
                },
            ],
        )
        post_journal_entry(allowed, self.employee.user)
        allowed.refresh_from_db()
        self.assertEqual(allowed.status, JournalEntry.STATUS.POSTED)

    def test_profit_and_loss_uses_posted_journal_lines_only(self):
        today = timezone.localdate()
        self._seed_report_activity(today)

        draft = create_manual_journal(
            entry_date=today,
            currency="NGN",
            branch=self.branch,
            created_by=self.employee.user,
            lines=[
                {
                    "ledger_account_id": self.asset.id,
                    "debit": Decimal("9000.00"),
                    "credit": Decimal("0.00"),
                },
                {
                    "ledger_account_id": self.revenue.id,
                    "debit": Decimal("0.00"),
                    "credit": Decimal("9000.00"),
                },
            ],
        )
        self.assertEqual(draft.status, JournalEntry.STATUS.DRAFT)

        report = profit_and_loss(
            date_from=today,
            date_to=today,
            currency="NGN",
        )
        self.assertEqual(report["total_revenue"], Decimal("1000.00"))
        self.assertEqual(report["total_expenses"], Decimal("300.00"))
        self.assertEqual(report["net_profit"], Decimal("700.00"))

    def test_balance_sheet_treats_contra_asset_as_reduction(self):
        today = timezone.localdate()
        self._seed_report_activity(today)

        report = balance_sheet(as_of=today, currency="NGN")
        self.assertEqual(report["total_assets"], Decimal("700.00"))
        self.assertEqual(report["cumulative_earnings"], Decimal("700.00"))
        self.assertEqual(report["total_equity"], Decimal("700.00"))
        self.assertEqual(report["equation_difference"], Decimal("0.00"))
        self.assertTrue(report["balanced"])

        contra_row = next(
            row
            for row in report["assets"]
            if row["ledger_account_id"] == self.contra_asset.id
        )
        self.assertEqual(contra_row["amount"], Decimal("-100.00"))

    def test_revenue_and_expense_reports_follow_accounting_types(self):
        today = timezone.localdate()
        self._seed_report_activity(today)

        revenue = revenue_report(
            date_from=today,
            date_to=today,
            currency="NGN",
        )
        expenses = expense_report(
            date_from=today,
            date_to=today,
            currency="NGN",
        )

        self.assertEqual(revenue["account_type"], LedgerAccount.ACCOUNT_TYPE.REVENUE)
        self.assertEqual(revenue["total"], Decimal("1000.00"))
        self.assertEqual(expenses["account_type"], LedgerAccount.ACCOUNT_TYPE.EXPENSE)
        self.assertEqual(expenses["total"], Decimal("300.00"))

    def test_default_period_uses_configured_financial_year(self):
        settings = FinanceSettings.get_settings()
        settings.financial_year_start_month = 4
        settings.save()

        today = timezone.localdate()
        report = profit_and_loss(currency="NGN")

        self.assertEqual(
            report["date_from"],
            financial_year_start(today, 4),
        )
        self.assertEqual(report["date_to"], today)

    def test_default_currency_comes_from_company_preferences(self):
        preferences = CompanyPreferences.get_settings()
        preferences.default_currency = "USD"
        preferences.save()

        report = profit_and_loss()
        self.assertEqual(report["currency"], "USD")

    def test_permissions_and_public_api_are_registered(self):
        self.assertEqual(PERMISSIONS_MAP["finance_settings"], ["view", "update"])
        self.assertEqual(PERMISSIONS_MAP["financial_reports"], ["view", "export"])

        schema = api.get_openapi_schema()
        paths = schema.get("paths", {})

        expected_suffixes = {
            "/finance/settings",
            "/finance/reports/profit-and-loss",
            "/finance/reports/balance-sheet",
            "/finance/reports/revenue",
            "/finance/reports/expenses",
        }
        actual_paths = set(paths)

        for suffix in expected_suffixes:
            self.assertTrue(
                any(path.endswith(suffix) for path in actual_paths),
                msg=f"Missing public API path ending in {suffix}",
            )

    def test_settings_api_exposes_company_currency_and_updates_policy(self):
        preferences = CompanyPreferences.get_settings()
        preferences.default_currency = "NGN"
        preferences.save()

        response = self.client.get(
            "/api/v1/finance/settings",
            **self.headers,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["default_currency"], "NGN")

        response = self.client.patch(
            "/api/v1/finance/settings",
            data={
                "financial_year_start_month": 7,
                "journal_prefix": "FIN",
                "draft_journal_warning_days": 14,
                "large_manual_journal_review_threshold": "5000000.00",
            },
            content_type="application/json",
            **self.headers,
        )
        self.assertEqual(response.status_code, 200)

        settings = FinanceSettings.get_settings()
        self.assertEqual(settings.financial_year_start_month, 7)
        self.assertEqual(settings.journal_prefix, "FIN")
        self.assertEqual(settings.draft_journal_warning_days, 14)
        self.assertEqual(
            settings.large_manual_journal_review_threshold,
            Decimal("5000000.00"),
        )
