from decimal import Decimal
from typing import List, Optional
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja import Query, Router
from ninja.pagination import LimitOffsetPagination, paginate
from finance.api.schemas import (
    PayrollStatutoryGenerateIn,
    StatutoryObligationDetailOut,
    StatutoryObligationIn,
    StatutoryObligationOut,
    StatutoryObligationUpdate,
    StatutoryPayIn,
    StatutoryRejectIn,
    StatutorySummaryOut,
    WHTGenerateIn,
)
from finance.models import FinanceAccount, PayrollRun, StatutoryObligation
from finance.service import (
    approve_statutory_obligation,
    generate_payroll_statutory_obligation,
    generate_wht_obligation,
    handle_payment_exception,
    pay_statutory_obligation,
    reject_statutory_obligation,
    submit_statutory_obligation,
    void_statutory_obligation,
)
from shared.api.schema import MessageSchema
from user.models.branch import Branch
from system.authorization import require_permission

router = Router(tags=["Finance Tax And Statutory"])


def _money(v):
    return (v or Decimal("0.00")).quantize(Decimal("0.01"))


def _qs():
    return StatutoryObligation.objects.select_related(
        "branch",
        "finance_account",
        "submitted_by",
        "approved_by",
        "rejected_by",
        "paid_by",
        "created_by",
    ).prefetch_related("items")


def _scope(r, q):
    ids = getattr(r, "_perm_branch_ids", [])
    return (
        q
        if getattr(r, "_perm_scope", "branches") == "company" or not ids
        else q.filter(branch_id__in=ids)
    )


def _get(r, i):
    return get_object_or_404(_scope(r, _qs()), id=i)


def _branch(r, i):
    q = Branch.objects.filter(id=i)
    ids = getattr(r, "_perm_branch_ids", [])
    if getattr(r, "_perm_scope", "branches") != "company" and ids:
        q = q.filter(id__in=ids)
    return get_object_or_404(q)


def _account(r, i):
    q = FinanceAccount.objects.filter(id=i, is_active=True)
    ids = getattr(r, "_perm_branch_ids", [])
    if getattr(r, "_perm_scope", "branches") != "company" and ids:
        q = q.filter(Q(branch_id__in=ids) | Q(branch__isnull=True))
    return get_object_or_404(q)


def _item(x):
    return {
        "id": x.id,
        "source_type": x.source_type,
        "source_reference": x.source_reference,
        "description": x.description,
        "basis_amount": x.basis_amount,
        "liability_amount": x.liability_amount,
    }


def _out(o):
    return {
        "id": o.id,
        "obligation_number": o.obligation_number,
        "obligation_type": o.obligation_type,
        "obligation_type_display": o.get_obligation_type_display(),
        "source_type": o.source_type,
        "branch_id": o.branch_id,
        "branch_name": o.branch.branch_name if o.branch else "",
        "period_label": o.period_label,
        "period_start": o.period_start,
        "period_end": o.period_end,
        "basis": o.basis,
        "basis_amount": o.basis_amount,
        "amount": o.amount,
        "due_date": o.due_date,
        "status": o.status,
        "status_display": o.get_status_display(),
        "is_overdue": o.is_overdue,
        "finance_account_id": o.finance_account_id,
        "finance_account_name": (
            o.finance_account.display_name if o.finance_account else ""
        ),
        "notes": o.notes,
        "submitted_at": o.submitted_at,
        "approved_at": o.approved_at,
        "rejected_at": o.rejected_at,
        "rejection_reason": o.rejection_reason,
        "paid_at": o.paid_at,
        "payment_reference": o.payment_reference,
        "created_at": o.created_at,
        "updated_at": o.updated_at,
    }


def _detail(o):
    d = _out(o)
    d["items"] = [_item(x) for x in o.items.all()]
    return d


@router.get("/statutory/summary", response=StatutorySummaryOut)
@require_permission("statutory", "view")
def summary(
    request,
    period_start: Optional[str] = Query(None),
    period_end: Optional[str] = Query(None),
    branch_id: Optional[int] = Query(None),
):
    q = _scope(request, _qs()).exclude(status__in=["paid", "void"])
    if period_start:
        q = q.filter(period_end__gte=period_start)
    if period_end:
        q = q.filter(period_start__lte=period_end)
    if branch_id:
        q = q.filter(branch_id=branch_id)
    totals = {
        t: _money(q.filter(obligation_type=t).aggregate(total=Sum("amount"))["total"])
        for t in StatutoryObligation.OBLIGATION_TYPE.values
    }
    overdue = q.filter(due_date__lt=timezone.localdate())
    return {
        "vat_payable": totals["vat"],
        "wht_payable": totals["wht"],
        "paye_payable": totals["paye"],
        "pension_payable": totals["pension"],
        "other_payable": totals["other"],
        "total_payable": _money(sum(totals.values(), Decimal("0.00"))),
        "overdue_amount": _money(overdue.aggregate(total=Sum("amount"))["total"]),
        "outstanding_count": q.count(),
        "overdue_count": overdue.count(),
    }


@router.get("/statutory/obligations", response=List[StatutoryObligationOut])
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("statutory", "list")
def listing(
    request,
    obligation_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    branch_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
):
    q = _scope(request, _qs())
    if obligation_type:
        q = q.filter(obligation_type=obligation_type)
    if status:
        q = q.filter(status=status)
    if branch_id:
        q = q.filter(branch_id=branch_id)
    if search:
        s = search.strip()
        q = q.filter(
            Q(obligation_number__icontains=s)
            | Q(period_label__icontains=s)
            | Q(basis__icontains=s)
            | Q(notes__icontains=s)
        )
    return [_out(x) for x in q.order_by("due_date", "-created_at")]


