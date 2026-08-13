from datetime import datetime
from typing import Optional

from ninja import Schema


class FinanceAccountIn(Schema):
    account_type: str = "bank"
    display_name: str
    currency: str = "NGN"
    branch_id: Optional[int] = None
    bank_name: str = ""
    account_number: str = ""
    account_name: str = ""
    notes: str = ""
    is_active: bool = True


class FinanceAccountUpdate(Schema):
    account_type: Optional[str] = None
    display_name: Optional[str] = None
    currency: Optional[str] = None
    branch_id: Optional[int] = None
    bank_name: Optional[str] = None
    account_number: Optional[str] = None
    account_name: Optional[str] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None


class FinanceAccountOut(Schema):
    id: int
    account_type: str
    account_type_display: str
    display_name: str
    currency: str
    branch_id: Optional[int] = None
    branch_name: str
    bank_name: str
    account_number: str
    account_name: str
    notes: str
    is_active: bool
    created_by_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def resolve_account_type_display(obj):
        return obj.get_account_type_display()

    @staticmethod
    def resolve_branch_name(obj):
        return obj.branch.branch_name if obj.branch else ""
