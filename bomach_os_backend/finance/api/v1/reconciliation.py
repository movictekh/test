from decimal import Decimal
from typing import List
from django.db.models import Sum
from django.shortcuts import get_object_or_404
from ninja import Router
from ninja.pagination import LimitOffsetPagination, paginate
from finance.api.schemas.reconciliation import (
    BankGLCandidateOut,
    BankReconciliationIn,
    BankReconciliationMatchIn,
    BankReconciliationMatchOut,
    BankReconciliationOut,
    BankReconciliationSummaryOut,
    BankStatementLineOut,
    BankStatementLinesIn,
)
from finance.models import (
    BankReconciliation,
    BankReconciliationMatch,
    BankStatementLine,
    FinanceAccount,
    JournalLine,
)
from finance.service import (
    add_bank_statement_lines,
    auto_match_bank_reconciliation,
    bank_gl_candidates,
    close_bank_reconciliation,
    create_bank_reconciliation,
    delete_bank_reconciliation_match,
    discard_bank_reconciliation,
    match_bank_statement_line,
    reconcile_bank_reconciliation,
    reconciliation_summary,
)
from services.api.schema.others import MessageSchema
from user.utils.perm import require_permission, scope_queryset

router = Router(tags=["Finance Bank Reconciliation"])


def _qs():
    return BankReconciliation.objects.select_related(
        "finance_account",
        "finance_account__branch",
        "finance_account__ledger_account",
        "reconciled_by",
        "closed_by",
        "created_by",
    )


def _scoped(request, qs):
    return scope_queryset(request, qs, branch_field="finance_account__branch_id")


def _out(r):
    return {
        "id": r.id,
        "finance_account_id": r.finance_account_id,
        "finance_account_name": r.finance_account.display_name,
        "statement_start_date": r.statement_start_date,
        "statement_end_date": r.statement_end_date,
        "statement_opening_balance": r.statement_opening_balance,
        "statement_closing_balance": r.statement_closing_balance,
        "status": r.status,
        "notes": r.notes,
        "reconciled_by_id": r.reconciled_by_id,
        "reconciled_at": r.reconciled_at,
        "closed_by_id": r.closed_by_id,
        "closed_at": r.closed_at,
        "created_by_id": r.created_by_id,
        "created_at": r.created_at,
        "updated_at": r.updated_at,
    }


def _line_out(x):
    matched = x.matches.aggregate(total=Sum("matched_amount"))["total"] or Decimal(
        "0.00"
    )
    return {
        "id": x.id,
        "transaction_date": x.transaction_date,
        "value_date": x.value_date,
        "description": x.description,
        "reference": x.reference,
        "amount": x.amount,
        "direction": x.direction,
        "running_balance": x.running_balance,
        "external_transaction_id": x.external_transaction_id,
        "sequence_number": x.sequence_number,
        "matched_amount": matched,
        "remaining_amount": (x.amount - matched).quantize(Decimal("0.01")),
    }


@router.get("/bank-reconciliations", response=List[BankReconciliationOut])
@paginate(LimitOffsetPagination, page_size=20)
@require_permission("bank_reconciliation", "list")
def list_reconciliations(request):
    return [_out(r) for r in _scoped(request, _qs())]


@router.post(
    "/bank-reconciliations", response={201: BankReconciliationOut, 400: MessageSchema}
)
@require_permission("bank_reconciliation", "create")
def create_reconciliation(request, payload: BankReconciliationIn):
    try:
        a = get_object_or_404(
            scope_queryset(
                request,
                FinanceAccount.objects.select_related(
                    "branch", "ledger_account"
                ).filter(is_active=True, account_type=FinanceAccount.ACCOUNT_TYPE.BANK),
                branch_field="branch_id",
            ),
            id=payload.finance_account_id,
        )
        r = create_bank_reconciliation(
            finance_account=a,
            statement_start_date=payload.statement_start_date,
            statement_end_date=payload.statement_end_date,
            statement_opening_balance=payload.statement_opening_balance,
            statement_closing_balance=payload.statement_closing_balance,
            notes=payload.notes,
            created_by=request.user,
        )
        return 201, _out(_qs().get(pk=r.pk))
    except Exception as e:
        return 400, {"detail": str(e)}


@router.get(
    "/bank-reconciliations/{reconciliation_id}",
    response={200: BankReconciliationOut, 404: MessageSchema},
)
@require_permission("bank_reconciliation", "view")
def get_reconciliation(request, reconciliation_id: int):
    return 200, _out(get_object_or_404(_scoped(request, _qs()), id=reconciliation_id))


