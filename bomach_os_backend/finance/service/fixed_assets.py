import calendar
from datetime import date
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from finance.models import FinanceAccount,FixedAsset,FixedAssetCategory,JournalEntry,JournalLine,LedgerAccount
from finance.service.accounting import _create_posted_source_journal,ensure_finance_account_ledger_account,get_system_ledger_account
from services.models.expenses import Expense
ZERO=Decimal('0.00'); CENT=Decimal('0.01')
def money(v): return (v or ZERO).quantize(CENT)
def _month_end(v): return date(v.year,v.month,calendar.monthrange(v.year,v.month)[1])
def _add_months(v,n):
    idx=v.year*12+v.month-1+n; y,m0=divmod(idx,12); m=m0+1; return date(y,m,min(v.day,calendar.monthrange(y,m)[1]))
def _months_between(a,b): return (b.year-a.year)*12+b.month-a.month
def _source_branch(e): return e.branch or (e.service_order.branch if e.service_order_id else None) or (e.finance_account.branch if e.finance_account_id else None)

def create_fixed_asset(*,category,source_expense,name,acquisition_date,acquisition_cost,created_by,description='',branch=None,residual_value=None,useful_life_months=None):
    with transaction.atomic():
        c=FixedAssetCategory.objects.select_for_update().select_related('asset_ledger_account','accumulated_depreciation_ledger_account','depreciation_expense_ledger_account').get(pk=category.pk)
        if not c.is_active: raise ValidationError('Fixed asset category is inactive.')
        e=Expense.objects.select_for_update().select_related('finance_account','branch','service_order__branch').get(pk=source_expense.pk)
        if e.cost_type!=Expense.COST_TYPE.CAPITAL_EXPENDITURE: raise ValidationError('Fixed assets require a capital-expenditure Expense.')
        if e.status!=Expense.STATUS.PAID: raise ValidationError('Fixed assets require a paid capital-expenditure Expense.')
        if not e.finance_account_id: raise ValidationError('Paid capital expenditure requires a Finance account.')
        cost=money(acquisition_cost)
        if cost<=ZERO: raise ValidationError('Acquisition cost must be positive.')
        residual=money(cost*money(c.default_residual_value_percent)/Decimal('100.00')) if residual_value is None else money(residual_value)
        if residual<ZERO or residual>cost: raise ValidationError('Residual value must be between zero and acquisition cost.')
        life=useful_life_months or c.default_useful_life_months
        if not life or life<=0: raise ValidationError('Useful life must be greater than zero.')
        sb=_source_branch(e); selected=branch or sb
        if branch and sb and branch.id!=sb.id: raise ValidationError('Fixed asset branch must match the source capital expenditure.')
        a=FixedAsset(name=name,description=description or '',category=c,branch=selected,source_expense=e,acquisition_date=acquisition_date,acquisition_cost=cost,residual_value=residual,useful_life_months=life,depreciation_method=c.default_depreciation_method,asset_ledger_account=c.asset_ledger_account,accumulated_depreciation_ledger_account=c.accumulated_depreciation_ledger_account,depreciation_expense_ledger_account=c.depreciation_expense_ledger_account,created_by=created_by); a.save(); return a

