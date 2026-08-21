from typing import List, Optional

from django.db.models import Q
from django.shortcuts import get_object_or_404
from ninja import Query, Router
from ninja.pagination import LimitOffsetPagination, paginate

from finance.api.schemas import (
    PayrollCancelIn,
    PayrollManualItemsReplaceIn,
    PayrollPayIn,
    PayrollRejectIn,
    PayrollRunDetailOut,
    PayrollRunIn,
    PayrollRunOut,
    PayrollRunUpdate,
)
from finance.models import FinanceAccount, PayrollLine, PayrollRun
from finance.service import (
    approve_payroll_run,
    calculate_payroll_run,
    cancel_payroll_run,
    handle_payment_exception,
    pay_payroll_run,
    reject_payroll_run,
    replace_manual_payroll_items,
    submit_payroll_run,
)
from services.api.schema.others import MessageSchema
from user.models.branch import Branch
from user.utils.perm import require_permission

router = Router(tags=["Finance Payroll"])


def _user_name(user):
    if not user:
        return ""
    return user.get_full_name() or user.email or user.username


def _mask_account_number(value):
    value = str(value or "")
    if not value:
        return ""
    if len(value) <= 4:
        return "*" * len(value)
    return ("*" * (len(value) - 4)) + value[-4:]


def _run_queryset():
    return PayrollRun.objects.select_related(
        "branch",
        "finance_account",
        "calculated_by",
        "submitted_by",
        "approved_by",
        "rejected_by",
        "paid_by",
        "cancelled_by",
        "created_by",
    ).prefetch_related(
        "lines",
        "lines__items",
    )


def _apply_run_scope(request, runs):
    branch_ids = getattr(request, "_perm_branch_ids", [])
    if getattr(request, "_perm_scope", "branches") == "company" or not branch_ids:
        return runs

    return runs.filter(branch_id__in=branch_ids)


def _get_run(request, run_id):
    return get_object_or_404(_apply_run_scope(request, _run_queryset()), id=run_id)


def _get_scoped_branch(request, branch_id):
    branches = Branch.objects.filter(id=branch_id)
    branch_ids = getattr(request, "_perm_branch_ids", [])
    if getattr(request, "_perm_scope", "branches") != "company" and branch_ids:
        branches = branches.filter(id__in=branch_ids)
    return get_object_or_404(branches)


def _get_scoped_account(request, account_id):
    accounts = FinanceAccount.objects.filter(id=account_id, is_active=True)
    branch_ids = getattr(request, "_perm_branch_ids", [])
    if getattr(request, "_perm_scope", "branches") != "company" and branch_ids:
        accounts = accounts.filter(Q(branch_id__in=branch_ids) | Q(branch__isnull=True))
    return get_object_or_404(accounts)


def _line_item_out(item):
    return {
        "id": item.id,
        "item_type": item.item_type,
        "category": item.category,
        "name": item.name,
        "amount": item.amount,
        "source_type": item.source_type,
        "source_reference": item.source_reference,
        "is_taxable": item.is_taxable,
        "is_statutory": item.is_statutory,
        "notes": item.notes,
        "sort_order": item.sort_order,
    }


def _line_out(line):
    return {
        "id": line.id,
        "employee_id": line.employee_id,
        "employee_number": line.employee_number,
        "employee_name": line.employee_name,
        "designation": line.designation,
        "branch_name": line.branch_name,
        "department_name": line.department_name,
        "salary_frequency": line.salary_frequency,
        "bank_name": line.bank_name,
        "account_number_masked": _mask_account_number(line.account_number),
        "missing_bank_details": line.missing_bank_details,
        "gross_salary_snapshot": line.gross_salary_snapshot,
        "gross_pay": line.gross_pay,
        "total_deductions": line.total_deductions,
        "net_pay": line.net_pay,
        "items": [_line_item_out(item) for item in line.items.all()],
    }


