from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from ninja import Schema


class FinanceSettingsOut(Schema):
    default_currency: str
    financial_year_start_month: int
    closed_through_date: Optional[date] = None
    journal_prefix: str
    draft_journal_warning_days: int
    large_manual_journal_review_threshold: Optional[Decimal] = None
    updated_by_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime


class FinanceSettingsUpdate(Schema):
    financial_year_start_month: Optional[int] = None
    closed_through_date: Optional[date] = None
    journal_prefix: Optional[str] = None
    draft_journal_warning_days: Optional[int] = None
    large_manual_journal_review_threshold: Optional[Decimal] = None
