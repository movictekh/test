from datetime import timedelta
from decimal import Decimal

from django.test import Client as DjangoClient
from django.test import TestCase
from django.utils import timezone

from finance.models import (
    FinanceSettings,
    FinanceVendor,
    FixedAsset,
    FixedAssetCategory,
    LedgerAccount,
    VendorBill,
)
from finance.service import create_manual_journal
from user.models.branch import Branch
from user.models.role import PERMISSIONS_MAP
from user.tests.helpers import RoleAPITestMixin


class FinanceIntelligenceControlPass34Tests(RoleAPITestMixin, TestCase):
    def setUp(self):
        self.client = DjangoClient()
        self.role = self.create_role(
            "FIN IC3-4 Tester",
            {
                "financial_reports": ["view"],
                "finance_audit": ["view"],
            },
        )
        self.employee = self.create_user_with_employee(
            "fin.ic34@test.com",
            "finic34",
            "EMP-FIN-IC34",
            role=self.role,
        )
        self.headers = self.auth_headers(self.employee)
        self.branch = self._branch("FIN IC34 Lagos", "BR-FIN-IC34-LAG")
        self.other_branch = self._branch("FIN IC34 Abuja", "BR-FIN-IC34-ABJ")
        self.role.branches.add(self.branch)
        self.vendor = FinanceVendor.objects.create(
            name="FIN IC34 Vendor",
            default_category=FinanceVendor.CATEGORY.PROFESSIONAL_SERVICES,
            created_by=self.employee.user,
        )

    def _branch(self, name, branch_id):
        return Branch.objects.create(
            branch_name=name,
            branch_id=branch_id,
            country="Nigeria",
            state="Lagos",
            office_address=f"{name} office",
            contact_email=f"{branch_id.lower()}@test.com",
            contact_phone="+2348011111199",
        )

    def _vendor_bill(self, *, branch, due_offset, amount):
        today = timezone.localdate()
        return VendorBill.objects.create(
            vendor=self.vendor,
            branch=branch,
            category="Professional Services",
            description="IC3 ageing test bill",
            gross_amount=Decimal(amount),
            withholding_tax=Decimal("0.00"),
            bill_date=today - timedelta(days=30),
            due_date=today + timedelta(days=due_offset),
            status=VendorBill.STATUS.AWAITING_APPROVAL,
            created_by=self.employee.user,
        )

    def _draft_manual_journal(self, *, branch, amount, created_days_ago=0):
        expense = LedgerAccount.objects.get(
            system_role=LedgerAccount.SYSTEM_ROLE.OPERATING_EXPENSE
        )
        revenue = LedgerAccount.objects.get(
            system_role=LedgerAccount.SYSTEM_ROLE.SERVICE_REVENUE
        )
        entry = create_manual_journal(
            entry_date=timezone.localdate(),
            currency="NGN",
            branch=branch,
            created_by=self.employee.user,
            memo="IC4 manual journal exception test",
            lines=[
                {
                    "ledger_account_id": expense.id,
                    "debit": Decimal(amount),
                    "credit": Decimal("0.00"),
                },
                {
                    "ledger_account_id": revenue.id,
                    "debit": Decimal("0.00"),
                    "credit": Decimal(amount),
                },
            ],
        )
        if created_days_ago:
            type(entry).objects.filter(pk=entry.pk).update(
                created_at=timezone.now() - timedelta(days=created_days_ago)
            )
            entry.refresh_from_db()
        return entry

    def _overdue_fixed_asset(self, branch):
        asset_cost = LedgerAccount.objects.get(code="1610")
        accumulated = LedgerAccount.objects.get(code="1690")
        depreciation_expense = LedgerAccount.objects.get(code="6300")
        category = FixedAssetCategory.objects.create(
            code="IC34-EQP",
            name="IC34 Equipment",
            asset_ledger_account=asset_cost,
            accumulated_depreciation_ledger_account=accumulated,
            depreciation_expense_ledger_account=depreciation_expense,
            default_useful_life_months=12,
            default_residual_value_percent=Decimal("0.00"),
            created_by=self.employee.user,
        )
        capitalization_date = timezone.localdate() - timedelta(days=120)
        asset = FixedAsset.objects.create(
            name="IC34 Test Asset",
            category=category,
            branch=branch,
            acquisition_date=capitalization_date,
            acquisition_cost=Decimal("12000.00"),
            residual_value=Decimal("0.00"),
            useful_life_months=12,
            asset_ledger_account=asset_cost,
            accumulated_depreciation_ledger_account=accumulated,
            depreciation_expense_ledger_account=depreciation_expense,
            created_by=self.employee.user,
        )
        FixedAsset.objects.filter(pk=asset.pk).update(
            status=FixedAsset.STATUS.ACTIVE,
            capitalization_date=capitalization_date,
        )
        asset.refresh_from_db()
        return asset

    def test_report_catalog_reuses_existing_engines_and_marks_deferred_reports(self):
        response = self.client.get(
            "/api/v1/finance/reports/catalog",
            **self.headers,
        )
        self.assertEqual(response.status_code, 200)
        reports = {row["key"]: row for row in response.json()["reports"]}
        self.assertEqual(
            reports["receivables_ageing"]["endpoint"],
            "/api/v1/finance/receivables/summary",
        )
        self.assertEqual(
            reports["project_profitability"]["endpoint"],
            "/api/v1/finance/service-orders/profitability/summary",
        )
        self.assertEqual(reports["cash_flow_statement"]["availability"], "deferred")
        self.assertEqual(reports["budget_vs_actual"]["availability"], "deferred")

    def test_payables_ageing_uses_buckets_and_branch_scope(self):
        self._vendor_bill(branch=self.branch, due_offset=-10, amount="100.00")
        self._vendor_bill(branch=self.branch, due_offset=10, amount="200.00")
        self._vendor_bill(branch=self.other_branch, due_offset=-40, amount="300.00")

        response = self.client.get(
            "/api/v1/finance/reports/payables-ageing",
            **self.headers,
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(Decimal(body["total_payables"]), Decimal("300.00"))
        self.assertEqual(Decimal(body["current"]), Decimal("200.00"))
        self.assertEqual(Decimal(body["bucket_1_30"]), Decimal("100.00"))
        self.assertEqual(Decimal(body["bucket_31_60"]), Decimal("0.00"))
        self.assertEqual(body["payable_count"], 2)
        self.assertEqual(body["overdue_count"], 1)
        self.assertEqual(body["currency"], "NGN")

    def test_paid_and_non_open_vendor_bills_are_not_in_payables_ageing(self):
        paid = self._vendor_bill(branch=self.branch, due_offset=-10, amount="100.00")
        VendorBill.objects.filter(pk=paid.pk).update(status=VendorBill.STATUS.PAID)
        rejected = self._vendor_bill(
            branch=self.branch,
            due_offset=-20,
            amount="200.00",
        )
        VendorBill.objects.filter(pk=rejected.pk).update(
            status=VendorBill.STATUS.REJECTED
        )

        response = self.client.get(
            "/api/v1/finance/reports/payables-ageing",
            **self.headers,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["payable_count"], 0)

    def test_exception_centre_detects_four_initial_deterministic_controls(self):
        settings = FinanceSettings.get_settings()
        settings.draft_journal_warning_days = 7
        settings.large_manual_journal_review_threshold = Decimal("1000.00")
        settings.updated_by = self.employee.user
        settings.save()

        self._draft_manual_journal(
            branch=self.branch,
            amount="5000.00",
            created_days_ago=10,
        )
        self._vendor_bill(branch=self.branch, due_offset=-5, amount="250.00")
        self._overdue_fixed_asset(self.branch)

        response = self.client.get("/api/v1/finance/exceptions", **self.headers)
        self.assertEqual(response.status_code, 200)
        rows = response.json()
        categories = {row["category"] for row in rows}
        self.assertEqual(
            categories,
            {
                "journal_draft_ageing",
                "manual_journal_review",
                "payables",
                "fixed_assets",
            },
        )
        self.assertEqual(len(rows), 4)

    def test_exception_centre_obeys_branch_scope(self):
        settings = FinanceSettings.get_settings()
        settings.draft_journal_warning_days = 1
        settings.large_manual_journal_review_threshold = None
        settings.save()

        self._draft_manual_journal(
            branch=self.other_branch,
            amount="50.00",
            created_days_ago=5,
        )
        self._vendor_bill(branch=self.other_branch, due_offset=-5, amount="250.00")

        response = self.client.get("/api/v1/finance/exceptions", **self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_large_manual_journal_threshold_is_optional(self):
        settings = FinanceSettings.get_settings()
        settings.draft_journal_warning_days = 365
        settings.large_manual_journal_review_threshold = None
        settings.save()
        self._draft_manual_journal(branch=self.branch, amount="999999.00")

        response = self.client.get(
            "/api/v1/finance/exceptions?category=manual_journal_review",
            **self.headers,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_exception_summary_counts_warning_and_information_separately(self):
        settings = FinanceSettings.get_settings()
        settings.draft_journal_warning_days = 7
        settings.large_manual_journal_review_threshold = Decimal("1000.00")
        settings.save()
        self._draft_manual_journal(
            branch=self.branch,
            amount="5000.00",
            created_days_ago=10,
        )
        self._vendor_bill(branch=self.branch, due_offset=-5, amount="250.00")

        response = self.client.get(
            "/api/v1/finance/exceptions/summary",
            **self.headers,
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["total_count"], 3)
        self.assertEqual(body["critical_count"], 0)
        self.assertEqual(body["warning_count"], 2)
        self.assertEqual(body["info_count"], 1)
        self.assertEqual(body["category_counts"]["payables"], 1)

    def test_exception_filters_reject_unknown_values(self):
        response = self.client.get(
            "/api/v1/finance/exceptions?severity=urgent",
            **self.headers,
        )
        self.assertEqual(response.status_code, 400)
        response = self.client.get(
            "/api/v1/finance/exceptions?category=bank_matching",
            **self.headers,
        )
        self.assertEqual(response.status_code, 400)

    def test_finance_audit_permission_family_is_registered(self):
        self.assertEqual(PERMISSIONS_MAP["finance_audit"], ["view"])