def _run_out(payroll_run):
    lines = list(payroll_run.lines.all())
    return {
        "id": payroll_run.id,
        "run_number": payroll_run.run_number,
        "period_month": payroll_run.period_month,
        "period_year": payroll_run.period_year,
        "period_display": payroll_run.period_display,
        "scheduled_payment_date": payroll_run.scheduled_payment_date,
        "branch_id": payroll_run.branch_id,
        "branch_name": payroll_run.branch.branch_name if payroll_run.branch else "",
        "finance_account_id": payroll_run.finance_account_id,
        "finance_account_name": (
            payroll_run.finance_account.display_name
            if payroll_run.finance_account
            else ""
        ),
        "status": payroll_run.status,
        "status_display": payroll_run.get_status_display(),
        "employee_count": payroll_run.employee_count,
        "missing_bank_details_count": sum(
            1 for line in lines if line.missing_bank_details
        ),
        "gross_pay": payroll_run.gross_pay,
        "total_deductions": payroll_run.total_deductions,
        "net_pay": payroll_run.net_pay,
        "notes": payroll_run.notes,
        "calculated_by_name": _user_name(payroll_run.calculated_by),
        "calculated_at": payroll_run.calculated_at,
        "submitted_by_name": _user_name(payroll_run.submitted_by),
        "submitted_at": payroll_run.submitted_at,
        "approved_by_name": _user_name(payroll_run.approved_by),
        "approved_at": payroll_run.approved_at,
        "rejected_by_name": _user_name(payroll_run.rejected_by),
        "rejected_at": payroll_run.rejected_at,
        "rejection_reason": payroll_run.rejection_reason,
        "paid_by_name": _user_name(payroll_run.paid_by),
        "paid_at": payroll_run.paid_at,
        "payment_reference": payroll_run.payment_reference,
        "cancelled_by_name": _user_name(payroll_run.cancelled_by),
        "cancelled_at": payroll_run.cancelled_at,
        "cancellation_reason": payroll_run.cancellation_reason,
        "created_by_name": _user_name(payroll_run.created_by),
        "created_at": payroll_run.created_at,
        "updated_at": payroll_run.updated_at,
    }


def _run_detail(payroll_run):
    data = _run_out(payroll_run)
    data["lines"] = [_line_out(line) for line in payroll_run.lines.all()]
    return data


def _active_period_conflict(period_year, period_month, branch):
    active = PayrollRun.objects.exclude(status=PayrollRun.STATUS.CANCELLED).filter(
        period_year=period_year,
        period_month=period_month,
    )

    if branch is None:
        # Company payroll and branch payrolls must never cover the same month.
        return active.exists()

    # A branch run conflicts with a company run or another run for this branch.
    return active.filter(Q(branch__isnull=True) | Q(branch=branch)).exists()


@router.get("/payroll", response=List[PayrollRunOut])
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("finance_payroll", "list")
def list_payroll_runs(
    request,
    period_year: Optional[int] = Query(None),
    period_month: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    branch_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
):
    runs = _apply_run_scope(request, _run_queryset())

    if period_year:
        runs = runs.filter(period_year=period_year)
    if period_month:
        runs = runs.filter(period_month=period_month)
    if status:
        runs = runs.filter(status=status)
    if branch_id:
        # The base permission scope has already limited this queryset.
        runs = runs.filter(branch_id=branch_id)
    if search:
        q = search.strip()
        runs = runs.filter(
            Q(run_number__icontains=q)
            | Q(notes__icontains=q)
            | Q(branch__branch_name__icontains=q)
        )

    return [
        _run_out(run)
        for run in runs.order_by("-period_year", "-period_month", "-created_at")
    ]


@router.post("/payroll", response={201: PayrollRunOut, 400: MessageSchema})
@require_permission("finance_payroll", "create")
def create_payroll_run(request, payload: PayrollRunIn):
    try:
        data = payload.dict()
        branch_id = data.pop("branch_id", None)

        branch_ids = getattr(request, "_perm_branch_ids", [])
        is_company_scope = getattr(request, "_perm_scope", "branches") == "company"

        if not is_company_scope and branch_ids and not branch_id:
            return 400, {
                "detail": "Branch-scoped payroll creation requires a branch_id."
            }

        branch = _get_scoped_branch(request, branch_id) if branch_id else None

        if _active_period_conflict(
            data["period_year"],
            data["period_month"],
            branch,
        ):
            return 400, {
                "detail": "An active payroll run already covers this payroll period and scope."
            }

        payroll_run = PayrollRun(
            **data,
            branch=branch,
            created_by=request.user,
        )
        payroll_run.save()
        return 201, _run_out(_run_queryset().get(id=payroll_run.id))
    except Exception as exc:
        return 400, handle_payment_exception(exc)


@router.get(
    "/payroll/{run_id}",
    response={200: PayrollRunDetailOut, 404: MessageSchema},
)
@require_permission("finance_payroll", "view")
def get_payroll_run(request, run_id: int):
    payroll_run = _get_run(request, run_id)
    return 200, _run_detail(payroll_run)


