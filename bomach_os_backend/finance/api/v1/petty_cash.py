from collections import Counter
from datetime import date
from decimal import Decimal
from typing import List, Optional

from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja import Query, Router
from ninja.pagination import LimitOffsetPagination, paginate

from finance.api.schemas import (
    PettyCashAdvanceIn,
    PettyCashAdvanceOut,
    PettyCashAdvanceUpdate,
    PettyCashIssueIn,
    PettyCashRejectIn,
    PettyCashRetireIn,
    PettyCashRetirementLineOut,
    PettyCashSummaryOut,
)
from finance.models import FinanceAccount, PettyCashAdvance, PettyCashRetirementLine
from finance.service import (
    approve_petty_cash_advance,
    cancel_petty_cash_advance,
    handle_payment_exception,
    issue_petty_cash_advance,
    reject_petty_cash_advance,
    retire_petty_cash_advance,
)
from shared.api.schema import MessageSchema
from services.models.service import ServiceOrder
from domains.organization.models.branch import Branch
from user.models.user import User
from system.authorization import require_permission

router = Router(tags=["Finance Petty Cash"])


def _money(value):
    return (value or Decimal("0.00")).quantize(Decimal("0.01"))


def _branch_filter(branch_ids):
    return (
        Q(branch_id__in=branch_ids)
        | Q(finance_account__branch_id__in=branch_ids)
        | Q(service_order__branch_id__in=branch_ids)
    )


def _apply_branch_scope(request, qs):
    branch_ids = getattr(request, "_perm_branch_ids", [])
    if getattr(request, "_perm_scope", "branches") == "company" or not branch_ids:
        return qs
    return qs.filter(_branch_filter(branch_ids))


def _advance_queryset():
    return PettyCashAdvance.objects.select_related(
        "requester",
        "custodian",
        "branch",
        "finance_account",
        "finance_account__branch",
        "service_order",
        "service_order__service",
        "service_order__branch",
        "approved_by",
        "rejected_by",
        "issued_by",
        "retired_by",
        "created_by",
    )


def _line_queryset():
    return PettyCashRetirementLine.objects.select_related(
        "advance",
        "advance__requester",
        "advance__finance_account",
        "service_order",
        "service_order__service",
        "created_by",
    )


def _get_user(user_id):
    return get_object_or_404(User, id=user_id) if user_id else None


def _get_scoped_branch(request, branch_id):
    branches = Branch.objects.filter(id=branch_id)
    branch_ids = getattr(request, "_perm_branch_ids", [])
    if getattr(request, "_perm_scope", "branches") != "company" and branch_ids:
        branches = branches.filter(id__in=branch_ids)
    return get_object_or_404(branches)


def _get_scoped_cash_account(request, account_id):
    accounts = FinanceAccount.objects.filter(
        id=account_id,
        is_active=True,
        account_type=FinanceAccount.ACCOUNT_TYPE.CASH,
    )
    branch_ids = getattr(request, "_perm_branch_ids", [])
    if getattr(request, "_perm_scope", "branches") != "company" and branch_ids:
        accounts = accounts.filter(Q(branch_id__in=branch_ids) | Q(branch__isnull=True))
    return get_object_or_404(accounts)


def _get_scoped_order(request, order_id):
    orders = ServiceOrder.objects.select_related("branch", "service").filter(
        id=order_id
    )
    branch_ids = getattr(request, "_perm_branch_ids", [])
    if getattr(request, "_perm_scope", "branches") != "company" and branch_ids:
        orders = orders.filter(Q(branch_id__in=branch_ids) | Q(branch__isnull=True))
    return get_object_or_404(orders)