def capitalize_fixed_asset(asset,capitalized_by,capitalization_date=None):
    with transaction.atomic():
        a=FixedAsset.objects.select_for_update().select_related('source_expense__finance_account','source_expense__branch','source_expense__service_order__branch','category','branch').get(pk=asset.pk)
        existing=JournalEntry.objects.filter(source_type='fixed_asset',source_id=str(a.id),source_event='capitalization',status=JournalEntry.STATUS.POSTED).first()
        if existing: return a,existing,False
        if a.status!=FixedAsset.STATUS.DRAFT: raise ValidationError('Only draft fixed assets can be capitalized.')
        if not a.category.is_active: raise ValidationError('Inactive fixed-asset categories cannot be used for capitalization.')
        if not a.source_expense_id: raise ValidationError('Capitalization requires a source capital-expenditure Expense.')
        e=Expense.objects.select_for_update().select_related('finance_account').get(pk=a.source_expense_id)
        if e.cost_type!=Expense.COST_TYPE.CAPITAL_EXPENDITURE or e.status!=Expense.STATUS.PAID or not e.finance_account_id: raise ValidationError('Source Expense must remain a paid capital expenditure with a Finance account.')
        src=JournalEntry.objects.filter(source_type='expense',source_id=str(e.id),source_event='paid',status=JournalEntry.STATUS.POSTED).first()
        if not src: raise ValidationError('Source capital expenditure has no posted paid-expense journal.')
        capex=get_system_ledger_account(LedgerAccount.SYSTEM_ROLE.CAPITAL_EXPENDITURE_CLEARING)
        if money(src.lines.filter(ledger_account=capex).aggregate(total=Sum('debit'))['total'])<=ZERO: raise ValidationError('Source Expense journal did not debit Capital Expenditure Clearing.')
        other=money(FixedAsset.objects.filter(source_expense_id=e.id,status__in=[FixedAsset.STATUS.ACTIVE,FixedAsset.STATUS.FULLY_DEPRECIATED,FixedAsset.STATUS.DISPOSED]).exclude(pk=a.pk).aggregate(total=Sum('acquisition_cost'))['total'])
        if money(other+a.acquisition_cost)>money(e.amount): raise ValidationError('Capitalized fixed assets cannot exceed the source capital expenditure amount.')
        paid=e.paid_at.date() if e.paid_at else e.date; entry_date=capitalization_date or max(a.acquisition_date,paid)
        if entry_date<a.acquisition_date or entry_date<paid: raise ValidationError('Capitalization date cannot precede acquisition or paid Expense date.')
        j,created=_create_posted_source_journal(entry_date=entry_date,currency=e.finance_account.currency,lines=[{'ledger_account_id':a.asset_ledger_account_id,'debit':money(a.acquisition_cost),'credit':ZERO,'description':f'Capitalize {a.asset_number} - {a.name}'},{'ledger_account_id':capex.id,'debit':ZERO,'credit':money(a.acquisition_cost),'description':f'Clear capital expenditure for {a.asset_number}'}],entry_type=JournalEntry.ENTRY_TYPE.AUTOMATIC,source_type='fixed_asset',source_id=a.id,source_event='capitalization',reference=a.asset_number,memo=f'Fixed asset capitalization: {a.name}',branch=a.branch,created_by=capitalized_by)
        a.status=FixedAsset.STATUS.ACTIVE; a.capitalization_date=entry_date; a._workflow_via_service=True; a.save(update_fields=['status','capitalization_date','updated_at']); return a,j,created

def posted_depreciation_total(asset): return money(JournalLine.objects.filter(journal_entry__status=JournalEntry.STATUS.POSTED,journal_entry__source_type='fixed_asset',journal_entry__source_id=str(asset.id),journal_entry__source_event__startswith='depreciation:',ledger_account_id=asset.accumulated_depreciation_ledger_account_id).aggregate(total=Sum('credit'))['total'])
def fixed_asset_summary(asset):
    acc=posted_depreciation_total(asset); dep=money(asset.acquisition_cost-asset.residual_value); return {'acquisition_cost':money(asset.acquisition_cost),'residual_value':money(asset.residual_value),'depreciable_amount':dep,'accumulated_depreciation':acc,'book_value':money(asset.acquisition_cost-acc)}
