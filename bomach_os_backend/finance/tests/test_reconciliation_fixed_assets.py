from datetime import date,datetime
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.test import Client as DjangoClient,TestCase
from django.utils import timezone
from finance.models import BankReconciliation,BankStatementLine,FinanceAccount,FixedAsset,FixedAssetCategory,JournalEntry,LedgerAccount
from finance.service import add_bank_statement_lines,capitalize_fixed_asset,close_bank_reconciliation,create_bank_reconciliation,create_fixed_asset,create_manual_journal,depreciation_schedule,dispose_fixed_asset,ensure_finance_account_ledger_account,match_bank_statement_line,post_expense_payment_journal,post_fixed_asset_depreciation,post_journal_entry,reconcile_bank_reconciliation,reconciliation_summary,reverse_journal_entry
from services.models.expenses import Expense
from user.models.branch import Branch
from user.tests.helpers import RoleAPITestMixin

class ReconciliationFixedAssetsPassTests(RoleAPITestMixin,TestCase):
    def setUp(self):
        self.client=DjangoClient(); self.role=self.create_role('FIN AT4-5 Tester',{'bank_reconciliation':['create','view','list','update','match','reconcile','close'],'fixed_asset_categories':['create','view','list','update','deactivate'],'fixed_assets':['create','view','list','update','capitalize','depreciate','dispose'],'chart_of_accounts':['view','list'],'journals':['create','view','list','update','post','reverse'],'general_ledger':['view','list']}); self.employee=self.create_user_with_employee('fin.at45@test.com','finat45','EMP-FIN-AT45',role=self.role); self.headers=self.auth_headers(self.employee)
        self.branch=Branch.objects.create(branch_name='FIN AT45 Abuja',branch_id='BR-FIN-AT45',country='Nigeria',state='FCT',office_address='Finance AT45 test office',contact_email='fin-at45@test.com',contact_phone='+2348011111455')
        self.finance_account=FinanceAccount.objects.create(account_type=FinanceAccount.ACCOUNT_TYPE.BANK,display_name='FIN AT45 Test Bank',currency='NGN',branch=self.branch,bank_name='Access Bank',account_number='4500112233',account_name='Bomach Group',opening_balance=Decimal('0.00'),created_by=self.employee.user)
        self.bank_ledger=ensure_finance_account_ledger_account(self.finance_account,self.employee.user); self.operating_expense=LedgerAccount.objects.get(system_role=LedgerAccount.SYSTEM_ROLE.OPERATING_EXPENSE); self.service_revenue=LedgerAccount.objects.get(system_role=LedgerAccount.SYSTEM_ROLE.SERVICE_REVENUE)
    def _bank_move(self,amount,money_in,day=None,reference=''):
        day=day or timezone.localdate(); lines=[{'ledger_account_id':self.bank_ledger.id,'debit':amount,'credit':Decimal('0.00')},{'ledger_account_id':self.service_revenue.id,'debit':Decimal('0.00'),'credit':amount}] if money_in else [{'ledger_account_id':self.operating_expense.id,'debit':amount,'credit':Decimal('0.00')},{'ledger_account_id':self.bank_ledger.id,'debit':Decimal('0.00'),'credit':amount}]
        return post_journal_entry(create_manual_journal(entry_date=day,currency='NGN',branch=self.branch,reference=reference,created_by=self.employee.user,lines=lines),self.employee.user)
    def _category(self,life=3):
        return FixedAssetCategory.objects.create(code=f'EQUIP-{life}',name=f'Equipment {life}',asset_ledger_account=LedgerAccount.objects.get(code='1610'),accumulated_depreciation_ledger_account=LedgerAccount.objects.get(code='1690'),depreciation_expense_ledger_account=LedgerAccount.objects.get(code='6300'),default_useful_life_months=life,default_residual_value_percent=Decimal('0.00'),created_by=self.employee.user)
    def _capex(self,amount=Decimal('100.00'),paid_date=date(2026,4,1)):
        e=Expense.objects.create(user=self.employee.user,branch=self.branch,finance_account=self.finance_account,date=paid_date,description='Capital equipment purchase',amount=amount,cost_type=Expense.COST_TYPE.CAPITAL_EXPENDITURE,category=Expense.CATEGORY_CHOICES.EQUIPMENT,status=Expense.STATUS.PAID,paid_by=self.employee.user,paid_at=timezone.make_aware(datetime(paid_date.year,paid_date.month,paid_date.day,12,0,0)),payment_reference=f'CAPEX-{amount}'); post_expense_payment_journal(e,self.employee.user); return e
    def test_reconciliation_requires_bank_account(self):
        cash=FinanceAccount.objects.create(account_type=FinanceAccount.ACCOUNT_TYPE.CASH,display_name='AT45 Cash',currency='NGN',opening_balance=Decimal('0.00'),created_by=self.employee.user); ensure_finance_account_ledger_account(cash,self.employee.user)
        with self.assertRaises(ValidationError): create_bank_reconciliation(finance_account=cash,statement_start_date=timezone.localdate(),statement_end_date=timezone.localdate(),statement_opening_balance=Decimal('0.00'),statement_closing_balance=Decimal('0.00'),created_by=self.employee.user)
    def test_reconciliation_supports_outstanding_gl_item(self):
        day=timezone.localdate(); dep=self._bank_move(Decimal('100.00'),True,day,'DEP-100'); self._bank_move(Decimal('20.00'),False,day,'PAY-20'); r=create_bank_reconciliation(finance_account=self.finance_account,statement_start_date=day,statement_end_date=day,statement_opening_balance=Decimal('0.00'),statement_closing_balance=Decimal('100.00'),created_by=self.employee.user); s=add_bank_statement_lines(r,[{'transaction_date':day,'reference':'DEP-100','amount':Decimal('100.00'),'direction':BankStatementLine.DIRECTION.CREDIT,'sequence_number':1}])[0]; match_bank_statement_line(reconciliation=r,bank_statement_line=s,journal_line=dep.lines.get(ledger_account=self.bank_ledger),matched_amount=Decimal('100.00'),matched_by=self.employee.user); summary=reconciliation_summary(r); self.assertEqual(summary['outstanding_gl_net'],Decimal('-20.00')); self.assertEqual(summary['adjusted_statement_balance'],Decimal('80.00')); self.assertEqual(summary['book_closing_balance'],Decimal('80.00')); self.assertEqual(summary['unexplained_difference'],Decimal('0.00')); self.assertEqual(reconcile_bank_reconciliation(r,self.employee.user).status,BankReconciliation.STATUS.RECONCILED)
    def test_unmatched_statement_blocks_reconcile(self):
        day=timezone.localdate(); r=create_bank_reconciliation(finance_account=self.finance_account,statement_start_date=day,statement_end_date=day,statement_opening_balance=Decimal('0.00'),statement_closing_balance=Decimal('10.00'),created_by=self.employee.user); add_bank_statement_lines(r,[{'transaction_date':day,'amount':Decimal('10.00'),'direction':BankStatementLine.DIRECTION.CREDIT,'sequence_number':1}])
        with self.assertRaises(ValidationError): reconcile_bank_reconciliation(r,self.employee.user)
    def test_closed_reconciliation_is_immutable(self):
        day=timezone.localdate(); dep=self._bank_move(Decimal('50.00'),True,day); r=create_bank_reconciliation(finance_account=self.finance_account,statement_start_date=day,statement_end_date=day,statement_opening_balance=Decimal('0.00'),statement_closing_balance=Decimal('50.00'),created_by=self.employee.user); s=add_bank_statement_lines(r,[{'transaction_date':day,'amount':Decimal('50.00'),'direction':BankStatementLine.DIRECTION.CREDIT,'sequence_number':1}])[0]; match_bank_statement_line(reconciliation=r,bank_statement_line=s,journal_line=dep.lines.get(ledger_account=self.bank_ledger),matched_amount=Decimal('50.00'),matched_by=self.employee.user); r=close_bank_reconciliation(reconcile_bank_reconciliation(r,self.employee.user),self.employee.user); r.notes='changed'
        with self.assertRaises(ValidationError): r.save()
    def test_category_enforces_accumulated_depreciation_shape(self):
        with self.assertRaises(ValidationError): FixedAssetCategory.objects.create(code='BAD',name='Bad',asset_ledger_account=LedgerAccount.objects.get(code='1610'),accumulated_depreciation_ledger_account=LedgerAccount.objects.get(code='1610'),depreciation_expense_ledger_account=LedgerAccount.objects.get(code='6300'),default_useful_life_months=12,created_by=self.employee.user)
    def test_capitalization_clears_capex(self):
        e=self._capex(Decimal('120.00')); c=self._category(12); a=create_fixed_asset(category=c,source_expense=e,name='Laptop',acquisition_date=e.date,acquisition_cost=Decimal('120.00'),created_by=self.employee.user); a,j,created=capitalize_fixed_asset(a,self.employee.user); self.assertTrue(created); self.assertEqual(a.status,FixedAsset.STATUS.ACTIVE); self.assertEqual(j.lines.get(ledger_account__code='1610').debit,Decimal('120.00')); self.assertEqual(j.lines.get(ledger_account__system_role=LedgerAccount.SYSTEM_ROLE.CAPITAL_EXPENDITURE_CLEARING).credit,Decimal('120.00'))
    def test_source_expense_cannot_be_overcapitalized(self):
        e=self._capex(Decimal('100.00')); c=self._category(12); a=create_fixed_asset(category=c,source_expense=e,name='A',acquisition_date=e.date,acquisition_cost=Decimal('70.00'),created_by=self.employee.user); capitalize_fixed_asset(a,self.employee.user); b=create_fixed_asset(category=c,source_expense=e,name='B',acquisition_date=e.date,acquisition_cost=Decimal('40.00'),created_by=self.employee.user)
        with self.assertRaises(ValidationError): capitalize_fixed_asset(b,self.employee.user)
    def test_depreciation_first_full_month_and_cumulative_rounding(self):
        e=self._capex(Decimal('100.00')); c=self._category(3); a=create_fixed_asset(category=c,source_expense=e,name='Three Month',acquisition_date=date(2026,4,1),acquisition_cost=Decimal('100.00'),created_by=self.employee.user); a,_,_=capitalize_fixed_asset(a,self.employee.user,capitalization_date=date(2026,4,1)); sch=depreciation_schedule(a); self.assertEqual(sch[0]['period_end'],date(2026,5,31)); self.assertEqual([x['depreciation_amount'] for x in sch],[Decimal('33.33'),Decimal('33.34'),Decimal('33.33')]); posted=[]
        for d in [date(2026,5,31),date(2026,6,30),date(2026,7,31)]:
            a,j,created=post_fixed_asset_depreciation(a,d,self.employee.user); self.assertTrue(created); posted.append(j.lines.get(ledger_account=a.accumulated_depreciation_ledger_account).credit); a.refresh_from_db()
        self.assertEqual(sum(posted,Decimal('0.00')),Decimal('100.00')); self.assertEqual(a.status,FixedAsset.STATUS.FULLY_DEPRECIATED)
    def test_disposal_gain_and_generic_reversal_block(self):
        e=self._capex(Decimal('100.00')); c=self._category(12); a=create_fixed_asset(category=c,source_expense=e,name='Disposal',acquisition_date=e.date,acquisition_cost=Decimal('100.00'),created_by=self.employee.user); a,cap,_=capitalize_fixed_asset(a,self.employee.user)
        with self.assertRaises(ValidationError): reverse_journal_entry(cap,self.employee.user)
        a,j,created=dispose_fixed_asset(a,disposal_date=date(2026,5,1),proceeds=Decimal('120.00'),finance_account=self.finance_account,reference='SALE-120',disposed_by=self.employee.user); self.assertTrue(created); self.assertEqual(j.total_debit,Decimal('120.00')); self.assertEqual(j.total_credit,Decimal('120.00')); self.assertEqual(j.lines.get(ledger_account__system_role=LedgerAccount.SYSTEM_ROLE.ASSET_DISPOSAL_GAIN).credit,Decimal('20.00')); self.assertEqual(a.status,FixedAsset.STATUS.DISPOSED)
    def test_bank_reconciliation_api_is_deferred_while_fixed_assets_remain_mounted(self):
        # Bank Reconciliation backend code is intentionally retained, but its
        # public API is deferred until the external bank-transaction ingestion
        # and reconciliation product workflow are defined.
        self.assertEqual(
            self.client.get('/api/v1/finance/bank-reconciliations', **self.headers).status_code,
            404,
        )
        self.assertEqual(
            self.client.get('/api/v1/finance/fixed-asset-categories', **self.headers).status_code,
            200,
        )
        self.assertEqual(
            self.client.get('/api/v1/finance/fixed-assets', **self.headers).status_code,
            200,
        )
