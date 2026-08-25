from typing import List, Optional
from django.db.models import Q
from django.shortcuts import get_object_or_404
from ninja import Query, Router
from ninja.pagination import LimitOffsetPagination, paginate
from finance.api.schemas.fixed_assets import (
    FixedAssetCapitalizeIn,
    FixedAssetCategoryIn,
    FixedAssetCategoryOut,
    FixedAssetCategoryUpdate,
    FixedAssetDepreciateIn,
    FixedAssetDepreciationScheduleRowOut,
    FixedAssetDisposeIn,
    FixedAssetIn,
    FixedAssetOut,
    FixedAssetUpdate,
)
from finance.models import FinanceAccount, FixedAsset, FixedAssetCategory, LedgerAccount
from finance.service import (
    capitalize_fixed_asset,
    create_fixed_asset,
    depreciation_schedule,
    dispose_fixed_asset,
    fixed_asset_summary,
    post_fixed_asset_depreciation,
)
from shared.api.schema import MessageSchema
from finance.transactions.expense import Expense
from domains.organization.models.branch import Branch
from system.authorization import require_permission, scope_queryset

router = Router(tags=["Finance Fixed Assets"])


def _cqs():
    return FixedAssetCategory.objects.select_related(
        "asset_ledger_account",
        "accumulated_depreciation_ledger_account",
        "depreciation_expense_ledger_account",
        "created_by",
    )


def _aqs():
    return FixedAsset.objects.select_related(
        "category",
        "branch",
        "source_expense",
        "source_expense__finance_account",
        "disposal_finance_account",
        "created_by",
    )


def _scope_assets(request, qs):
    return scope_queryset(request, qs, branch_field="branch_id")


def _scope_expenses(request, qs):
    ids = getattr(request, "_perm_branch_ids", [])
    return (
        qs
        if getattr(request, "_perm_scope", "branches") == "company" or not ids
        else qs.filter(
            Q(branch_id__in=ids)
            | Q(service_order__branch_id__in=ids)
            | Q(finance_account__branch_id__in=ids)
        )
    )


def _ledger(pk):
    return get_object_or_404(LedgerAccount, pk=pk)


def _out(a):
    s = fixed_asset_summary(a)
    return {
        "id": a.id,
        "asset_number": a.asset_number,
        "name": a.name,
        "description": a.description,
        "category_id": a.category_id,
        "category_name": a.category.name,
        "branch_id": a.branch_id,
        "branch_name": a.branch.branch_name if a.branch else "",
        "source_expense_id": a.source_expense_id,
        "acquisition_date": a.acquisition_date,
        "capitalization_date": a.capitalization_date,
        "currency": a.currency,
        "acquisition_cost": a.acquisition_cost,
        "residual_value": a.residual_value,
        "useful_life_months": a.useful_life_months,
        "depreciation_method": a.depreciation_method,
        "status": a.status,
        "depreciable_amount": s["depreciable_amount"],
        "accumulated_depreciation": s["accumulated_depreciation"],
        "book_value": s["book_value"],
        "disposed_at": a.disposed_at,
        "disposal_proceeds": a.disposal_proceeds,
        "disposal_finance_account_id": a.disposal_finance_account_id,
        "disposal_reference": a.disposal_reference,
        "disposal_notes": a.disposal_notes,
        "created_by_id": a.created_by_id,
        "created_at": a.created_at,
        "updated_at": a.updated_at,
    }


@router.get("/fixed-asset-categories", response=List[FixedAssetCategoryOut])
@paginate(LimitOffsetPagination, page_size=20)
@require_permission("fixed_asset_categories", "list")
def list_categories(request, is_active: Optional[bool] = Query(True)):
    q = _cqs()
    return (
        q.filter(is_active=is_active).order_by("code")
        if is_active is not None
        else q.order_by("code")
    )


