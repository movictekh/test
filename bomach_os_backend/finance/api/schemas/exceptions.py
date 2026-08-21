from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from ninja import Schema


class FinanceExceptionOut(Schema):
    key: str
    severity: str
    category: str
    title: str
    detail: str
    entity_type: str
    entity_id: int
    reference: str
    branch_id: Optional[int] = None
    branch_name: str
    relevant_date: date
    amount: Optional[Decimal] = None
    action_path: str


class FinanceExceptionSummaryOut(Schema):
    generated_at: datetime
    total_count: int
    critical_count: int
    warning_count: int
    info_count: int
    category_counts: dict
