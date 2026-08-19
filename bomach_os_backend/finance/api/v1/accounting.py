from datetime import date
from decimal import Decimal
from typing import List, Optional

from django.core.exceptions import ValidationError
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja import Query, Router
from ninja.pagination import LimitOffsetPagination, paginate

from finance.api.schemas import (
    FinanceAccountLedgerMapIn,
    FinanceAccountLedgerMapOut,
    GeneralLedgerLineOut,
    JournalEntryDetailOut,
    JournalEntryOut,
    JournalReverseIn,
    LedgerAccountIn,
    LedgerAccountOut,
    LedgerAccountUpdate,
    ManualJournalIn,
    ManualJournalUpdate,
    TrialBalanceOut,
)
from finance.models import FinanceAccount, JournalEntry, JournalLine, LedgerAccount
from finance.service import create_manual_journal, map_finance_account_ledger, post_journal_entry, reverse_journal_entry, update_manual_journal
from services.api.schema.others import MessageSchema
from user.models.branch import Branch
from user.utils.perm import require_permission, scope_queryset


router = Router(tags=["Finance Accounting"])


def _ledger_queryset():
    return LedgerAccount.objects.select_related("parent", "created_by")


def _journal_queryset():
    return JournalEntry.objects.select_related("branch", "created_by", "posted_by", "reversal_of").prefetch_related("lines__ledger_account")


def _scope_journals(request, qs):
    branch_ids = getattr(request, "_perm_branch_ids", [])
    if getattr(request, "_perm_scope", "branches") == "company" or not branch_ids:
        return qs
    return qs.filter(branch_id__in=branch_ids)


def _scoped_branch(request, branch_id):
    branches = Branch.objects.filter(id=branch_id)
    branch_ids = getattr(request, "_perm_branch_ids", [])
    if getattr(request, "_perm_scope", "branches") != "company" and branch_ids:
        branches = branches.filter(id__in=branch_ids)
    return get_object_or_404(branches)


def _manual_branch(request, branch_id):
    branch_ids = getattr(request, "_perm_branch_ids", [])
    is_company_scope = getattr(request, "_perm_scope", "branches") == "company"
    if not is_company_scope and branch_ids and not branch_id:
        raise ValidationError("Branch-scoped journal creation/update requires a branch_id.")
    return _scoped_branch(request, branch_id) if branch_id else None


def _money(value):
    return (value or Decimal("0.00")).quantize(Decimal("0.01"))


def _line_out(line):
    return {
        "id": line.id,
        "line_order": line.line_order,
        "ledger_account_id": line.ledger_account_id,
        "ledger_account_code": line.ledger_account.code,
        "ledger_account_name": line.ledger_account.name,
        "description": line.description,
        "debit": line.debit,
        "credit": line.credit,
    }


def _journal_out(entry, include_lines=False):
    data = {
        "id": entry.id,
        "journal_number": entry.journal_number,
        "entry_date": entry.entry_date,
        "currency": entry.currency,
        "entry_type": entry.entry_type,
        "status": entry.status,
        "branch_id": entry.branch_id,
        "branch_name": entry.branch.branch_name if entry.branch else "",
        "reference": entry.reference,
        "memo": entry.memo,
        "source_type": entry.source_type,
        "source_id": entry.source_id,
        "source_event": entry.source_event,
        "reversal_of_id": entry.reversal_of_id,
        "is_reversed": entry.is_reversed,
        "total_debit": entry.total_debit,
        "total_credit": entry.total_credit,
        "line_count": entry.lines.count(),
        "posted_at": entry.posted_at,
        "created_at": entry.created_at,
        "updated_at": entry.updated_at,
    }
    if include_lines:
        data["lines"] = [_line_out(line) for line in entry.lines.all()]
    return data


@router.get("/ledger-accounts", response=List[LedgerAccountOut])
@paginate(LimitOffsetPagination, page_size=25)
@require_permission("chart_of_accounts", "list")
def list_ledger_accounts(request, account_type: Optional[str] = Query(None), parent_id: Optional[int] = Query(None), is_postable: Optional[bool] = Query(None), is_active: Optional[bool] = Query(True), system_role: Optional[str] = Query(None), search: Optional[str] = Query(None)):
    qs = _ledger_queryset()
    if account_type: qs = qs.filter(account_type=account_type)
    if parent_id is not None: qs = qs.filter(parent_id=parent_id)
    if is_postable is not None: qs = qs.filter(is_postable=is_postable)
    if is_active is not None: qs = qs.filter(is_active=is_active)
    if system_role: qs = qs.filter(system_role=system_role)
    if search:
        q = search.strip(); qs = qs.filter(Q(code__icontains=q) | Q(name__icontains=q))
    return qs.order_by("code")