@router.post(
    "/fixed-asset-categories", response={201: FixedAssetCategoryOut, 400: MessageSchema}
)
@require_permission("fixed_asset_categories", "create")
def create_category(request, payload: FixedAssetCategoryIn):
    try:
        c = FixedAssetCategory(
            code=payload.code,
            name=payload.name,
            description=payload.description,
            asset_ledger_account=_ledger(payload.asset_ledger_account_id),
            accumulated_depreciation_ledger_account=_ledger(
                payload.accumulated_depreciation_ledger_account_id
            ),
            depreciation_expense_ledger_account=_ledger(
                payload.depreciation_expense_ledger_account_id
            ),
            default_useful_life_months=payload.default_useful_life_months,
            default_residual_value_percent=payload.default_residual_value_percent,
            created_by=request.user,
        )
        c.save()
        return 201, _cqs().get(pk=c.pk)
    except Exception as e:
        return 400, {"detail": str(e)}


@router.get(
    "/fixed-asset-categories/{category_id}",
    response={200: FixedAssetCategoryOut, 404: MessageSchema},
)
@require_permission("fixed_asset_categories", "view")
def get_category(request, category_id: int):
    return 200, get_object_or_404(_cqs(), pk=category_id)


@router.patch(
    "/fixed-asset-categories/{category_id}",
    response={200: FixedAssetCategoryOut, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("fixed_asset_categories", "update")
def update_category(request, category_id: int, payload: FixedAssetCategoryUpdate):
    try:
        c = get_object_or_404(_cqs(), pk=category_id)
        d = payload.dict(exclude_unset=True)
        rel = {
            "asset_ledger_account_id": "asset_ledger_account",
            "accumulated_depreciation_ledger_account_id": "accumulated_depreciation_ledger_account",
            "depreciation_expense_ledger_account_id": "depreciation_expense_ledger_account",
        }
        for pf, mf in rel.items():
            if pf in d:
                setattr(c, mf, _ledger(d.pop(pf)))
        for f, v in d.items():
            setattr(c, f, v)
        c.save()
        return 200, _cqs().get(pk=c.pk)
    except Exception as e:
        return 400, {"detail": str(e)}


@router.post(
    "/fixed-asset-categories/{category_id}/deactivate",
    response={200: FixedAssetCategoryOut, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("fixed_asset_categories", "deactivate")
def deactivate_category(request, category_id: int):
    try:
        c = get_object_or_404(_cqs(), pk=category_id)
        c.is_active = False
        c.save(update_fields=["is_active", "updated_at"])
        return 200, _cqs().get(pk=c.pk)
    except Exception as e:
        return 400, {"detail": str(e)}


@router.get("/fixed-assets", response=List[FixedAssetOut])
@paginate(LimitOffsetPagination, page_size=20)
@require_permission("fixed_assets", "list")
def list_assets(
    request,
    status: Optional[str] = Query(None),
    category_id: Optional[int] = Query(None),
    branch_id: Optional[int] = Query(None),
):
    q = _scope_assets(request, _aqs())
    q = q.filter(status=status) if status else q
    q = q.filter(category_id=category_id) if category_id else q
    q = q.filter(branch_id=branch_id) if branch_id else q
    return [_out(a) for a in q.order_by("asset_number")]


@router.post("/fixed-assets", response={201: FixedAssetOut, 400: MessageSchema})
@require_permission("fixed_assets", "create")
def create_asset(request, payload: FixedAssetIn):
    try:
        c = get_object_or_404(
            FixedAssetCategory, pk=payload.category_id, is_active=True
        )
        e = get_object_or_404(
            _scope_expenses(
                request,
                Expense.objects.select_related(
                    "branch", "service_order__branch", "finance_account"
                ),
            ),
            pk=payload.source_expense_id,
        )
        branch = None
        if payload.branch_id:
            q = Branch.objects.filter(pk=payload.branch_id)
            ids = getattr(request, "_perm_branch_ids", [])
            q = (
                q.filter(pk__in=ids)
                if getattr(request, "_perm_scope", "branches") != "company" and ids
                else q
            )
            branch = get_object_or_404(q)
        a = create_fixed_asset(
            category=c,
            source_expense=e,
            name=payload.name,
            description=payload.description,
            acquisition_date=payload.acquisition_date,
            acquisition_cost=payload.acquisition_cost,
            residual_value=payload.residual_value,
            useful_life_months=payload.useful_life_months,
            branch=branch,
            created_by=request.user,
        )
        return 201, _out(_aqs().get(pk=a.pk))
    except Exception as e:
        return 400, {"detail": str(e)}


@router.get(
    "/fixed-assets/{asset_id}", response={200: FixedAssetOut, 404: MessageSchema}
)
@require_permission("fixed_assets", "view")
def get_asset(request, asset_id: int):
    return 200, _out(get_object_or_404(_scope_assets(request, _aqs()), pk=asset_id))


@router.patch(
    "/fixed-assets/{asset_id}",
    response={200: FixedAssetOut, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("fixed_assets", "update")
def update_asset(request, asset_id: int, payload: FixedAssetUpdate):
    try:
        a = get_object_or_404(_scope_assets(request, _aqs()), pk=asset_id)
        for f, v in payload.dict(exclude_unset=True).items():
            setattr(a, f, v)
        a.save()
        return 200, _out(_aqs().get(pk=a.pk))
    except Exception as e:
        return 400, {"detail": str(e)}


@router.post(
    "/fixed-assets/{asset_id}/capitalize",
    response={200: FixedAssetOut, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("fixed_assets", "capitalize")
def capitalize(request, asset_id: int, payload: FixedAssetCapitalizeIn):
    try:
        a, _, _ = capitalize_fixed_asset(
            get_object_or_404(_scope_assets(request, _aqs()), pk=asset_id),
            request.user,
            capitalization_date=payload.capitalization_date,
        )
        return 200, _out(_aqs().get(pk=a.pk))
    except Exception as e:
        return 400, {"detail": str(e)}


@router.get(
    "/fixed-assets/{asset_id}/depreciation-schedule",
    response=List[FixedAssetDepreciationScheduleRowOut],
)
@require_permission("fixed_assets", "view")
def schedule(request, asset_id: int):
    return depreciation_schedule(
        get_object_or_404(_scope_assets(request, _aqs()), pk=asset_id)
    )


@router.post(
    "/fixed-assets/{asset_id}/depreciate",
    response={200: FixedAssetOut, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("fixed_assets", "depreciate")
def depreciate(request, asset_id: int, payload: FixedAssetDepreciateIn):
    try:
        a, _, _ = post_fixed_asset_depreciation(
            get_object_or_404(_scope_assets(request, _aqs()), pk=asset_id),
            payload.period_end,
            request.user,
        )
        return 200, _out(_aqs().get(pk=a.pk))
    except Exception as e:
        return 400, {"detail": str(e)}


@router.post(
    "/fixed-assets/{asset_id}/dispose",
    response={200: FixedAssetOut, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("fixed_assets", "dispose")
def dispose(request, asset_id: int, payload: FixedAssetDisposeIn):
    try:
        a = get_object_or_404(_scope_assets(request, _aqs()), pk=asset_id)
        account = None
        if payload.finance_account_id:
            account = get_object_or_404(
                scope_queryset(
                    request,
                    FinanceAccount.objects.filter(is_active=True),
                    branch_field="branch_id",
                ),
                pk=payload.finance_account_id,
            )
        a, _, _ = dispose_fixed_asset(
            a,
            disposal_date=payload.disposal_date,
            proceeds=payload.proceeds,
            finance_account=account,
            reference=payload.reference,
            notes=payload.notes,
            disposed_by=request.user,
        )
        return 200, _out(_aqs().get(pk=a.pk))
    except Exception as e:
        return 400, {"detail": str(e)}
