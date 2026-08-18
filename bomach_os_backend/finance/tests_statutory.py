from datetime import date
from decimal import Decimal
from django.test import Client as DjangoClient, TestCase
from finance.models import FinanceAccount,FinanceVendor,StatutoryObligation,VendorBill
from user.models.branch import Branch
from user.models.role import Role
from user.tests.helpers import RoleAPITestMixin
class FinanceStatutoryAPITests(RoleAPITestMixin,TestCase):
    def setUp(self):
        self.client=DjangoClient(); self.role=self.create_role("Statutory Manager",{"statutory":["list","view","create","update","generate","submit","approve","reject","pay","void"],"finance_payroll":["list","view","create","update","calculate","submit","approve","reject","pay","cancel"],"payments":["list"]})
        self.employee=self.create_user_with_employee("stat.manager@test.com","statmanager","EMP-STAT-MGR",role=self.role); self.headers=self.auth_headers(self.employee)
        self.branch=Branch.objects.create(branch_name="Enugu",branch_id="BR-STAT-ENU",country="Nigeria",state="Enugu",office_address="Enugu office",contact_email="stat-enugu@test.com",contact_phone="+2348010000001")
        # Payroll calculation only includes active monthly employees with positive salary.
        # Give the statutory test manager a real payroll configuration so the PAYE
        # source-generation test exercises the actual Finance Payroll workflow.
        self.employee.branch=self.branch
        self.employee.gross_salary=Decimal("300000.00")
        self.employee.salary_frequency="monthly"
        self.employee.employment_status="active"
        self.employee.bank_name="GTBank"
        self.employee.account_number="1234567890"
        self.employee.is_active=True
        self.employee.save()
        self.account=FinanceAccount.objects.create(account_type="bank",display_name="Statutory Account",bank_name="GTBank",account_number="2222333344",account_name="Bomach Group",opening_balance=Decimal("2000000.00"),opening_balance_date=date(2026,8,1),branch=self.branch,created_by=self.employee.user)
        self.vendor=FinanceVendor.objects.create(name="BuildMart",default_category="materials",created_by=self.employee.user)
    def post(self,path,payload=None): return self.client.post(path,data=payload or {},content_type="application/json",**self.headers)
    def test_manual_vat_drives_summary(self):
        r=self.post("/api/v1/finance/statutory/obligations",{"obligation_type":"vat","period_label":"July 2026","period_start":"2026-07-01","period_end":"2026-07-31","basis":"Reviewed VAT return","basis_amount":"12000000.00","amount":"918750.00","due_date":"2026-08-21","branch_id":self.branch.id}); self.assertEqual(r.status_code,201)
        s=self.client.get("/api/v1/finance/statutory/summary",**self.headers); self.assertEqual(s.status_code,200); self.assertEqual(s.json()["vat_payable"],"918750.00")
    def test_wht_generation_and_cashbook_split(self):
        bill=VendorBill.objects.create(vendor=self.vendor,branch=self.branch,finance_account=self.account,category="Materials",description="Cement",gross_amount=Decimal("1000000.00"),withholding_tax=Decimal("50000.00"),bill_date=date(2026,8,1),due_date=date(2026,8,10),status="paid",paid_by=self.employee.user,paid_at="2026-08-10T10:00:00+01:00",payment_reference="VEN-NET-001",created_by=self.employee.user)
        g=self.post("/api/v1/finance/statutory/generate/wht",{"period_start":"2026-08-01","period_end":"2026-08-31","due_date":"2026-09-21","branch_id":self.branch.id,"period_label":"August 2026"}); self.assertEqual(g.status_code,201); self.assertEqual(g.json()["amount"],"50000.00")
        self.assertEqual(self.post("/api/v1/finance/statutory/generate/wht",{"period_start":"2026-08-01","period_end":"2026-08-31","due_date":"2026-09-21","branch_id":self.branch.id}).status_code,400)
        oid=g.json()["id"]; self.post(f"/api/v1/finance/statutory/obligations/{oid}/submit"); self.post(f"/api/v1/finance/statutory/obligations/{oid}/approve"); self.assertEqual(self.post(f"/api/v1/finance/statutory/obligations/{oid}/pay",{"finance_account_id":self.account.id,"paid_at":"2026-09-21T10:00:00+01:00","payment_reference":"WHT-REM-001"}).status_code,200)
        v=self.client.get("/api/v1/finance/cashbook",{"date_from":"2026-08-10","date_to":"2026-08-10","source":"vendor_bill"},**self.headers); self.assertEqual(v.json()["items"][0]["money_out"],"950000.00")
        st=self.client.get("/api/v1/finance/cashbook",{"date_from":"2026-09-21","date_to":"2026-09-21","source":"statutory"},**self.headers); self.assertEqual(st.json()["items"][0]["money_out"],"50000.00")
    def test_payroll_paye_uses_explicit_deduction(self):
        p=self.post("/api/v1/finance/payroll",{"period_month":8,"period_year":2026,"scheduled_payment_date":"2026-08-31","branch_id":self.branch.id}); self.assertEqual(p.status_code,201); rid=p.json()["id"]
        c=self.post(f"/api/v1/finance/payroll/{rid}/calculate")
        self.assertEqual(c.status_code,200)
        self.assertEqual(len(c.json()["lines"]),1)
        line=c.json()["lines"][0]
        a=self.client.put(f"/api/v1/finance/payroll/{rid}/lines/{line['id']}/manual-items",data={"items":[{"item_type":"deduction","category":"paye","name":"PAYE","amount":"25000.00"}]},content_type="application/json",**self.headers); self.assertEqual(a.status_code,200)
        self.post(f"/api/v1/finance/payroll/{rid}/submit"); self.post(f"/api/v1/finance/payroll/{rid}/approve")
        g=self.post("/api/v1/finance/statutory/generate/payroll",{"payroll_run_id":rid,"category":"paye","due_date":"2026-09-10"}); self.assertEqual(g.status_code,201); self.assertEqual(g.json()["amount"],"25000.00")
        self.assertEqual(self.post("/api/v1/finance/statutory/generate/payroll",{"payroll_run_id":rid,"category":"paye","due_date":"2026-09-10"}).status_code,400)
    def test_permission_is_separate(self):
        role=Role.objects.create(name="No Stat",permissions={"finance_payroll":["list"]}); emp=self.create_user_with_employee("nostat@test.com","nostat","EMP-NOSTAT",role=role)
        self.assertEqual(self.client.get("/api/v1/finance/statutory/obligations",**self.auth_headers(emp)).status_code,403)
    def test_paid_cannot_be_voided(self):
        o=StatutoryObligation.objects.create(obligation_type="other",source_type="manual",branch=self.branch,period_label="Aug 2026",period_start=date(2026,8,1),period_end=date(2026,8,31),basis="Filing",basis_amount=Decimal("100000.00"),amount=Decimal("10000.00"),due_date=date(2026,9,15),status="approved",created_by=self.employee.user)
        self.assertEqual(self.post(f"/api/v1/finance/statutory/obligations/{o.id}/pay",{"finance_account_id":self.account.id,"payment_reference":"STAT-001"}).status_code,200)
        self.assertEqual(self.post(f"/api/v1/finance/statutory/obligations/{o.id}/void").status_code,400)