@router.post("/ledger-accounts", response={201: LedgerAccountOut, 400: MessageSchema})
@require_permission("chart_of_accounts", "create")
def create_ledger_account(request, payload: LedgerAccountIn):
    try:
        data = payload.dict(); parent_id = data.pop("parent_id", None)
        parent = get_object_or_404(LedgerAccount, id=parent_id) if parent_id else None
        account = LedgerAccount(**data, parent=parent, created_by=request.user); account.save()
        return 201, _ledger_queryset().get(id=account.id)
    except Exception as exc:
        return 400, {"detail": str(exc)}


@router.get("/ledger-accounts/{account_id}", response={200: LedgerAccountOut, 404: MessageSchema})
@require_permission("chart_of_accounts", "view")
def get_ledger_account(request, account_id: int):
    return 200, get_object_or_404(_ledger_queryset(), id=account_id)


@router.patch("/ledger-accounts/{account_id}", response={200: LedgerAccountOut, 400: MessageSchema, 404: MessageSchema})
@require_permission("chart_of_accounts", "update")
def update_ledger_account(request, account_id: int, payload: LedgerAccountUpdate):
    try:
        account = get_object_or_404(_ledger_queryset(), id=account_id); data = payload.dict(exclude_unset=True)
        if "parent_id" in data:
            parent_id = data.pop("parent_id"); account.parent = get_object_or_404(LedgerAccount, id=parent_id) if parent_id else None
        for field, value in data.items(): setattr(account, field, value)
        account.save(); return 200, _ledger_queryset().get(id=account.id)
    except Exception as exc:
        return 400, {"detail": str(exc)}


@router.post("/ledger-accounts/{account_id}/deactivate", response={200: LedgerAccountOut, 400: MessageSchema, 404: MessageSchema})
@require_permission("chart_of_accounts", "deactivate")
def deactivate_ledger_account(request, account_id: int):
    try:
        account = get_object_or_404(_ledger_queryset(), id=account_id); account.is_active = False; account.save(update_fields=["is_active", "updated_at"])
        return 200, _ledger_queryset().get(id=account.id)
    except Exception as exc:
        return 400, {"detail": str(exc)}


@router.post("/accounts/{account_id}/ledger-account", response={200: FinanceAccountLedgerMapOut, 400: MessageSchema, 404: MessageSchema})
@require_permission("chart_of_accounts", "update")
def map_finance_account_endpoint(request, account_id: int, payload: FinanceAccountLedgerMapIn):
    try:
        finance_account = get_object_or_404(scope_queryset(request, FinanceAccount.objects.select_related("branch", "ledger_account"), branch_field="branch_id"), id=account_id)
        ledger = get_object_or_404(LedgerAccount, id=payload.ledger_account_id)
        mapped = map_finance_account_ledger(finance_account, ledger, request.user)
        return 200, {
            "finance_account_id": mapped.id, "finance_account_name": mapped.display_name,
            "ledger_account_id": mapped.ledger_account_id, "ledger_account_code": mapped.ledger_account.code,
            "ledger_account_name": mapped.ledger_account.name,
        }
    except Exception as exc:
        return 400, {"detail": str(exc)}


@router.get("/journals", response=List[JournalEntryOut])
@paginate(LimitOffsetPagination, page_size=20)
@require_permission("journals", "list")
def list_journals(request, status: Optional[str] = Query(None), entry_type: Optional[str] = Query(None), currency: Optional[str] = Query(None), branch_id: Optional[int] = Query(None), date_from: Optional[date] = Query(None), date_to: Optional[date] = Query(None), search: Optional[str] = Query(None)):
    qs = _scope_journals(request, _journal_queryset())
    if status: qs = qs.filter(status=status)
    if entry_type: qs = qs.filter(entry_type=entry_type)
    if currency: qs = qs.filter(currency=currency.upper())
    if branch_id: qs = qs.filter(branch_id=branch_id)
    if date_from: qs = qs.filter(entry_date__gte=date_from)
    if date_to: qs = qs.filter(entry_date__lte=date_to)
    if search:
        q = search.strip(); qs = qs.filter(Q(journal_number__icontains=q) | Q(reference__icontains=q) | Q(memo__icontains=q) | Q(source_type__icontains=q))
    return [_journal_out(entry) for entry in qs.order_by("-entry_date", "-created_at")]


