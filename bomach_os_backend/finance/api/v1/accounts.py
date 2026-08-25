from datetime import date
from decimal import Decimal
from typing import List, Optional

from django.db import transaction
from django.db.models import Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja import Query, Router
from ninja.pagination import LimitOffsetPagination, paginate

from finance.api.schemas import (
    FinanceAccountBalanceOut,
    FinanceAccountIn,
    FinanceAccountOut,
    FinanceAccountUpdate,
)
from finance.models import FinanceAccount, JournalEntry, JournalLine
from finance.service import (
    ensure_finance_account_ledger_account,
    post_opening_balance_journal,
)
from shared.api.schema import MessageSchema
from user.models.branch import Branch
from system.authorization import require_permission, scope_queryset

router = Router(tags=["Finance Accounts"])


def _account_queryset():
    return FinanceAccount.objects.select_related(
        "branch", "ledger_account", "created_by"
    )


@router.get("/accounts", response=List[FinanceAccountOut])
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("payments", "list")
def list_finance_accounts(
    request,
    is_active: Optional[bool] = Query(True),
    account_type: Optional[str] = Query(None),
    branch_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
):
    accounts = scope_queryset(request, _account_queryset(), branch_field="branch_id")
    if is_active is not None:
        accounts = accounts.filter(is_active=is_active)
    if account_type:
        accounts = accounts.filter(account_type=account_type)
    if branch_id:
        accounts = accounts.filter(branch_id=branch_id)
    if search:
        accounts = accounts.filter(display_name__icontains=search)
    return accounts.order_by("display_name")


def _ledger_book_balance(account, as_of):
    if not account.ledger_account_id:
        return None
    totals = JournalLine.objects.filter(
        ledger_account_id=account.ledger_account_id,
        journal_entry__status=JournalEntry.STATUS.POSTED,
        journal_entry__entry_date__lte=as_of,
    ).aggregate(debit=Sum("debit"), credit=Sum("credit"))
    debit = totals["debit"] or Decimal("0.00")
    credit = totals["credit"] or Decimal("0.00")
    return (debit - credit).quantize(Decimal("0.01"))


@router.get(
    "/accounts/{account_id}/balance",
    response={200: FinanceAccountBalanceOut, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("payments", "list")
def get_finance_account_balance(
    request,
    account_id: int,
    as_of: Optional[date] = Query(None),
):
    account = get_object_or_404(
        scope_queryset(
            request,
            _account_queryset(),
            branch_field="branch_id",
        ),
        id=account_id,
    )
    balance_date = as_of or timezone.localdate()
    book_balance = _ledger_book_balance(account, balance_date)
    if book_balance is None:
        return 400, {
            "detail": "Finance account requires a mapped Ledger Account before book balance can be calculated."
        }

    return 200, {
        "account_id": account.id,
        "display_name": account.display_name,
        "account_type": account.account_type,
        "currency": account.currency,
        "as_of": balance_date,
        "opening_balance": account.opening_balance,
        "opening_balance_date": account.opening_balance_date,
        "book_balance": book_balance,
    }


@router.post("/accounts", response={201: FinanceAccountOut, 400: MessageSchema})
@require_permission("payments", "create")
def create_finance_account(request, payload: FinanceAccountIn):
    try:
        data = payload.dict()
        branch_id = data.pop("branch_id", None)
        branch_ids = getattr(request, "_perm_branch_ids", [])
        is_company_scope = getattr(request, "_perm_scope", "branches") == "company"
        if not is_company_scope and branch_ids and not branch_id:
            return 400, {
                "detail": "Branch-scoped Finance account creation requires a branch_id."
            }

        account = FinanceAccount(
            **data,
            created_by=request.user,
        )
        if branch_id:
            account.branch = get_object_or_404(
                scope_queryset(
                    request,
                    Branch.objects.all(),
                    branch_field="id",
                ),
                id=branch_id,
            )
        with transaction.atomic():
            account.save()
            ensure_finance_account_ledger_account(account, request.user)
            if account.opening_balance:
                post_opening_balance_journal(account, request.user)
        return 201, _account_queryset().get(id=account.id)
    except Exception as exc:
        return 400, {"detail": str(exc)}


@router.patch(
    "/accounts/{account_id}",
    response={200: FinanceAccountOut, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("payments", "create")
def update_finance_account(request, account_id: int, payload: FinanceAccountUpdate):
    try:
        account = get_object_or_404(
            scope_queryset(
                request,
                FinanceAccount.objects.all(),
                branch_field="branch_id",
            ),
            id=account_id,
        )
        data = payload.dict(exclude_unset=True)
        if "branch_id" in data:
            branch_id = data.pop("branch_id")
            branch_ids = getattr(request, "_perm_branch_ids", [])
            is_company_scope = getattr(request, "_perm_scope", "branches") == "company"
            if not is_company_scope and branch_ids and not branch_id:
                return 400, {
                    "detail": "Branch-scoped Finance accounts cannot be changed to company-wide."
                }
            account.branch = (
                get_object_or_404(
                    scope_queryset(
                        request,
                        Branch.objects.all(),
                        branch_field="id",
                    ),
                    id=branch_id,
                )
                if branch_id
                else None
            )
        for field, value in data.items():
            setattr(account, field, value)
        account.save()
        return 200, account
    except Exception as exc:
        return 400, {"detail": str(exc)}


@router.post(
    "/accounts/{account_id}/deactivate",
    response={200: FinanceAccountOut, 404: MessageSchema},
)
@require_permission("payments", "create")
def deactivate_finance_account(request, account_id: int):
    account = get_object_or_404(
        scope_queryset(
            request,
            FinanceAccount.objects.all(),
            branch_field="branch_id",
        ),
        id=account_id,
    )
    account.is_active = False
    account.save(update_fields=["is_active", "updated_at"])
    return 200, account
