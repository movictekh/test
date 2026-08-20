from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from ninja import Schema


class FinanceExpenseIn(Schema):
    user_id: Optional[int] = None
    department_id: Optional[int] = None
    branch_id: Optional[int] = None
    finance_account_id: Optional[int] = None
    service_order_id: Optional[int] = None
    date: date
    description: str
    amount: Decimal
    vendor: str = ""
    beneficiary: str = ""
    category: str = "other"
    cost_type: str = "operating_expense"
    project_name: str = ""
    stage: str = ""
    billable: bool = False
    client_visible: bool = False
    attachment: Optional[str] = None


class FinanceExpenseUpdate(Schema):
    user_id: Optional[int] = None
    department_id: Optional[int] = None
    branch_id: Optional[int] = None
    finance_account_id: Optional[int] = None
    service_order_id: Optional[int] = None
    date: Optional[date] = None
    description: Optional[str] = None
    amount: Optional[Decimal] = None
    vendor: Optional[str] = None
    beneficiary: Optional[str] = None
    category: Optional[str] = None
    cost_type: Optional[str] = None
    project_name: Optional[str] = None
    stage: Optional[str] = None
    billable: Optional[bool] = None
    client_visible: Optional[bool] = None
    status: Optional[str] = None
    attachment: Optional[str] = None
    paid_at: Optional[datetime] = None


class FinanceExpenseRejectIn(Schema):
    rejection_reason: str = ""


class FinanceExpensePayIn(Schema):
    finance_account_id: int
    paid_at: Optional[datetime] = None
    payment_reference: str = ""


class FinanceExpenseOut(Schema):
    id: int
    expense_number: str
    user_id: int
    requester_name: str
    department_id: Optional[int] = None
    department_name: str
    branch_id: Optional[int] = None
    branch_name: str
    finance_account_id: Optional[int] = None
    finance_account_name: str
    service_order_id: Optional[int] = None
    service_order_number: str
    service_name: str
    date: date
    description: str
    amount: Decimal
    vendor: Optional[str] = None
    beneficiary: str
    category: str
    category_display: str
    cost_type: str
    cost_type_display: str
    project_name: str
    stage: str
    billable: bool
    client_visible: bool
    status: str
    status_display: str
    approved_by_id: Optional[int] = None
    approved_by_name: str
    approved_at: Optional[datetime] = None
    rejected_by_id: Optional[int] = None
    rejected_by_name: str
    rejected_at: Optional[datetime] = None
    rejection_reason: str
    paid_by_id: Optional[int] = None
    paid_by_name: str
    payment_reference: str
    attachment: Optional[str] = None
    paid_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def resolve_expense_number(obj):
        return obj.expense_number or f"EXP-{obj.id}"

    @staticmethod
    def resolve_requester_name(obj):
        return obj.user.get_full_name() or obj.user.email

    @staticmethod
    def resolve_department_name(obj):
        return obj.department.name if obj.department else ""

    @staticmethod
    def resolve_branch_name(obj):
        return obj.branch.branch_name if obj.branch else ""

    @staticmethod
    def resolve_finance_account_name(obj):
        return obj.finance_account.display_name if obj.finance_account else ""

    @staticmethod
    def resolve_service_order_number(obj):
        return obj.service_order.order_number if obj.service_order else ""

    @staticmethod
    def resolve_service_name(obj):
        return obj.service_order.service.name if obj.service_order else ""

    @staticmethod
    def resolve_category_display(obj):
        return obj.get_category_display()

    @staticmethod
    def resolve_cost_type_display(obj):
        return obj.get_cost_type_display()

    @staticmethod
    def resolve_status_display(obj):
        return obj.get_status_display()

    @staticmethod
    def resolve_approved_by_name(obj):
        return (obj.approved_by.get_full_name() or obj.approved_by.email) if obj.approved_by else ""

    @staticmethod
    def resolve_rejected_by_name(obj):
        return (obj.rejected_by.get_full_name() or obj.rejected_by.email) if obj.rejected_by else ""

    @staticmethod
    def resolve_paid_by_name(obj):
        return (obj.paid_by.get_full_name() or obj.paid_by.email) if obj.paid_by else ""