@router.post(
    "/bank-reconciliations/{reconciliation_id}/discard",
    response={200: MessageSchema, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("bank_reconciliation", "update")
def discard_reconciliation(request, reconciliation_id: int):
    try:
        r = get_object_or_404(_scoped(request, _qs()), id=reconciliation_id)
        discard_bank_reconciliation(r)
        return 200, {"detail": "Draft bank reconciliation discarded."}
    except Exception as e:
        return 400, {"detail": str(e)}


@router.post(
    "/bank-reconciliations/{reconciliation_id}/statement-lines",
    response={201: List[BankStatementLineOut], 400: MessageSchema, 404: MessageSchema},
)
@require_permission("bank_reconciliation", "update")
def add_lines(request, reconciliation_id: int, payload: BankStatementLinesIn):
    try:
        r = get_object_or_404(_scoped(request, _qs()), id=reconciliation_id)
        lines = add_bank_statement_lines(r, [x.dict() for x in payload.lines])
        return 201, [_line_out(x) for x in lines]
    except Exception as e:
        return 400, {"detail": str(e)}


@router.get(
    "/bank-reconciliations/{reconciliation_id}/statement-lines",
    response=List[BankStatementLineOut],
)
@require_permission("bank_reconciliation", "view")
def list_lines(request, reconciliation_id: int):
    r = get_object_or_404(_scoped(request, _qs()), id=reconciliation_id)
    return [_line_out(x) for x in r.statement_lines.prefetch_related("matches").all()]


@router.get(
    "/bank-reconciliations/{reconciliation_id}/gl-candidates",
    response=List[BankGLCandidateOut],
)
@require_permission("bank_reconciliation", "match")
def gl_candidates(request, reconciliation_id: int):
    return bank_gl_candidates(
        get_object_or_404(_scoped(request, _qs()), id=reconciliation_id)
    )


@router.post(
    "/bank-reconciliations/{reconciliation_id}/matches",
    response={201: BankReconciliationMatchOut, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("bank_reconciliation", "match")
def create_match(request, reconciliation_id: int, payload: BankReconciliationMatchIn):
    try:
        r = get_object_or_404(_scoped(request, _qs()), id=reconciliation_id)
        s = get_object_or_404(
            BankStatementLine,
            id=payload.bank_statement_line_id,
            bank_reconciliation_id=r.id,
        )
        jl = get_object_or_404(JournalLine, id=payload.journal_line_id)
        m = match_bank_statement_line(
            reconciliation=r,
            bank_statement_line=s,
            journal_line=jl,
            matched_amount=payload.matched_amount,
            matched_by=request.user,
            notes=payload.notes,
        )
        return 201, m
    except Exception as e:
        return 400, {"detail": str(e)}


@router.delete(
    "/bank-reconciliations/{reconciliation_id}/matches/{match_id}",
    response={200: MessageSchema, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("bank_reconciliation", "match")
def delete_match(request, reconciliation_id: int, match_id: int):
    try:
        r = get_object_or_404(_scoped(request, _qs()), id=reconciliation_id)
        m = get_object_or_404(
            BankReconciliationMatch, id=match_id, bank_reconciliation_id=r.id
        )
        delete_bank_reconciliation_match(m)
        return 200, {"detail": "Bank reconciliation match removed."}
    except Exception as e:
        return 400, {"detail": str(e)}


@router.post(
    "/bank-reconciliations/{reconciliation_id}/auto-match",
    response={
        200: List[BankReconciliationMatchOut],
        400: MessageSchema,
        404: MessageSchema,
    },
)
@require_permission("bank_reconciliation", "match")
def auto_match(request, reconciliation_id: int):
    try:
        return 200, auto_match_bank_reconciliation(
            get_object_or_404(_scoped(request, _qs()), id=reconciliation_id),
            request.user,
        )
    except Exception as e:
        return 400, {"detail": str(e)}


@router.get(
    "/bank-reconciliations/{reconciliation_id}/summary",
    response={200: BankReconciliationSummaryOut, 404: MessageSchema},
)
@require_permission("bank_reconciliation", "view")
def summary(request, reconciliation_id: int):
    return 200, reconciliation_summary(
        get_object_or_404(_scoped(request, _qs()), id=reconciliation_id)
    )


@router.post(
    "/bank-reconciliations/{reconciliation_id}/reconcile",
    response={200: BankReconciliationOut, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("bank_reconciliation", "reconcile")
def reconcile(request, reconciliation_id: int):
    try:
        r = reconcile_bank_reconciliation(
            get_object_or_404(_scoped(request, _qs()), id=reconciliation_id),
            request.user,
        )
        return 200, _out(_qs().get(pk=r.pk))
    except Exception as e:
        return 400, {"detail": str(e)}


@router.post(
    "/bank-reconciliations/{reconciliation_id}/close",
    response={200: BankReconciliationOut, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("bank_reconciliation", "close")
def close(request, reconciliation_id: int):
    try:
        r = close_bank_reconciliation(
            get_object_or_404(_scoped(request, _qs()), id=reconciliation_id),
            request.user,
        )
        return 200, _out(_qs().get(pk=r.pk))
    except Exception as e:
        return 400, {"detail": str(e)}