@router.post("/journals", response={201: JournalEntryDetailOut, 400: MessageSchema})
@require_permission("journals", "create")
def create_manual_journal_endpoint(request, payload: ManualJournalIn):
    try:
        branch = _manual_branch(request, payload.branch_id)
        entry = create_manual_journal(entry_date=payload.entry_date, currency=payload.currency, lines=[line.dict() for line in payload.lines], created_by=request.user, branch=branch, reference=payload.reference, memo=payload.memo)
        return 201, _journal_out(_journal_queryset().get(id=entry.id), True)
    except Exception as exc:
        return 400, {"detail": str(exc)}


@router.get("/journals/{journal_id}", response={200: JournalEntryDetailOut, 404: MessageSchema})
@require_permission("journals", "view")
def get_journal(request, journal_id: int):
    entry = get_object_or_404(_scope_journals(request, _journal_queryset()), id=journal_id)
    return 200, _journal_out(entry, True)


@router.patch("/journals/{journal_id}", response={200: JournalEntryDetailOut, 400: MessageSchema, 404: MessageSchema})
@require_permission("journals", "update")
def update_manual_journal_endpoint(request, journal_id: int, payload: ManualJournalUpdate):
    try:
        entry = get_object_or_404(_scope_journals(request, _journal_queryset()), id=journal_id)
        data = payload.dict(exclude_unset=True); branch_marker = "branch_id" in data; branch = None
        if branch_marker: branch = _manual_branch(request, data.pop("branch_id"))
        lines = data.pop("lines", None)
        updated = update_manual_journal(entry, entry_date=data.get("entry_date"), currency=data.get("currency"), branch_marker=branch_marker, branch=branch, reference=data.get("reference"), memo=data.get("memo"), lines=[line.dict() for line in lines] if lines is not None else None)
        return 200, _journal_out(_journal_queryset().get(id=updated.id), True)
    except Exception as exc:
        return 400, {"detail": str(exc)}


@router.post("/journals/{journal_id}/post", response={200: JournalEntryDetailOut, 400: MessageSchema, 404: MessageSchema})
@require_permission("journals", "post")
def post_journal_endpoint(request, journal_id: int):
    try:
        entry = get_object_or_404(_scope_journals(request, _journal_queryset()), id=journal_id)
        posted = post_journal_entry(entry, request.user)
        return 200, _journal_out(_journal_queryset().get(id=posted.id), True)
    except Exception as exc:
        return 400, {"detail": str(exc)}


@router.post("/journals/{journal_id}/reverse", response={201: JournalEntryDetailOut, 400: MessageSchema, 404: MessageSchema})
@require_permission("journals", "reverse")
def reverse_journal_endpoint(request, journal_id: int, payload: JournalReverseIn):
    try:
        entry = get_object_or_404(_scope_journals(request, _journal_queryset()), id=journal_id)
        reversal = reverse_journal_entry(entry, request.user, entry_date=payload.entry_date, memo=payload.memo)
        return 201, _journal_out(_journal_queryset().get(id=reversal.id), True)
    except Exception as exc:
        return 400, {"detail": str(exc)}