@router.post(
    "/statutory/obligations", response={201: StatutoryObligationOut, 400: MessageSchema}
)
@require_permission("statutory", "create")
def create(request, payload: StatutoryObligationIn):
    try:
        d = payload.dict()
        bid = d.pop("branch_id", None)
        b = _branch(request, bid) if bid else None
        if (
            getattr(request, "_perm_scope", "branches") != "company"
            and getattr(request, "_perm_branch_ids", [])
            and not b
        ):
            return 400, {
                "detail": "Branch-scoped statutory creation requires branch_id."
            }
        o = StatutoryObligation.objects.create(
            **d, source_type="manual", branch=b, created_by=request.user
        )
        return 201, _out(_qs().get(id=o.id))
    except Exception as e:
        return 400, handle_payment_exception(e)


@router.post(
    "/statutory/generate/wht",
    response={201: StatutoryObligationDetailOut, 400: MessageSchema},
)
@require_permission("statutory", "generate")
def gen_wht(request, payload: WHTGenerateIn):
    try:
        b = _branch(request, payload.branch_id) if payload.branch_id else None
        o = generate_wht_obligation(
            period_start=payload.period_start,
            period_end=payload.period_end,
            due_date=payload.due_date,
            created_by=request.user,
            branch=b,
            period_label=payload.period_label,
            notes=payload.notes,
        )
        return 201, _detail(_qs().get(id=o.id))
    except Exception as e:
        return 400, handle_payment_exception(e)


@router.post(
    "/statutory/generate/payroll",
    response={201: StatutoryObligationDetailOut, 400: MessageSchema},
)
@require_permission("statutory", "generate")
def gen_payroll(request, payload: PayrollStatutoryGenerateIn):
    try:
        q = PayrollRun.objects.filter(id=payload.payroll_run_id)
        ids = getattr(request, "_perm_branch_ids", [])
        if getattr(request, "_perm_scope", "branches") != "company" and ids:
            q = q.filter(branch_id__in=ids)
        run = get_object_or_404(q)
        o = generate_payroll_statutory_obligation(
            payroll_run=run,
            category=payload.category,
            due_date=payload.due_date,
            created_by=request.user,
            notes=payload.notes,
        )
        return 201, _detail(_qs().get(id=o.id))
    except Exception as e:
        return 400, handle_payment_exception(e)


@router.get(
    "/statutory/obligations/{obligation_id}",
    response={200: StatutoryObligationDetailOut, 404: MessageSchema},
)
@require_permission("statutory", "view")
def detail(request, obligation_id: int):
    return 200, _detail(_get(request, obligation_id))


@router.patch(
    "/statutory/obligations/{obligation_id}",
    response={200: StatutoryObligationOut, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("statutory", "update")
def update(request, obligation_id: int, payload: StatutoryObligationUpdate):
    o = _get(request, obligation_id)
    try:
        if o.status not in {"draft", "rejected"}:
            return 400, {
                "detail": "Only draft or rejected statutory obligations can be updated."
            }
        for k, v in payload.dict(exclude_unset=True).items():
            if v is not None:
                setattr(o, k, v)
        o.save()
        return 200, _out(_qs().get(id=o.id))
    except Exception as e:
        return 400, handle_payment_exception(e)


@router.post(
    "/statutory/obligations/{obligation_id}/submit",
    response={200: StatutoryObligationOut, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("statutory", "submit")
def submit(request, obligation_id: int):
    o = _get(request, obligation_id)
    try:
        submit_statutory_obligation(o, request.user)
        return 200, _out(_qs().get(id=o.id))
    except Exception as e:
        return 400, handle_payment_exception(e)


@router.post(
    "/statutory/obligations/{obligation_id}/approve",
    response={200: StatutoryObligationOut, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("statutory", "approve")
def approve(request, obligation_id: int):
    o = _get(request, obligation_id)
    try:
        approve_statutory_obligation(o, request.user)
        return 200, _out(_qs().get(id=o.id))
    except Exception as e:
        return 400, handle_payment_exception(e)


@router.post(
    "/statutory/obligations/{obligation_id}/reject",
    response={200: StatutoryObligationOut, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("statutory", "reject")
def reject(request, obligation_id: int, payload: StatutoryRejectIn):
    o = _get(request, obligation_id)
    try:
        reject_statutory_obligation(o, request.user, payload.reason)
        return 200, _out(_qs().get(id=o.id))
    except Exception as e:
        return 400, handle_payment_exception(e)


@router.post(
    "/statutory/obligations/{obligation_id}/pay",
    response={200: StatutoryObligationOut, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("statutory", "pay")
def pay(request, obligation_id: int, payload: StatutoryPayIn):
    o = _get(request, obligation_id)
    try:
        a = _account(request, payload.finance_account_id)
        pay_statutory_obligation(
            o,
            request.user,
            a,
            paid_at=payload.paid_at,
            payment_reference=payload.payment_reference,
        )
        return 200, _out(_qs().get(id=o.id))
    except Exception as e:
        return 400, handle_payment_exception(e)


@router.post(
    "/statutory/obligations/{obligation_id}/void",
    response={200: StatutoryObligationOut, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("statutory", "void")
def void(request, obligation_id: int):
    o = _get(request, obligation_id)
    try:
        void_statutory_obligation(o, request.user)
        return 200, _out(_qs().get(id=o.id))
    except Exception as e:
        return 400, handle_payment_exception(e)