@router.patch(
    "/payroll/{run_id}",
    response={200: PayrollRunOut, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("finance_payroll", "update")
def update_payroll_run(request, run_id: int, payload: PayrollRunUpdate):
    payroll_run = _get_run(request, run_id)
    try:
        if payroll_run.status not in {
            PayrollRun.STATUS.DRAFT,
            PayrollRun.STATUS.CALCULATED,
            PayrollRun.STATUS.REJECTED,
        }:
            return 400, {
                "detail": "Only draft, calculated, or rejected payroll runs can be updated."
            }

        data = payload.dict(exclude_unset=True)
        for field, value in data.items():
            if value is not None:
                setattr(payroll_run, field, value)
        payroll_run.save()
        return 200, _run_out(_run_queryset().get(id=payroll_run.id))
    except Exception as exc:
        return 400, handle_payment_exception(exc)


@router.post(
    "/payroll/{run_id}/calculate",
    response={200: PayrollRunDetailOut, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("finance_payroll", "calculate")
def calculate_payroll_run_endpoint(request, run_id: int):
    payroll_run = _get_run(request, run_id)
    try:
        calculate_payroll_run(payroll_run, request.user)
        return 200, _run_detail(_run_queryset().get(id=run_id))
    except Exception as exc:
        return 400, handle_payment_exception(exc)


@router.put(
    "/payroll/{run_id}/lines/{line_id}/manual-items",
    response={200: PayrollRunDetailOut, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("finance_payroll", "update")
def replace_manual_items_endpoint(
    request,
    run_id: int,
    line_id: int,
    payload: PayrollManualItemsReplaceIn,
):
    payroll_run = _get_run(request, run_id)
    line = get_object_or_404(
        PayrollLine.objects.select_related("payroll_run"),
        id=line_id,
        payroll_run_id=payroll_run.id,
    )
    try:
        replace_manual_payroll_items(
            line,
            [item.dict() for item in payload.items],
            request.user,
        )
        return 200, _run_detail(_run_queryset().get(id=run_id))
    except Exception as exc:
        return 400, handle_payment_exception(exc)


@router.post(
    "/payroll/{run_id}/submit",
    response={200: PayrollRunOut, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("finance_payroll", "submit")
def submit_payroll_run_endpoint(request, run_id: int):
    payroll_run = _get_run(request, run_id)
    try:
        submit_payroll_run(payroll_run, request.user)
        return 200, _run_out(_run_queryset().get(id=run_id))
    except Exception as exc:
        return 400, handle_payment_exception(exc)


@router.post(
    "/payroll/{run_id}/approve",
    response={200: PayrollRunOut, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("finance_payroll", "approve")
def approve_payroll_run_endpoint(request, run_id: int):
    payroll_run = _get_run(request, run_id)
    try:
        approve_payroll_run(payroll_run, request.user)
        return 200, _run_out(_run_queryset().get(id=run_id))
    except Exception as exc:
        return 400, handle_payment_exception(exc)


@router.post(
    "/payroll/{run_id}/reject",
    response={200: PayrollRunOut, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("finance_payroll", "reject")
def reject_payroll_run_endpoint(
    request,
    run_id: int,
    payload: PayrollRejectIn,
):
    payroll_run = _get_run(request, run_id)
    try:
        reject_payroll_run(payroll_run, request.user, payload.reason)
        return 200, _run_out(_run_queryset().get(id=run_id))
    except Exception as exc:
        return 400, handle_payment_exception(exc)


@router.post(
    "/payroll/{run_id}/pay",
    response={200: PayrollRunOut, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("finance_payroll", "pay")
def pay_payroll_run_endpoint(
    request,
    run_id: int,
    payload: PayrollPayIn,
):
    payroll_run = _get_run(request, run_id)
    try:
        account = _get_scoped_account(request, payload.finance_account_id)
        pay_payroll_run(
            payroll_run,
            request.user,
            account,
            paid_at=payload.paid_at,
            payment_reference=payload.payment_reference,
        )
        return 200, _run_out(_run_queryset().get(id=run_id))
    except Exception as exc:
        return 400, handle_payment_exception(exc)


@router.post(
    "/payroll/{run_id}/cancel",
    response={200: PayrollRunOut, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("finance_payroll", "cancel")
def cancel_payroll_run_endpoint(
    request,
    run_id: int,
    payload: PayrollCancelIn,
):
    payroll_run = _get_run(request, run_id)
    try:
        cancel_payroll_run(payroll_run, request.user, payload.reason)
        return 200, _run_out(_run_queryset().get(id=run_id))
    except Exception as exc:
        return 400, handle_payment_exception(exc)