def depreciation_schedule(asset):
    if not asset.capitalization_date: return []
    dep=money(asset.acquisition_cost-asset.residual_value); first=_month_end(_add_months(asset.capitalization_date,1)); events=set(JournalEntry.objects.filter(status=JournalEntry.STATUS.POSTED,source_type='fixed_asset',source_id=str(asset.id),source_event__startswith='depreciation:').values_list('source_event',flat=True)); rows=[]; prev=ZERO
    for i in range(asset.useful_life_months):
        end=_month_end(_add_months(first,i)); elapsed=i+1; target=dep if elapsed>=asset.useful_life_months else money(dep*Decimal(elapsed)/Decimal(asset.useful_life_months)); amount=money(target-prev); event=f'depreciation:{end:%Y-%m}'; rows.append({'period_end':end,'depreciation_amount':amount,'cumulative_depreciation':target,'closing_book_value':money(asset.acquisition_cost-target),'posted':event in events}); prev=target
    return rows

def post_fixed_asset_depreciation(asset,period_end,posted_by):
    with transaction.atomic():
        a=FixedAsset.objects.select_for_update().select_related('branch','source_expense__finance_account').get(pk=asset.pk)
        if a.status==FixedAsset.STATUS.FULLY_DEPRECIATED: raise ValidationError('This fixed asset is already fully depreciated.')
        if a.status!=FixedAsset.STATUS.ACTIVE or not a.capitalization_date: raise ValidationError('Only capitalized active fixed assets can be depreciated.')
        end=_month_end(period_end)
        if end!=period_end: raise ValidationError('Depreciation must be posted on a calendar month-end.')
        if end>timezone.localdate(): raise ValidationError('Future depreciation cannot be posted.')
        first=_month_end(_add_months(a.capitalization_date,1))
        if end<first: raise ValidationError('Depreciation starts at the first full month-end after capitalization.')
        event=f'depreciation:{end:%Y-%m}'; existing=JournalEntry.objects.filter(source_type='fixed_asset',source_id=str(a.id),source_event=event,status=JournalEntry.STATUS.POSTED).first()
        if existing: return a,existing,False
        latest=JournalEntry.objects.filter(source_type='fixed_asset',source_id=str(a.id),source_event__startswith='depreciation:',status=JournalEntry.STATUS.POSTED).order_by('-entry_date').first()
        if latest and end<=latest.entry_date: raise ValidationError('Depreciation periods must be posted once and in chronological order.')
        elapsed=min(_months_between(first,end)+1,a.useful_life_months); dep=money(a.acquisition_cost-a.residual_value); target=dep if elapsed>=a.useful_life_months else money(dep*Decimal(elapsed)/Decimal(a.useful_life_months)); already=posted_depreciation_total(a); amount=money(target-already)
        if amount<=ZERO: raise ValidationError('No depreciation remains to post for this period.')
        j,created=_create_posted_source_journal(entry_date=end,currency=a.currency,lines=[{'ledger_account_id':a.depreciation_expense_ledger_account_id,'debit':amount,'credit':ZERO,'description':f'Depreciation {a.asset_number} {end:%Y-%m}'},{'ledger_account_id':a.accumulated_depreciation_ledger_account_id,'debit':ZERO,'credit':amount,'description':f'Accumulated depreciation {a.asset_number}'}],entry_type=JournalEntry.ENTRY_TYPE.AUTOMATIC,source_type='fixed_asset',source_id=a.id,source_event=event,reference=a.asset_number,memo=f'Straight-line depreciation for {a.name} through {end:%Y-%m}',branch=a.branch,created_by=posted_by)
        if created and money(already+amount)>=dep: a.status=FixedAsset.STATUS.FULLY_DEPRECIATED; a._workflow_via_service=True; a.save(update_fields=['status','updated_at'])
        return a,j,created

