from datetime import date, datetime
from decimal import Decimal
from typing import Dict, List, Optional

from ninja import Schema


class PettyCashAdvanceIn(Schema):
    requester_id: Optional[int] = None
    custodian_id: Optional[int] = None
    branch_id: Optional[int] = None
    finance_account_id: int
    service_order_id: Optional[int] = None
    purpose: str
    amount_requested: Decimal
    due_date: date
    attachment: Optional[str] = None
    notes: str = ""


class PettyCashAdvanceUpdate(Schema):
    requester_id: Optional[int] = None
    custodian_id: Optional[int] = None
    branch_id: Optional[int] = None
    finance_account_id: Optional[int] = None
    service_order_id: Optional[int] = None
    purpose: Optional[str] = None
    amount_requested: Optional[Decimal] = None
    due_date: Optional[date] = None
    status: Optional[str] = None
    attachment: Optional[str] = None
    notes: Optional[str] = None


class PettyCashRejectIn(Schema):
    rejection_reason: str = ""


class PettyCashIssueIn(Schema):
    custodian_id: Optional[int] = None
    amount_issued: Optional[Decimal] = None
    issued_at: Optional[datetime] = None


class PettyCashRetirementLineIn(Schema):
    service_order_id: Optional[int] = None
    category: str = ""
    cost_type: str = "operating_expense"
    stage: str = ""
    description: str
    amount_spent: Decimal = Decimal("0.00")
    amount_returned: Decimal = Decimal("0.00")
    attachment: Optional[str] = None
    billable: bool = False
    client_visible: bool = False


class PettyCashRetireIn(Schema):
    lines: List[PettyCashRetirementLineIn]


class PettyCashRetirementLineOut(Schema):
    id: int
    advance_id: int
    service_order_id: Optional[int] = None
    service_order_number: str
    category: str
    cost_type: str
    stage: str
    description: str
    amount_spent: Decimal
    amount_returned: Decimal
    attachment: Optional[str] = None
    billable: bool
    client_visible: bool
    created_by_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def resolve_service_order_number(obj):
        return obj.service_order.order_number if obj.service_order else ""


class PettyCashAdvanceOut(Schema):
    id: int
    advance_number: str
    requester_id: int
    requester_name: str
    custodian_id: Optional[int] = None
    custodian_name: str
    branch_id: Optional[int] = None
    branch_name: str
    finance_account_id: int
    finance_account_name: str
    service_order_id: Optional[int] = None
    service_order_number: str
    service_name: str
    project_name: str
    purpose: str
    amount_requested: Decimal
    amount_issued: Decimal
    amount_retired: Decimal
    amount_returned: Decimal
    unretired_amount: Decimal
    due_date: date
    issued_at: Optional[datetime] = None
    retired_at: Optional[datetime] = None
    is_overdue: bool
    status: str
    status_display: str
    attachment: Optional[str] = None
    notes: str
    approved_by_id: Optional[int] = None
    approved_by_name: str
    approved_at: Optional[datetime] = None
    rejected_by_id: Optional[int] = None
    rejected_by_name: str
    rejected_at: Optional[datetime] = None
    rejection_reason: str
    issued_by_id: Optional[int] = None
    issued_by_name: str
    retired_by_id: Optional[int] = None
    retired_by_name: str
    created_by_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def _user_name(user):
        return (user.get_full_name() or user.email) if user else ""

    @staticmethod
    def resolve_requester_name(obj):
        return PettyCashAdvanceOut._user_name(obj.requester)

    @staticmethod
    def resolve_custodian_name(obj):
        return PettyCashAdvanceOut._user_name(obj.custodian)

    @staticmethod
    def resolve_branch_name(obj):
        return obj.branch.branch_name if obj.branch else ""

    @staticmethod
    def resolve_finance_account_name(obj):
        return obj.finance_account.display_name

    @staticmethod
    def resolve_service_order_number(obj):
        return obj.service_order.order_number if obj.service_order else ""

    @staticmethod
    def resolve_service_name(obj):
        return obj.service_order.service.name if obj.service_order else ""

    @staticmethod
    def resolve_project_name(obj):
        return obj.service_order.description if obj.service_order else ""

    @staticmethod
    def resolve_unretired_amount(obj):
        return obj.unretired_amount

    @staticmethod
    def resolve_is_overdue(obj):
        return obj.is_overdue

    @staticmethod
    def resolve_status_display(obj):
        return obj.get_status_display()

    @staticmethod
    def resolve_approved_by_name(obj):
        return PettyCashAdvanceOut._user_name(obj.approved_by)

    @staticmethod
    def resolve_rejected_by_name(obj):
        return PettyCashAdvanceOut._user_name(obj.rejected_by)

    @staticmethod
    def resolve_issued_by_name(obj):
        return PettyCashAdvanceOut._user_name(obj.issued_by)

    @staticmethod
    def resolve_retired_by_name(obj):
        return PettyCashAdvanceOut._user_name(obj.retired_by)


class PettyCashAccountSummaryOut(Schema):
    finance_account_id: int
    finance_account_name: str
    branch_id: Optional[int] = None
    branch_name: str
    opening_balance: Decimal
    issued_total: Decimal
    returned_total: Decimal
    calculated_balance: Decimal
    unretired_total: Decimal
    overdue_count: int
    replenishment_needed: bool


class PettyCashSummaryOut(Schema):
    issued_total: Decimal
    retired_total: Decimal
    returned_total: Decimal
    unretired_total: Decimal
    overdue_count: int
    replenishment_count: int
    status_counts: Dict[str, int]
    accounts: List[PettyCashAccountSummaryOut]
