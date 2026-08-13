from typing import List, Optional

from django.shortcuts import get_object_or_404
from ninja import Query, Router
from ninja.pagination import LimitOffsetPagination, paginate

from finance.api.schemas import FinanceAccountIn, FinanceAccountOut, FinanceAccountUpdate
from finance.models import FinanceAccount
from services.api.schema.others import MessageSchema
from user.models.branch import Branch
from user.utils.perm import require_permission, scope_queryset


router = Router(tags=["Finance Accounts"])


def _account_queryset():
    return FinanceAccount.objects.select_related("branch", "created_by")


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


@router.post("/accounts", response={201: FinanceAccountOut, 400: MessageSchema})
@require_permission("payments", "create")
def create_finance_account(request, payload: FinanceAccountIn):
    try:
        data = payload.dict()
        branch_id = data.pop("branch_id", None)
        account = FinanceAccount(
            **data,
            created_by=request.user,
        )
        if branch_id:
            account.branch = get_object_or_404(Branch, id=branch_id)
        account.save()
        return 201, account
    except Exception as exc:
        return 400, {"detail": str(exc)}


@router.patch("/accounts/{account_id}", response={200: FinanceAccountOut, 400: MessageSchema, 404: MessageSchema})
@require_permission("payments", "create")
def update_finance_account(request, account_id: int, payload: FinanceAccountUpdate):
    try:
        account = get_object_or_404(FinanceAccount, id=account_id)
        data = payload.dict(exclude_unset=True)
        if "branch_id" in data:
            branch_id = data.pop("branch_id")
            account.branch = get_object_or_404(Branch, id=branch_id) if branch_id else None
        for field, value in data.items():
            setattr(account, field, value)
        account.save()
        return 200, account
    except Exception as exc:
        return 400, {"detail": str(exc)}


@router.post("/accounts/{account_id}/deactivate", response={200: FinanceAccountOut, 404: MessageSchema})
@require_permission("payments", "create")
def deactivate_finance_account(request, account_id: int):
    account = get_object_or_404(FinanceAccount, id=account_id)
    account.is_active = False
    account.save(update_fields=["is_active", "updated_at"])
    return 200, account