def dispose_fixed_asset(asset,*,disposal_date,proceeds,disposed_by,finance_account=None,reference='',notes=''):
    with transaction.atomic():
        a=FixedAsset.objects.select_for_update().select_related('branch','source_expense__finance_account').get(pk=asset.pk)
        if a.status not in {FixedAsset.STATUS.ACTIVE,FixedAsset.STATUS.FULLY_DEPRECIATED}: raise ValidationError('Only active or fully depreciated fixed assets can be disposed.')
        if not a.capitalization_date or disposal_date<a.capitalization_date: raise ValidationError('Disposal date cannot precede capitalization.')
        latest=JournalEntry.objects.filter(source_type='fixed_asset',source_id=str(a.id),source_event__startswith='depreciation:',status=JournalEntry.STATUS.POSTED).order_by('-entry_date').first()
        if latest and disposal_date<latest.entry_date: raise ValidationError('Disposal date cannot predate the last posted depreciation journal.')
        existing=JournalEntry.objects.filter(source_type='fixed_asset',source_id=str(a.id),source_event='disposal',status=JournalEntry.STATUS.POSTED).first()
        if existing: return a,existing,False
        proceeds=money(proceeds)
        if proceeds<ZERO: raise ValidationError('Disposal proceeds cannot be negative.')
        selected=None; cash=None
        if proceeds>ZERO:
            if not finance_account: raise ValidationError('A Finance account is required when disposal proceeds are received.')
            selected=FinanceAccount.objects.select_for_update().select_related('branch','ledger_account').get(pk=finance_account.pk)
            if selected.currency.upper()!=a.currency.upper(): raise ValidationError('Disposal Finance account currency must match the fixed asset currency.')
            if a.branch_id and selected.branch_id and a.branch_id!=selected.branch_id: raise ValidationError('Disposal Finance account branch must match the fixed asset branch.')
            cash=ensure_finance_account_ledger_account(selected,disposed_by)
        elif finance_account: selected=FinanceAccount.objects.get(pk=finance_account.pk)
        acc=posted_depreciation_total(a); book=money(a.acquisition_cost-acc); gain=money(max(ZERO,proceeds-book)); loss=money(max(ZERO,book-proceeds)); gain_acct=get_system_ledger_account(LedgerAccount.SYSTEM_ROLE.ASSET_DISPOSAL_GAIN); loss_acct=get_system_ledger_account(LedgerAccount.SYSTEM_ROLE.ASSET_DISPOSAL_LOSS); lines=[]
        if acc>ZERO: lines.append({'ledger_account_id':a.accumulated_depreciation_ledger_account_id,'debit':acc,'credit':ZERO,'description':f'Remove accumulated depreciation {a.asset_number}'})
        if proceeds>ZERO: lines.append({'ledger_account_id':cash.id,'debit':proceeds,'credit':ZERO,'description':reference or f'Disposal proceeds {a.asset_number}'})
        if loss>ZERO: lines.append({'ledger_account_id':loss_acct.id,'debit':loss,'credit':ZERO,'description':f'Loss on disposal {a.asset_number}'})
        lines.append({'ledger_account_id':a.asset_ledger_account_id,'debit':ZERO,'credit':money(a.acquisition_cost),'description':f'Remove fixed asset cost {a.asset_number}'})
        if gain>ZERO: lines.append({'ledger_account_id':gain_acct.id,'debit':ZERO,'credit':gain,'description':f'Gain on disposal {a.asset_number}'})
        j,created=_create_posted_source_journal(entry_date=disposal_date,currency=a.currency,lines=lines,entry_type=JournalEntry.ENTRY_TYPE.AUTOMATIC,source_type='fixed_asset',source_id=a.id,source_event='disposal',reference=reference or a.asset_number,memo=notes or f'Dispose fixed asset {a.name}',branch=a.branch,created_by=disposed_by)
        a.status=FixedAsset.STATUS.DISPOSED; a.disposed_at=disposal_date; a.disposal_proceeds=proceeds; a.disposal_finance_account=selected; a.disposal_reference=reference or ''; a.disposal_notes=notes or ''; a._workflow_via_service=True; a.save(update_fields=['status','disposed_at','disposal_proceeds','disposal_finance_account','disposal_reference','disposal_notes','updated_at']); return a,j,created