@router.get("/general-ledger", response=List[GeneralLedgerLineOut])
@paginate(LimitOffsetPagination, page_size=50)
@require_permission("general_ledger", "list")
def general_ledger(request, ledger_account_id: Optional[int] = Query(None), currency: str = Query("NGN"), branch_id: Optional[int] = Query(None), date_from: Optional[date] = Query(None), date_to: Optional[date] = Query(None)):
    currency = currency.upper()
    scoped = JournalLine.objects.select_related("journal_entry", "journal_entry__branch", "ledger_account").filter(
        journal_entry__status=JournalEntry.STATUS.POSTED,
        journal_entry__currency=currency,
    )
    branch_ids = getattr(request, "_perm_branch_ids", [])
    if getattr(request, "_perm_scope", "branches") != "company" and branch_ids:
        scoped = scoped.filter(journal_entry__branch_id__in=branch_ids)
    if ledger_account_id:
        scoped = scoped.filter(ledger_account_id=ledger_account_id)
    if branch_id:
        scoped = scoped.filter(journal_entry__branch_id=branch_id)

    running = {}
    if date_from:
        prior = scoped.filter(journal_entry__entry_date__lt=date_from)
        for row in prior.values("ledger_account_id", "ledger_account__normal_balance").annotate(total_debit=Sum("debit"), total_credit=Sum("credit")):
            debit, credit = _money(row["total_debit"]), _money(row["total_credit"])
            running[row["ledger_account_id"]] = (
                _money(debit - credit)
                if row["ledger_account__normal_balance"] == LedgerAccount.NORMAL_BALANCE.DEBIT
                else _money(credit - debit)
            )
        scoped = scoped.filter(journal_entry__entry_date__gte=date_from)
    if date_to:
        scoped = scoped.filter(journal_entry__entry_date__lte=date_to)

    rows = []
    for line in scoped.order_by("journal_entry__entry_date", "journal_entry_id", "line_order"):
        entry = line.journal_entry
        current = running.get(line.ledger_account_id, Decimal("0.00"))
        delta = (line.debit - line.credit) if line.ledger_account.normal_balance == LedgerAccount.NORMAL_BALANCE.DEBIT else (line.credit - line.debit)
        current = _money(current + delta)
        running[line.ledger_account_id] = current
        rows.append({
            "journal_entry_id": entry.id, "journal_number": entry.journal_number, "entry_date": entry.entry_date,
            "currency": entry.currency, "branch_id": entry.branch_id, "branch_name": entry.branch.branch_name if entry.branch else "",
            "reference": entry.reference, "memo": entry.memo,
            "ledger_account_id": line.ledger_account_id, "ledger_account_code": line.ledger_account.code,
            "ledger_account_name": line.ledger_account.name, "description": line.description,
            "debit": line.debit, "credit": line.credit, "running_balance": current,
        })
    return rows


@router.get("/trial-balance", response=TrialBalanceOut)
@require_permission("general_ledger", "view")
def trial_balance(request, as_of: Optional[date] = Query(None), currency: str = Query("NGN"), branch_id: Optional[int] = Query(None)):
    balance_date = as_of or timezone.localdate(); currency = currency.upper()
    lines = JournalLine.objects.filter(journal_entry__status=JournalEntry.STATUS.POSTED, journal_entry__entry_date__lte=balance_date, journal_entry__currency=currency)
    branch_ids = getattr(request, "_perm_branch_ids", [])
    if getattr(request, "_perm_scope", "branches") != "company" and branch_ids: lines = lines.filter(journal_entry__branch_id__in=branch_ids)
    if branch_id: lines = lines.filter(journal_entry__branch_id=branch_id)
    grouped = lines.values("ledger_account_id", "ledger_account__code", "ledger_account__name", "ledger_account__account_type", "ledger_account__normal_balance").annotate(total_debit=Sum("debit"), total_credit=Sum("credit")).order_by("ledger_account__code")
    rows, total_debit, total_credit = [], Decimal("0.00"), Decimal("0.00")
    for row in grouped:
        debit, credit = _money(row["total_debit"]), _money(row["total_credit"]); total_debit += debit; total_credit += credit
        balance = _money(debit - credit) if row["ledger_account__normal_balance"] == LedgerAccount.NORMAL_BALANCE.DEBIT else _money(credit - debit)
        rows.append({
            "ledger_account_id": row["ledger_account_id"], "ledger_account_code": row["ledger_account__code"],
            "ledger_account_name": row["ledger_account__name"], "account_type": row["ledger_account__account_type"],
            "normal_balance": row["ledger_account__normal_balance"], "total_debit": debit, "total_credit": credit, "balance": balance,
        })
    total_debit, total_credit = _money(total_debit), _money(total_credit)
    return {"as_of": balance_date, "currency": currency, "total_debit": total_debit, "total_credit": total_credit, "balanced": total_debit == total_credit, "rows": rows}
