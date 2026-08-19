from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from ninja import Schema


class LedgerAccountIn(Schema):
    code: str
    name: str
    account_type: str
    normal_balance: str
    parent_id: Optional[int] = None
    is_postable: bool = True
    system_role: Optional[str] = None
    description: str = ""
    is_active: bool = True


class LedgerAccountUpdate(Schema):
    code: Optional[str] = None
    name: Optional[str] = None
    account_type: Optional[str] = None
    normal_balance: Optional[str] = None
    parent_id: Optional[int] = None
    is_postable: Optional[bool] = None
    system_role: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class LedgerAccountOut(Schema):
    id: int
    code: str
    name: str
    account_type: str
    normal_balance: str
    parent_id: Optional[int] = None
    parent_code: str
    is_postable: bool
    system_role: Optional[str] = None
    description: str
    is_active: bool
    created_by_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def resolve_parent_code(obj):
        return obj.parent.code if obj.parent else ""


class FinanceAccountLedgerMapIn(Schema):
    ledger_account_id: int


class FinanceAccountLedgerMapOut(Schema):
    finance_account_id: int
    finance_account_name: str
    ledger_account_id: int
    ledger_account_code: str
    ledger_account_name: str


class JournalLineIn(Schema):
    ledger_account_id: int
    description: str = ""
    debit: Decimal = Decimal("0.00")
    credit: Decimal = Decimal("0.00")


class ManualJournalIn(Schema):
    entry_date: date
    currency: str = "NGN"
    branch_id: Optional[int] = None
    reference: str = ""
    memo: str = ""
    lines: List[JournalLineIn]


class ManualJournalUpdate(Schema):
    entry_date: Optional[date] = None
    currency: Optional[str] = None
    branch_id: Optional[int] = None
    reference: Optional[str] = None
    memo: Optional[str] = None
    lines: Optional[List[JournalLineIn]] = None


class JournalReverseIn(Schema):
    entry_date: Optional[date] = None
    memo: str = ""


class JournalLineOut(Schema):
    id: int
    line_order: int
    ledger_account_id: int
    ledger_account_code: str
    ledger_account_name: str
    description: str
    debit: Decimal
    credit: Decimal


class JournalEntryOut(Schema):
    id: int
    journal_number: str
    entry_date: date
    currency: str
    entry_type: str
    status: str
    branch_id: Optional[int] = None
    branch_name: str
    reference: str
    memo: str
    source_type: str
    source_id: str
    source_event: str
    reversal_of_id: Optional[int] = None
    is_reversed: bool
    total_debit: Decimal
    total_credit: Decimal
    line_count: int
    posted_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class JournalEntryDetailOut(JournalEntryOut):
    lines: List[JournalLineOut]


class GeneralLedgerLineOut(Schema):
    journal_entry_id: int
    journal_number: str
    entry_date: date
    currency: str
    branch_id: Optional[int] = None
    branch_name: str
    reference: str
    memo: str
    ledger_account_id: int
    ledger_account_code: str
    ledger_account_name: str
    description: str
    debit: Decimal
    credit: Decimal
    running_balance: Decimal


class TrialBalanceRowOut(Schema):
    ledger_account_id: int
    ledger_account_code: str
    ledger_account_name: str
    account_type: str
    normal_balance: str
    total_debit: Decimal
    total_credit: Decimal
    balance: Decimal


class TrialBalanceOut(Schema):
    as_of: date
    currency: str
    total_debit: Decimal
    total_credit: Decimal
    balanced: bool
    rows: List[TrialBalanceRowOut]
