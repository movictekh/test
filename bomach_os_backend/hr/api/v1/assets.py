from typing import List, Optional
from ninja import Router, Query
from ninja.pagination import paginate, LimitOffsetPagination
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.core.exceptions import ValidationError
from hr.models.asset import Asset
from hr.api.schemas.asset import AssetCreate, AssetUpdate, AssetOut
from hr.api.schemas import MessageSchema
from user.utils.perm import require_permission, scope_queryset, check_obj_permission

router = Router(tags=['Assets'])

@router.get("/", response=List[AssetOut])
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("assets", "list")
def list_assets(
    request,
    search: Optional[str] = None,
    branch: Optional[str] = None,
    asset_type: Optional[str] = None,
    status: Optional[str] = None
):
    qs = Asset.objects.all()

    if search:
        qs = qs.filter(Q(name__icontains=search) | Q(asset_id__icontains=search))

    if branch:
        qs = qs.filter(branch=branch)

    if asset_type:
        qs = qs.filter(asset_type=asset_type)

    if status:
        qs = qs.filter(status=status)

    return qs

@router.post("/", response={201: AssetOut, 400: MessageSchema})
@require_permission("assets", "create")
def create_asset(request, payload: AssetCreate):
    try:
        asset = Asset.objects.create(**payload.model_dump())
        return 201, asset
    except ValidationError as e:
        return 400, {'detail': e.messages[0]}

@router.get("/{asset_id}", response=AssetOut)
@require_permission("assets", "view")
def get_asset(request, asset_id: int):
    asset = get_object_or_404(Asset, id=asset_id)
    return asset

@router.put("/{asset_id}", response={200: AssetOut, 400: MessageSchema})
@require_permission("assets", "update")
def update_asset(request, asset_id: int, payload: AssetUpdate):
    try:
        asset = get_object_or_404(Asset, id=asset_id)
        for attr, value in payload.model_dump(exclude_unset=True).items():
            setattr(asset, attr, value)
        asset.save()
        return 200, asset
    except ValidationError as e:
        return 400, {'detail': e.messages[0]}

@router.delete("/{asset_id}", response={200: MessageSchema, 400: MessageSchema})
@require_permission("assets", "delete")
def delete_asset(request, asset_id: int):
    try:
        asset = get_object_or_404(Asset, id=asset_id)
        asset.delete()
        return 200, {"detail": "Deleted successfully"}
    except ValidationError as e:
        return 400, {'detail': e.messages[0]}
