from datetime import timedelta
from decimal import Decimal

from django.test import Client as DjangoClient
from django.test import TestCase
from django.utils import timezone

from finance.models import FinanceSettings, FinanceVendor, LedgerAccount, VendorBill
from finance.service import create_manual_journal, post_journal_entry
from finance.service.audit import record_finance_audit
from user.models import AuditLog
from user.models.branch import Branch
from user.models.role import PERMISSIONS_MAP
from user.tests.helpers import RoleAPITestMixin


class FinanceAuditExportsPass56Tests(RoleAPITestMixin, TestCase):
    def setUp(self):
        self.client = DjangoClient()
        self.role = self.create_role(
            "FIN IC5-6 Company Tester",
            {
                "financial_reports": ["view", "export"],
                "finance_audit": ["view", "export"],
                "finance_settings": ["view", "update"],
            },
        )
        self.employee = self.create_user_with_employee(
            "fin.ic56@test.com",
            "finic56",
            "EMP-FIN-IC56",
            role=self.role,
        )
        self.headers = self.auth_headers(self.employee)
        self.branch = self._branch("FIN IC56 Lagos", "BR-FIN-IC56-LAG")
        self.other_branch = self._branch("FIN IC56 Abuja", "BR-FIN-IC56-ABJ")
        self.vendor = FinanceVendor.objects.create(
            name="FIN IC56 Vendor",
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
            contact_phone="+2348011111187",
        )

    def _posted_manual_journal(self, branch=None, amount="100.00"):
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
            memo="IC5-6 audit and export test",
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
        return post_journal_entry(entry, self.employee.user)

    def _overdue_bill(self, branch=None, amount="250.00"):
        today = timezone.localdate()
        return VendorBill.objects.create(
            vendor=self.vendor,
            branch=branch,
            category="Professional Services",
            description="IC5-6 overdue bill",
            gross_amount=Decimal(amount),
            withholding_tax=Decimal("0.00"),
            bill_date=today - timedelta(days=30),
            due_date=today - timedelta(days=5),
            status=VendorBill.STATUS.AWAITING_APPROVAL,
            created_by=self.employee.user,
        )

    def test_permissions_and_finance_audit_type_are_registered(self):
        self.assertEqual(PERMISSIONS_MAP["financial_reports"], ["view", "export"])
        self.assertEqual(PERMISSIONS_MAP["finance_audit"], ["view", "export"])
        self.assertEqual(AuditLog.AuditType.FINANCE_ACTION, "finance_action")

    def test_posting_journal_creates_structured_permanent_audit_event(self):
        entry = self._posted_manual_journal(branch=self.branch, amount="125.00")
        log = AuditLog.objects.get(
            audit_type=AuditLog.AuditType.FINANCE_ACTION,
            metadata__area="journals",
            metadata__action="posted",
            metadata__entity_id=entry.id,
        )
        self.assertEqual(log.user_id, self.employee.user_id)
        self.assertEqual(log.metadata["reference"], entry.journal_number)
        self.assertEqual(log.metadata["branch_id"], self.branch.id)
        self.assertEqual(log.metadata["amount"], "125.00")

    def test_finance_settings_save_creates_audit_with_change_metadata(self):
        settings = FinanceSettings.get_settings()
        settings.draft_journal_warning_days = 14
        settings.updated_by = self.employee.user
        settings.save()

        log = AuditLog.objects.get(
            audit_type=AuditLog.AuditType.FINANCE_ACTION,
            metadata__area="finance_settings",
            metadata__action="updated",
        )
        changes = log.metadata["details"]["changes"]
        self.assertEqual(changes["draft_journal_warning_days"]["to"], 14)

    def test_finance_audit_endpoint_excludes_non_finance_audit_types(self):
        AuditLog.objects.create(
            audit_type=AuditLog.AuditType.LOGIN,
            audit_status=AuditLog.AuditStatus.SUCCESS,
            activity="Ordinary login audit",
            user=self.employee.user,
        )
        settings = FinanceSettings.get_settings()
        record_finance_audit(
            area="finance_settings",
            action="reviewed",
            actor=self.employee.user,
            entity=settings,
            reference="Finance Settings",
        )

        response = self.client.get("/api/v1/finance/audit", **self.headers)
        self.assertEqual(response.status_code, 200)
        body = response.json()
        items = body["items"] if isinstance(body, dict) and "items" in body else body
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["audit_type"], "finance_action")

    def test_finance_audit_endpoint_obeys_branch_scope(self):
        branch_role = self.create_role(
            "FIN IC5-6 Branch Auditor",
            {"finance_audit": ["view", "export"]},
        )
        branch_role.branches.add(self.branch)
        branch_employee = self.create_user_with_employee(
            "fin.ic56.branch@test.com",
            "finic56branch",
            "EMP-FIN-IC56-BR",
            role=branch_role,
        )
        branch_headers = self.auth_headers(branch_employee)

        first = self._posted_manual_journal(branch=self.branch, amount="10.00")
        second = self._posted_manual_journal(branch=self.other_branch, amount="20.00")
        self.assertNotEqual(first.branch_id, second.branch_id)

        response = self.client.get("/api/v1/finance/audit", **branch_headers)
        self.assertEqual(response.status_code, 200)
        body = response.json()
        items = body["items"] if isinstance(body, dict) and "items" in body else body
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["metadata"]["branch_id"], self.branch.id)

    def test_profit_and_loss_csv_export_uses_posted_accounting(self):
        self._posted_manual_journal(amount="300.00")
        response = self.client.get(
            "/api/v1/finance/reports/export?report_key=profit_and_loss",
            **self.headers,
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response["Content-Type"].startswith("text/csv"))
        content = response.content.decode()
        self.assertIn("Net Profit", content)
        self.assertIn("300.00", content)

    def test_payables_ageing_csv_export(self):
        bill = self._overdue_bill(branch=self.branch, amount="450.00")
        response = self.client.get(
            "/api/v1/finance/reports/export?report_key=payables_ageing",
            **self.headers,
        )
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn(bill.bill_number, content)
        self.assertIn("450.00", content)

    def test_exception_csv_export(self):
        bill = self._overdue_bill(branch=self.branch)
        response = self.client.get(
            "/api/v1/finance/exceptions/export",
            **self.headers,
        )
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn("payables", content)
        self.assertIn(bill.bill_number, content)

    def test_audit_csv_export(self):
        settings = FinanceSettings.get_settings()
        record_finance_audit(
            area="finance_settings",
            action="reviewed",
            actor=self.employee.user,
            entity=settings,
            reference="Finance Settings",
        )
        response = self.client.get("/api/v1/finance/audit/export", **self.headers)
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn("finance_settings", content)
        self.assertIn("reviewed", content)

    def test_report_catalog_exposes_native_csv_and_exception_report(self):
        response = self.client.get(
            "/api/v1/finance/reports/catalog",
            **self.headers,
        )
        self.assertEqual(response.status_code, 200)
        reports = {row["key"]: row for row in response.json()["reports"]}
        self.assertEqual(reports["profit_and_loss"]["export_format"], "csv")
        self.assertIn(
            "report_key=profit_and_loss",
            reports["profit_and_loss"]["export_endpoint"],
        )
        self.assertEqual(reports["audit_exceptions"]["availability"], "available")
        self.assertEqual(
            reports["audit_exceptions"]["export_endpoint"],
            "/api/v1/finance/exceptions/export",
        )
        self.assertIsNone(reports["payroll"].get("export_endpoint"))

    def test_unknown_report_export_is_rejected(self):
        response = self.client.get(
            "/api/v1/finance/reports/export?report_key=budget_vs_actual",
            **self.headers,
        )
        self.assertEqual(response.status_code, 400)
