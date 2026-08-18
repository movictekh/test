from typing import List, Optional

from django.db.models import Q
from django.shortcuts import get_object_or_404
from ninja import Query, Router
from ninja.pagination import LimitOffsetPagination, paginate

from finance.api.schemas import (
    FinanceExpenseIn,
    FinanceExpenseOut,
    FinanceExpensePayIn,
    FinanceExpenseRejectIn,
    FinanceExpenseUpdate,
)
from finance.models import FinanceAccount
from finance.service import (
    approve_finance_expense,
    handle_payment_exception,
    pay_finance_expense,
    reject_finance_expense,
)
from services.api.schema.others import MessageSchema
from services.models.expenses import Expense
from services.models.service import ServiceOrder
from user.models.branch import Branch
from user.models.roles import Department
from user.models.user import User
from user.utils.perm import require_permission


router = Router(tags=["Finance Expenses"])


def _branch_filter(branch_ids):
    return (
        Q(branch_id__in=branch_ids)
        | Q(service_order__branch_id__in=branch_ids)
        | Q(finance_account__branch_id__in=branch_ids)
    )


def _apply_branch_scope(request, qs):
    branch_ids = getattr(request, "_perm_branch_ids", [])
    if getattr(request, "_perm_scope", "branches") == "company" or not branch_ids:
        return qs
    return qs.filter(_branch_filter(branch_ids))


def _expense_queryset():
    return Expense.objects.select_related(
        "user",
        "department",
        "branch",
        "finance_account",
        "service_order",
        "service_order__service",
        "service_order__client",
        "service_order__client__user",
        "service_order__branch",
        "approved_by",
        "rejected_by",
        "paid_by",
    )


def _get_scoped_account(request, account_id):
    accounts = FinanceAccount.objects.filter(id=account_id)
    branch_ids = getattr(request, "_perm_branch_ids", [])
    if getattr(request, "_perm_scope", "branches") != "company" and branch_ids:
        accounts = accounts.filter(Q(branch_id__in=branch_ids) | Q(branch__isnull=True))
    return get_object_or_404(accounts)


def _get_scoped_order(request, order_id):
    orders = ServiceOrder.objects.select_related("branch", "service").filter(id=order_id)
    branch_ids = getattr(request, "_perm_branch_ids", [])
    if getattr(request, "_perm_scope", "branches") != "company" and branch_ids:
        orders = orders.filter(Q(branch_id__in=branch_ids) | Q(branch__isnull=True))
    return get_object_or_404(orders)


def _assign_expense_relations(request, expense, data):
    if "user_id" in data:
        user_id = data.pop("user_id")
        expense.user = get_object_or_404(User, id=user_id) if user_id else request.user
    if "department_id" in data:
        department_id = data.pop("department_id")
        expense.department = get_object_or_404(Department, id=department_id) if department_id else None
    if "branch_id" in data:
        branch_id = data.pop("branch_id")
        expense.branch = get_object_or_404(Branch, id=branch_id) if branch_id else None
    if "finance_account_id" in data:
        account_id = data.pop("finance_account_id")
        expense.finance_account = _get_scoped_account(request, account_id) if account_id else None
    if "service_order_id" in data:
        order_id = data.pop("service_order_id")
        expense.service_order = _get_scoped_order(request, order_id) if order_id else None


@router.get("/expenses", response=List[FinanceExpenseOut])
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("expenses", "list")
def list_finance_expenses(
    request,
    status: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    cost_type: Optional[str] = Query(None),
    branch_id: Optional[int] = Query(None),
    finance_account_id: Optional[int] = Query(None),
    service_order_id: Optional[int] = Query(None),
    department_id: Optional[int] = Query(None),
    user_id: Optional[int] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
):
    expenses = _apply_branch_scope(request, _expense_queryset())
    if status:
        expenses = expenses.filter(status=status)
    if category:
        expenses = expenses.filter(category=category)
    if cost_type:
        expenses = expenses.filter(cost_type=cost_type)
    if branch_id:
        expenses = expenses.filter(branch_id=branch_id)
    if finance_account_id:
        expenses = expenses.filter(finance_account_id=finance_account_id)
    if service_order_id:
        expenses = expenses.filter(service_order_id=service_order_id)
    if department_id:
        expenses = expenses.filter(department_id=department_id)
    if user_id:
        expenses = expenses.filter(user_id=user_id)
    if date_from:
        expenses = expenses.filter(date__gte=date_from)
    if date_to:
        expenses = expenses.filter(date__lte=date_to)
    if search:
        q = search.strip()
        expenses = expenses.filter(
            Q(expense_number__icontains=q)
            | Q(description__icontains=q)
            | Q(vendor__icontains=q)
            | Q(beneficiary__icontains=q)
            | Q(project_name__icontains=q)
            | Q(stage__icontains=q)
            | Q(service_order__order_number__icontains=q)
        )
    return expenses.distinct().order_by("-date", "-created_at")