def _assign_advance_relations(request, advance, data):
    if "requester_id" in data:
        requester_id = data.pop("requester_id")
        advance.requester = _get_user(requester_id) or request.user
    if "custodian_id" in data:
        advance.custodian = _get_user(data.pop("custodian_id"))
    if "branch_id" in data:
        branch_id = data.pop("branch_id")
        advance.branch = _get_scoped_branch(request, branch_id) if branch_id else None
    if "finance_account_id" in data:
        account_id = data.pop("finance_account_id")
        advance.finance_account = (
            _get_scoped_cash_account(request, account_id) if account_id else None
        )
    if "service_order_id" in data:
        order_id = data.pop("service_order_id")
        advance.service_order = (
            _get_scoped_order(request, order_id) if order_id else None
        )


@router.get("/petty-cash/advances", response=List[PettyCashAdvanceOut])
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("petty_cash", "list")
def list_petty_cash_advances(
    request,
    status: Optional[str] = Query(None),
    requester_id: Optional[int] = Query(None),
    custodian_id: Optional[int] = Query(None),
    finance_account_id: Optional[int] = Query(None),
    branch_id: Optional[int] = Query(None),
    service_order_id: Optional[int] = Query(None),
    due_from: Optional[date] = Query(None),
    due_to: Optional[date] = Query(None),
    overdue: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
):
    advances = _apply_branch_scope(request, _advance_queryset())
    if status:
        advances = advances.filter(status=status)
    if requester_id:
        advances = advances.filter(requester_id=requester_id)
    if custodian_id:
        advances = advances.filter(custodian_id=custodian_id)
    if finance_account_id:
        advances = advances.filter(finance_account_id=finance_account_id)
    if branch_id:
        advances = advances.filter(
            Q(branch_id=branch_id)
            | Q(finance_account__branch_id=branch_id)
            | Q(service_order__branch_id=branch_id)
        )
    if service_order_id:
        advances = advances.filter(service_order_id=service_order_id)
    if due_from:
        advances = advances.filter(due_date__gte=due_from)
    if due_to:
        advances = advances.filter(due_date__lte=due_to)
    if overdue is not None:
        overdue_filter = Q(
            status__in=[
                PettyCashAdvance.STATUS.ISSUED,
                PettyCashAdvance.STATUS.PARTIALLY_RETIRED,
            ],
            due_date__lt=timezone.localdate(),
        )
        advances = (
            advances.filter(overdue_filter)
            if overdue
            else advances.exclude(overdue_filter)
        )
    if search:
        q = search.strip()
        advances = advances.filter(
            Q(advance_number__icontains=q)
            | Q(purpose__icontains=q)
            | Q(notes__icontains=q)
            | Q(requester__first_name__icontains=q)
            | Q(requester__last_name__icontains=q)
            | Q(requester__email__icontains=q)
            | Q(service_order__order_number__icontains=q)
            | Q(service_order__description__icontains=q)
            | Q(finance_account__display_name__icontains=q)
        )
    return advances.distinct().order_by("-created_at")


@router.post(
    "/petty-cash/advances", response={201: PettyCashAdvanceOut, 400: MessageSchema}
)
@require_permission("petty_cash", "create")
def create_petty_cash_advance(request, payload: PettyCashAdvanceIn):
    try:
        data = payload.dict()
        advance = PettyCashAdvance(requester=request.user, created_by=request.user)
        _assign_advance_relations(request, advance, data)
        for field, value in data.items():
            setattr(advance, field, value)
        advance.save()
        return 201, _advance_queryset().get(id=advance.id)
    except Exception as exc:
        return 400, handle_payment_exception(exc)


@router.get(
    "/petty-cash/advances/{advance_id}",
    response={200: PettyCashAdvanceOut, 404: MessageSchema},
)
@require_permission("petty_cash", "view")
def get_petty_cash_advance(request, advance_id: int):
    advance = get_object_or_404(
        _apply_branch_scope(request, _advance_queryset()), id=advance_id
    )
    return 200, advance


