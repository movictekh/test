from ninja import Router
from typing import List
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.core.exceptions import ValidationError

from operations.models import SiteEquipment, Worksite
from ..schemas.schemas import SiteEquipmentCreateSchema, SiteEquipmentUpdateSchema, SiteEquipmentOutSchema, MessageSchema
from ninja.pagination import paginate, LimitOffsetPagination
from user.utils.perm import require_permission

router = Router(tags=["Site Equipment"])


@router.get("", response=List[SiteEquipmentOutSchema], operation_id="operations_api_v1_site_equipment_list_site_equipment")
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("site_equipment", "list")
def list_site_equipment(
    request,
    worksite_id: int = None,
    search: str = None,
):
    """List all site equipment with optional filters"""
    equipment = SiteEquipment.objects.all()

    if worksite_id:
        equipment = equipment.filter(worksite_id=worksite_id)
    if search:
        equipment = equipment.filter(
            Q(name__icontains=search) |
            Q(unit_value__icontains=search)
        )

    return list(equipment)


@router.get("/{equipment_id}", response=SiteEquipmentOutSchema, operation_id="operations_api_v1_site_equipment_get_site_equipment")
@require_permission("site_equipment", "view")
def get_site_equipment(request, equipment_id: int):
    """Get a specific site equipment item by ID"""
    equipment = get_object_or_404(SiteEquipment, id=equipment_id)
    return equipment


@router.post("", response={200: SiteEquipmentOutSchema, 400: MessageSchema}, operation_id="operations_api_v1_site_equipment_create_site_equipment")
@require_permission("site_equipment", "create")
def create_site_equipment(request, payload: SiteEquipmentCreateSchema):
    """Create a new site equipment item"""
    try:
        equipment_data = payload.dict()
        worksite = get_object_or_404(Worksite, id=equipment_data.pop('worksite_id'))
        equipment = SiteEquipment.objects.create(worksite=worksite, **equipment_data)
        return equipment
    except ValidationError as e:
        return 400, {'detail': e.messages[0]}


@router.put("/{equipment_id}", response={200: SiteEquipmentOutSchema, 400: MessageSchema}, operation_id="operations_api_v1_site_equipment_update_site_equipment")
@require_permission("site_equipment", "update")
def update_site_equipment(request, equipment_id: int, payload: SiteEquipmentUpdateSchema):
    """Update an existing site equipment item"""
    try:
        equipment = get_object_or_404(SiteEquipment, id=equipment_id)

        update_data = payload.dict(exclude_unset=True)
        if 'worksite_id' in update_data:
            worksite = get_object_or_404(Worksite, id=update_data.pop('worksite_id'))
            equipment.worksite = worksite

        for attr, value in update_data.items():
            setattr(equipment, attr, value)

        equipment.save()
        return equipment
    except ValidationError as e:
        return 400, {'detail': e.messages[0]}


@router.delete("/{equipment_id}", operation_id="operations_api_v1_site_equipment_delete_site_equipment")
@require_permission("site_equipment", "delete")
def delete_site_equipment(request, equipment_id: int):
    """Delete a site equipment item"""
    equipment = get_object_or_404(SiteEquipment, id=equipment_id)
    equipment.delete()
    return {"detail": "Site equipment deleted successfully"}