@router.post("/expenses", response={201: FinanceExpenseOut, 400: MessageSchema})
@require_permission("expenses", "create")
def create_finance_expense(request, payload: FinanceExpenseIn):
    try:
        data = payload.dict()
        expense = Expense(user=request.user)
        _assign_expense_relations(request, expense, data)
        for field, value in data.items():
            setattr(expense, field, value)
        if expense.service_order and not expense.project_name:
            expense.project_name = expense.service_order.description
        if expense.service_order and not expense.branch:
            expense.branch = expense.service_order.branch
        expense.save()
        return 201, _expense_queryset().get(id=expense.id)
    except Exception as exc:
        return 400, {"detail": str(exc)}


@router.get("/expenses/{expense_id}", response={200: FinanceExpenseOut, 404: MessageSchema})
@require_permission("expenses", "view")
def get_finance_expense(request, expense_id: int):
    expense = get_object_or_404(_apply_branch_scope(request, _expense_queryset()), id=expense_id)
    return 200, expense


@router.patch("/expenses/{expense_id}", response={200: FinanceExpenseOut, 400: MessageSchema, 404: MessageSchema})
@require_permission("expenses", "update")
def update_finance_expense(request, expense_id: int, payload: FinanceExpenseUpdate):
    try:
        expense = get_object_or_404(_apply_branch_scope(request, _expense_queryset()), id=expense_id)
        data = payload.dict(exclude_unset=True)
        if "status" in data or "paid_at" in data:
            return 400, {"detail": "Use the approve, reject, or pay endpoint to change expense workflow status."}
        if expense.status != Expense.STATUS.PENDING:
            return 400, {"detail": "Only pending expenses can be updated."}
        _assign_expense_relations(request, expense, data)
        for field, value in data.items():
            setattr(expense, field, value)
        if expense.service_order and not expense.project_name:
            expense.project_name = expense.service_order.description
        if expense.service_order and not expense.branch:
            expense.branch = expense.service_order.branch
        expense.save()
        return 200, _expense_queryset().get(id=expense.id)
    except Exception as exc:
        return 400, {"detail": str(exc)}


@router.delete("/expenses/{expense_id}", response={200: MessageSchema, 404: MessageSchema})
@require_permission("expenses", "delete")
def delete_finance_expense(request, expense_id: int):
    expense = get_object_or_404(_apply_branch_scope(request, _expense_queryset()), id=expense_id)
    expense.delete()
    return 200, {"detail": "Expense deleted successfully"}


@router.post("/expenses/{expense_id}/approve", response={200: FinanceExpenseOut, 400: MessageSchema, 404: MessageSchema})
@require_permission("expenses", "approve")
def approve_finance_expense_endpoint(request, expense_id: int):
    try:
        expense = get_object_or_404(_apply_branch_scope(request, _expense_queryset()), id=expense_id)
        approved = approve_finance_expense(expense, request.user)
        return 200, _expense_queryset().get(id=approved.id)
    except Exception as exc:
        return 400, handle_payment_exception(exc)


@router.post("/expenses/{expense_id}/reject", response={200: FinanceExpenseOut, 400: MessageSchema, 404: MessageSchema})
@require_permission("expenses", "reject")
def reject_finance_expense_endpoint(request, expense_id: int, payload: FinanceExpenseRejectIn):
    try:
        expense = get_object_or_404(_apply_branch_scope(request, _expense_queryset()), id=expense_id)
        rejected = reject_finance_expense(expense, request.user, payload.rejection_reason)
        return 200, _expense_queryset().get(id=rejected.id)
    except Exception as exc:
        return 400, handle_payment_exception(exc)


@router.post("/expenses/{expense_id}/pay", response={200: FinanceExpenseOut, 400: MessageSchema, 404: MessageSchema})
@require_permission("expenses", "pay")
def pay_finance_expense_endpoint(request, expense_id: int, payload: FinanceExpensePayIn):
    try:
        expense = get_object_or_404(_apply_branch_scope(request, _expense_queryset()), id=expense_id)
        account = _get_scoped_account(request, payload.finance_account_id)
        paid = pay_finance_expense(
            expense,
            request.user,
            account,
            paid_at=payload.paid_at,
            payment_reference=payload.payment_reference,
        )
        return 200, _expense_queryset().get(id=paid.id)
    except Exception as exc:
        return 400, handle_payment_exception(exc)