@router.patch(
    "/petty-cash/advances/{advance_id}",
    response={200: PettyCashAdvanceOut, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("petty_cash", "update")
def update_petty_cash_advance(
    request, advance_id: int, payload: PettyCashAdvanceUpdate
):
    try:
        advance = get_object_or_404(
            _apply_branch_scope(request, _advance_queryset()), id=advance_id
        )
        data = payload.dict(exclude_unset=True)
        if "status" in data:
            return 400, {
                "detail": "Use the petty cash workflow endpoints to change status."
            }
        if advance.status != PettyCashAdvance.STATUS.REQUESTED:
            return 400, {"detail": "Only requested petty cash advances can be updated."}
        _assign_advance_relations(request, advance, data)
        for field, value in data.items():
            setattr(advance, field, value)
        advance.save()
        return 200, _advance_queryset().get(id=advance.id)
    except Exception as exc:
        return 400, handle_payment_exception(exc)


@router.post(
    "/petty-cash/advances/{advance_id}/approve",
    response={200: PettyCashAdvanceOut, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("petty_cash", "approve")
def approve_petty_cash_advance_endpoint(request, advance_id: int):
    try:
        advance = get_object_or_404(
            _apply_branch_scope(request, _advance_queryset()), id=advance_id
        )
        approved = approve_petty_cash_advance(advance, request.user)
        return 200, _advance_queryset().get(id=approved.id)
    except Exception as exc:
        return 400, handle_payment_exception(exc)


@router.post(
    "/petty-cash/advances/{advance_id}/reject",
    response={200: PettyCashAdvanceOut, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("petty_cash", "reject")
def reject_petty_cash_advance_endpoint(
    request, advance_id: int, payload: PettyCashRejectIn
):
    try:
        advance = get_object_or_404(
            _apply_branch_scope(request, _advance_queryset()), id=advance_id
        )
        rejected = reject_petty_cash_advance(
            advance, request.user, payload.rejection_reason
        )
        return 200, _advance_queryset().get(id=rejected.id)
    except Exception as exc:
        return 400, handle_payment_exception(exc)


@router.post(
    "/petty-cash/advances/{advance_id}/issue",
    response={200: PettyCashAdvanceOut, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("petty_cash", "issue")
def issue_petty_cash_advance_endpoint(
    request, advance_id: int, payload: PettyCashIssueIn
):
    try:
        advance = get_object_or_404(
            _apply_branch_scope(request, _advance_queryset()), id=advance_id
        )
        custodian = _get_user(payload.custodian_id) if payload.custodian_id else None
        issued = issue_petty_cash_advance(
            advance,
            request.user,
            custodian=custodian,
            amount_issued=payload.amount_issued,
            issued_at=payload.issued_at,
        )
        return 200, _advance_queryset().get(id=issued.id)
    except Exception as exc:
        return 400, handle_payment_exception(exc)


@router.post(
    "/petty-cash/advances/{advance_id}/retire",
    response={200: PettyCashAdvanceOut, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("petty_cash", "retire")
def retire_petty_cash_advance_endpoint(
    request, advance_id: int, payload: PettyCashRetireIn
):
    try:
        advance = get_object_or_404(
            _apply_branch_scope(request, _advance_queryset()), id=advance_id
        )
        line_payloads = [line.dict() for line in payload.lines]
        retired, _ = retire_petty_cash_advance(advance, request.user, line_payloads)
        return 200, _advance_queryset().get(id=retired.id)
    except Exception as exc:
        return 400, handle_payment_exception(exc)


@router.post(
    "/petty-cash/advances/{advance_id}/cancel",
    response={200: PettyCashAdvanceOut, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("petty_cash", "cancel")
def cancel_petty_cash_advance_endpoint(request, advance_id: int):
    try:
        advance = get_object_or_404(
            _apply_branch_scope(request, _advance_queryset()), id=advance_id
        )
        cancelled = cancel_petty_cash_advance(advance, request.user)
        return 200, _advance_queryset().get(id=cancelled.id)
    except Exception as exc:
        return 400, handle_payment_exception(exc)


@router.get(
    "/petty-cash/advances/{advance_id}/retirement-lines",
    response=List[PettyCashRetirementLineOut],
)
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("petty_cash", "view")
def list_petty_cash_retirement_lines(request, advance_id: int):
    advance = get_object_or_404(
        _apply_branch_scope(request, _advance_queryset()), id=advance_id
    )
    return _line_queryset().filter(advance=advance).order_by("-created_at")


@router.get("/petty-cash/summary", response=PettyCashSummaryOut)
@require_permission("petty_cash", "list")
def petty_cash_summary(
    request,
    branch_id: Optional[int] = Query(None),
    finance_account_id: Optional[int] = Query(None),
):
    advances = _apply_branch_scope(request, _advance_queryset())
    accounts = FinanceAccount.objects.filter(
        account_type=FinanceAccount.ACCOUNT_TYPE.CASH, is_active=True
    )
    branch_ids = getattr(request, "_perm_branch_ids", [])
    if getattr(request, "_perm_scope", "branches") != "company" and branch_ids:
        accounts = accounts.filter(Q(branch_id__in=branch_ids) | Q(branch__isnull=True))
    if branch_id:
        advances = advances.filter(
            Q(branch_id=branch_id)
            | Q(finance_account__branch_id=branch_id)
            | Q(service_order__branch_id=branch_id)
        )
        accounts = accounts.filter(branch_id=branch_id)
    if finance_account_id:
        advances = advances.filter(finance_account_id=finance_account_id)
        accounts = accounts.filter(id=finance_account_id)

    open_statuses = [
        PettyCashAdvance.STATUS.ISSUED,
        PettyCashAdvance.STATUS.PARTIALLY_RETIRED,
    ]
    active_statuses = open_statuses + [PettyCashAdvance.STATUS.RETIRED]
    issued_total = _money(
        advances.filter(status__in=active_statuses).aggregate(
            total=Sum("amount_issued")
        )["total"]
    )
    retired_total = _money(
        advances.filter(status__in=active_statuses).aggregate(
            total=Sum("amount_retired")
        )["total"]
    )
    returned_total = _money(
        advances.filter(status__in=active_statuses).aggregate(
            total=Sum("amount_returned")
        )["total"]
    )
    unretired_total = _money(
        sum(
            advance.unretired_amount
            for advance in advances.filter(status__in=open_statuses)
        )
    )
    overdue_q = advances.filter(
        status__in=open_statuses, due_date__lt=timezone.localdate()
    )
    status_counts = Counter(advances.values_list("status", flat=True))

    account_rows = []
    replenishment_count = 0
    for account in accounts.select_related("branch").order_by("display_name"):
        account_advances = advances.filter(finance_account=account)
        account_issued = _money(
            account_advances.filter(status__in=active_statuses).aggregate(
                total=Sum("amount_issued")
            )["total"]
        )
        account_returned = _money(
            account_advances.filter(status__in=active_statuses).aggregate(
                total=Sum("amount_returned")
            )["total"]
        )
        account_unretired = _money(
            sum(
                advance.unretired_amount
                for advance in account_advances.filter(status__in=open_statuses)
            )
        )
        calculated_balance = _money(
            account.opening_balance - account_issued + account_returned
        )
        replenishment_needed = calculated_balance <= _money(
            account.opening_balance * Decimal("0.25")
        )
        if replenishment_needed:
            replenishment_count += 1
        account_rows.append(
            {
                "finance_account_id": account.id,
                "finance_account_name": account.display_name,
                "branch_id": account.branch_id,
                "branch_name": account.branch.branch_name if account.branch else "",
                "opening_balance": _money(account.opening_balance),
                "issued_total": account_issued,
                "returned_total": account_returned,
                "calculated_balance": calculated_balance,
                "unretired_total": account_unretired,
                "overdue_count": account_advances.filter(
                    status__in=open_statuses, due_date__lt=timezone.localdate()
                ).count(),
                "replenishment_needed": replenishment_needed,
            }
        )

    return {
        "issued_total": issued_total,
        "retired_total": retired_total,
        "returned_total": returned_total,
        "unretired_total": unretired_total,
        "overdue_count": overdue_q.count(),
        "replenishment_count": replenishment_count,
        "status_counts": dict(status_counts),
        "accounts": account_rows,
    }
