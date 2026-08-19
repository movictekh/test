from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import Client as DjangoClient
from django.test import TestCase
from django.utils import timezone

from finance.models import FinanceAccount, FinanceVendor, VendorBill
from user.models.branch import Branch
from user.models.role import Role
from user.tests.helpers import RoleAPITestMixin


class BankCashAccountPass1Tests(RoleAPITestMixin, TestCase):
    def setUp(self):
        self.client = DjangoClient()
        self.role = self.create_role(
            "FIN AT1 Account Tester",
            {"payments": ["list", "create", "view"]},
        )
        self.employee = self.create_user_with_employee(
            "fin.at1@test.com",
            "finat1",
            "EMP-FIN-AT1",
            role=self.role,
        )
        self.headers = self.auth_headers(self.employee)

        self.enugu = Branch.objects.create(
            branch_name="FIN AT1 Enugu",
            branch_id="BR-FIN-AT1-ENU",
            country="Nigeria",
            state="Enugu",
            office_address="Enugu finance test office",
            contact_email="fin-at1-enugu@test.com",
            contact_phone="+2348011111198",
        )
        self.lagos = Branch.objects.create(
            branch_name="FIN AT1 Lagos",
            branch_id="BR-FIN-AT1-LAG",
            country="Nigeria",
            state="Lagos",
            office_address="Lagos finance test office",
            contact_email="fin-at1-lagos@test.com",
            contact_phone="+2348011111199",
        )

        self.account = FinanceAccount.objects.create(
            account_type=FinanceAccount.ACCOUNT_TYPE.BANK,
            display_name="GTBank Operating",
            currency="NGN",
            branch=self.enugu,
            bank_name="GTBank",
            account_number="0123456789",
            account_name="Bomach Group",
            opening_balance=Decimal("2500.00"),
            opening_balance_date=timezone.localdate(),
            created_by=self.employee.user,
        )

    def _record_paid_vendor_bill(self, amount=Decimal("500.00")):
        vendor = FinanceVendor.objects.create(
            name=f"FIN AT1 Test Vendor {FinanceVendor.objects.count() + 1}",
            created_by=self.employee.user,
        )
        return VendorBill.objects.create(
            vendor=vendor,
            branch=self.enugu,
            finance_account=self.account,
            category="Testing",
            description="Paid bill used to establish account activity",
            gross_amount=amount,
            withholding_tax=Decimal("0.00"),
            bill_date=timezone.localdate(),
            due_date=timezone.localdate(),
            status=VendorBill.STATUS.PAID,
            paid_at=timezone.now(),
            payment_reference=f"FIN-AT1-PAID-{VendorBill.objects.count() + 1:03d}",
            created_by=self.employee.user,
        )

    def test_same_physical_bank_account_cannot_be_registered_twice(self):
        with self.assertRaises(ValidationError):
            FinanceAccount.objects.create(
                account_type=FinanceAccount.ACCOUNT_TYPE.BANK,
                display_name="Duplicate GTBank",
                currency="NGN",
                branch=self.enugu,
                bank_name="GTBank",
                account_number="0123456789",
                account_name="Bomach Group",
                created_by=self.employee.user,
            )

    def test_opening_balance_and_financial_identity_are_locked_after_activity(self):
        self._record_paid_vendor_bill()
        self.assertTrue(self.account.has_financial_activity())

        self.account.opening_balance = Decimal("9999.00")
        with self.assertRaises(ValidationError):
            self.account.save()

        self.account.refresh_from_db()
        self.account.account_number = "9999999999"
        with self.assertRaises(ValidationError):
            self.account.save()

    def test_descriptive_fields_can_still_change_after_activity(self):
        self._record_paid_vendor_bill()

        self.account.display_name = "GTBank Main Operating"
        self.account.account_name = "Bomach Group Limited"
        self.account.notes = "Description corrected; financial identity unchanged."
        self.account.save()
        self.account.refresh_from_db()

        self.assertEqual(self.account.display_name, "GTBank Main Operating")
        self.assertEqual(self.account.account_name, "Bomach Group Limited")

    def test_opening_balance_can_be_corrected_before_activity(self):
        fresh = FinanceAccount.objects.create(
            account_type=FinanceAccount.ACCOUNT_TYPE.CASH,
            display_name="Fresh Cash Account",
            currency="NGN",
            branch=self.enugu,
            opening_balance=Decimal("0.00"),
            created_by=self.employee.user,
        )

        fresh.opening_balance = Decimal("350.00")
        fresh.opening_balance_date = timezone.localdate()
        fresh.save()
        fresh.refresh_from_db()

        self.assertEqual(fresh.opening_balance, Decimal("350.00"))

    def test_balance_endpoint_reuses_existing_cashbook_balance(self):
        self._record_paid_vendor_bill(Decimal("500.00"))

        response = self.client.get(
            f"/api/v1/finance/accounts/{self.account.id}/balance",
            **self.headers,
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["account_id"], self.account.id)
        self.assertEqual(body["opening_balance"], "2500.00")
        self.assertEqual(body["book_balance"], "2000.00")
        self.assertEqual(body["currency"], "NGN")

    def test_branch_scoped_user_cannot_modify_or_deactivate_another_branch_account(self):
        scoped_role = Role.objects.create(
            name="FIN AT1 Enugu Scoped",
            permissions={"payments": ["list", "create", "view"]},
        )
        scoped_role.branches.add(self.enugu)
        scoped_employee = self.create_user_with_employee(
            "fin.at1.scoped@test.com",
            "finat1scoped",
            "EMP-FIN-AT1-SCOPED",
            role=scoped_role,
        )
        headers = self.auth_headers(scoped_employee)

        lagos_account = FinanceAccount.objects.create(
            account_type=FinanceAccount.ACCOUNT_TYPE.BANK,
            display_name="Lagos Bank",
            currency="NGN",
            branch=self.lagos,
            bank_name="Access Bank",
            account_number="9988776655",
            account_name="Bomach Group",
            created_by=self.employee.user,
        )

        update_response = self.client.patch(
            f"/api/v1/finance/accounts/{lagos_account.id}",
            data={"display_name": "Unauthorized Change"},
            content_type="application/json",
            **headers,
        )
        self.assertNotEqual(update_response.status_code, 200)

        deactivate_response = self.client.post(
            f"/api/v1/finance/accounts/{lagos_account.id}/deactivate",
            **headers,
        )
        self.assertEqual(deactivate_response.status_code, 404)

        lagos_account.refresh_from_db()
        self.assertEqual(lagos_account.display_name, "Lagos Bank")
        self.assertTrue(lagos_account.is_active)

    def test_branch_scoped_user_cannot_create_account_in_another_branch(self):
        scoped_role = Role.objects.create(
            name="FIN AT1 Enugu Create Scoped",
            permissions={"payments": ["create"]},
        )
        scoped_role.branches.add(self.enugu)
        scoped_employee = self.create_user_with_employee(
            "fin.at1.create.scoped@test.com",
            "finat1createscoped",
            "EMP-FIN-AT1-CREATE",
            role=scoped_role,
        )

        response = self.client.post(
            "/api/v1/finance/accounts",
            data={
                "account_type": "bank",
                "display_name": "Unauthorized Lagos Bank",
                "currency": "NGN",
                "branch_id": self.lagos.id,
                "bank_name": "UBA",
                "account_number": "1122334455",
                "account_name": "Bomach Group",
            },
            content_type="application/json",
            **self.auth_headers(scoped_employee),
        )

        self.assertNotEqual(response.status_code, 201)
        self.assertFalse(
            FinanceAccount.objects.filter(account_number="1122334455").exists()
        )

    def test_branch_scoped_user_cannot_create_company_wide_account(self):
        scoped_role = Role.objects.create(
            name="FIN AT1 Enugu Company Scope Guard",
            permissions={"payments": ["create"]},
        )
        scoped_role.branches.add(self.enugu)
        scoped_employee = self.create_user_with_employee(
            "fin.at1.company.guard@test.com",
            "finat1companyguard",
            "EMP-FIN-AT1-COMPANY",
            role=scoped_role,
        )

        response = self.client.post(
            "/api/v1/finance/accounts",
            data={
                "account_type": "bank",
                "display_name": "Unauthorized Company Bank",
                "currency": "NGN",
                "bank_name": "Zenith Bank",
                "account_number": "2233445566",
                "account_name": "Bomach Group",
            },
            content_type="application/json",
            **self.auth_headers(scoped_employee),
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(
            FinanceAccount.objects.filter(account_number="2233445566").exists()
        )

    def test_branch_scoped_user_cannot_clear_account_branch(self):
        scoped_role = Role.objects.create(
            name="FIN AT1 Enugu Branch Clear Guard",
            permissions={"payments": ["create"]},
        )
        scoped_role.branches.add(self.enugu)
        scoped_employee = self.create_user_with_employee(
            "fin.at1.branch.clear@test.com",
            "finat1branchclear",
            "EMP-FIN-AT1-BRANCH-CLEAR",
            role=scoped_role,
        )

        response = self.client.patch(
            f"/api/v1/finance/accounts/{self.account.id}",
            data={"branch_id": None},
            content_type="application/json",
            **self.auth_headers(scoped_employee),
        )

        self.assertEqual(response.status_code, 400)
        self.account.refresh_from_db()
        self.assertEqual(self.account.branch_id, self.enugu.id)

    def test_inactive_finance_account_cannot_be_selected_for_new_expense(self):
        inactive = FinanceAccount.objects.create(
            account_type=FinanceAccount.ACCOUNT_TYPE.BANK,
            display_name="Inactive Expense Bank",
            currency="NGN",
            branch=self.enugu,
            bank_name="First Bank",
            account_number="3344556677",
            account_name="Bomach Group",
            is_active=False,
            created_by=self.employee.user,
        )
        expense_role = Role.objects.create(
            name="FIN AT1 Expense Active Account Guard",
            permissions={"expenses": ["create"]},
        )
        expense_role.branches.add(self.enugu)
        expense_employee = self.create_user_with_employee(
            "fin.at1.expense.guard@test.com",
            "finat1expenseguard",
            "EMP-FIN-AT1-EXPENSE",
            role=expense_role,
        )

        response = self.client.post(
            "/api/v1/finance/expenses",
            data={
                "branch_id": self.enugu.id,
                "finance_account_id": inactive.id,
                "date": timezone.localdate().isoformat(),
                "description": "Should not use an inactive Finance account",
                "amount": "100.00",
            },
            content_type="application/json",
            **self.auth_headers(expense_employee),
        )

        self.assertEqual(response.status_code, 400)
