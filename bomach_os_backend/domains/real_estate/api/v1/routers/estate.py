from typing import List, Optional

from django.core.exceptions import ValidationError
from ninja import Query, Router
from ninja.pagination import LimitOffsetPagination, paginate

from domains.real_estate.api.v1.schemas.estate import (
    EstateChoicesSchema,
    EstateCreateSchema,
    EstateSchema,
    EstateStatsSchema,
    EstateUpdateSchema,
    PlotLayoutSchema,
    PlotQuickUpdateSchema,
    PropertyChoicesSchema,
    PropertyCreateSchema,
    PropertySchema,
    PropertyUpdateSchema,
    StandalonePropertyCreateSchema,
)
from shared.api.schema.others import MessageSchema
from domains.real_estate.models.estate import Estate, Property
from domains.real_estate.selectors.estate import (
    estate_exists,
    estate_layout as select_estate_layout,
    estate_stats as select_estate_stats,
    get_estate as select_estate,
    get_property as select_property,
    list_estates as select_estates,
    list_properties as select_properties,
    list_standalone_properties as select_standalone_properties,
)
from domains.real_estate.services.estate import (
    create_estate as create_estate_record,
    create_property as create_property_record,
    delete_estate as delete_estate_record,
    delete_property as delete_property_record,
    quick_update_plot as quick_update_plot_record,
    update_estate as update_estate_record,
    update_property as update_property_record,
)
from user.utils.perm import require_permission

estate_api = Router(tags=["Real Estate"])


# Choices endpoint - MUST come before parameterized routes
@estate_api.get("/choices/fields", response=EstateChoicesSchema)
def get_estate_field_choices(request):
    """Get available choices for estate fields"""
    return {
        "estate_type": [
            {"value": c[0], "label": c[1]} for c in Estate.ESTATE_TYPE_CHOICES
        ],
        "estate_status": [
            {"value": c[0], "label": c[1]} for c in Estate.ESTATE_STATUS_CHOICES
        ],
        "area_unit": [{"value": c[0], "label": c[1]} for c in Estate.AREA_UNIT_CHOICES],
    }


@estate_api.get("/", response=List[EstateSchema])
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("estates", "list")
def list_estates(
    request,
    country: Optional[str] = Query(None),
    estate_type: Optional[str] = Query(None),
    is_our_estate: Optional[bool] = Query(None),
    estate_status: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
):
    return select_estates(
        country=country,
        estate_type=estate_type,
        is_our_estate=is_our_estate,
        estate_status=estate_status,
        is_active=is_active,
        search=search,
    )


@estate_api.get("/{estate_id}", response={200: EstateSchema, 404: MessageSchema})
@require_permission("estates", "view")
def get_estate(request, estate_id: int):
    try:
        return 200, select_estate(estate_id)
    except Estate.DoesNotExist:
        return 404, {"detail": "Estate not found"}


@estate_api.post("/", response={201: EstateSchema, 400: MessageSchema})
@require_permission("estates", "create")
def create_estate(request, payload: EstateCreateSchema):
    try:
        return 201, create_estate_record(payload)
    except ValidationError as e:
        return 400, {"detail": e.messages[0] if hasattr(e, "messages") else str(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


@estate_api.put(
    "/{estate_id}", response={200: EstateSchema, 400: MessageSchema, 404: MessageSchema}
)
@require_permission("estates", "update")
def update_estate(request, estate_id: int, payload: EstateUpdateSchema):
    try:
        estate = Estate.objects.get(id=estate_id)
        return 200, update_estate_record(estate, payload)
    except Estate.DoesNotExist:
        return 404, {"detail": "Estate not found"}
    except ValidationError as e:
        return 400, {"detail": e.messages[0] if hasattr(e, "messages") else str(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


@estate_api.delete("/{estate_id}", response={200: MessageSchema, 404: MessageSchema})
@require_permission("estates", "delete")
def delete_estate(request, estate_id: int):
    try:
        estate = Estate.objects.get(id=estate_id)
        delete_estate_record(estate)
        return 200, {"detail": "Estate deleted successfully"}
    except Estate.DoesNotExist:
        return 404, {"detail": "Estate not found"}
    except Exception as e:
        return 400, {"detail": str(e)}


# ============== Property Endpoints ==============


@estate_api.get(
    "/{estate_id}/properties/choices/fields", response=PropertyChoicesSchema
)
def get_property_field_choices(request, estate_id: int):
    """Get available choices for property fields"""
    return {
        "property_type": [
            {"value": c[0], "label": c[1]} for c in Property.PROPERTY_TYPE_CHOICES
        ],
        "property_status": [
            {"value": c[0], "label": c[1]} for c in Property.PROPERTY_STATUS_CHOICES
        ],
        "residential_building_type": [
            {"value": c[0], "label": c[1]} for c in Property.RESIDENTIAL_TYPE_CHOICES
        ],
        "commercial_building_type": [
            {"value": c[0], "label": c[1]} for c in Property.COMMERCIAL_TYPE_CHOICES
        ],
        "area_unit": [
            {"value": c[0], "label": c[1]} for c in Property.AREA_UNIT_CHOICES
        ],
    }


@estate_api.get(
    "/{estate_id}/properties", response={200: List[PropertySchema], 404: MessageSchema}
)
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("properties", "list")
def list_properties(
    request,
    estate_id: int,
    property_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
):
    if not estate_exists(estate_id):
        return []
    return select_properties(
        estate_id=estate_id,
        property_type=property_type,
        status=status,
        is_active=is_active,
        search=search,
    )


@estate_api.get(
    "/{estate_id}/properties/{property_id}",
    response={200: PropertySchema, 404: MessageSchema},
)
@require_permission("properties", "view")
def get_property(request, estate_id: int, property_id: int):
    try:
        return 200, select_property(property_id=property_id, estate_id=estate_id)
    except Property.DoesNotExist:
        return 404, {"detail": "Property not found"}


@estate_api.post(
    "/{estate_id}/properties",
    response={201: PropertySchema, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("properties", "create")
def create_property(request, estate_id: int, payload: PropertyCreateSchema):
    try:
        estate = Estate.objects.get(id=estate_id)
        return 201, create_property_record(payload, estate=estate)
    except Estate.DoesNotExist:
        return 404, {"detail": "Estate not found"}
    except ValidationError as e:
        return 400, {"detail": e.messages[0] if hasattr(e, "messages") else str(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


@estate_api.put(
    "/{estate_id}/properties/{property_id}",
    response={200: PropertySchema, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("properties", "update")
def update_property(
    request, estate_id: int, property_id: int, payload: PropertyUpdateSchema
):
    try:
        prop = Property.objects.select_related("estate").get(
            id=property_id, estate_id=estate_id
        )
        return 200, update_property_record(prop, payload)
    except Property.DoesNotExist:
        return 404, {"detail": "Property not found"}
    except ValidationError as e:
        return 400, {"detail": e.messages[0] if hasattr(e, "messages") else str(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


@estate_api.delete(
    "/{estate_id}/properties/{property_id}",
    response={200: MessageSchema, 404: MessageSchema},
)
@require_permission("properties", "delete")
def delete_property(request, estate_id: int, property_id: int):
    try:
        prop = Property.objects.get(id=property_id, estate_id=estate_id)
        delete_property_record(prop)
        return 200, {"detail": "Property deleted successfully"}
    except Property.DoesNotExist:
        return 404, {"detail": "Property not found"}
    except Exception as e:
        return 400, {"detail": str(e)}


# ============== Estate Stats & Plot Layout ==============


@estate_api.get(
    "/{estate_id}/stats", response={200: EstateStatsSchema, 404: MessageSchema}
)
@require_permission("estates", "view")
def estate_stats(request, estate_id: int):
    stats = select_estate_stats(estate_id)
    if stats is None:
        return 404, {"detail": "Estate not found"}
    return 200, stats


@estate_api.get(
    "/{estate_id}/layout", response={200: List[PlotLayoutSchema], 404: MessageSchema}
)
@require_permission("properties", "list")
def estate_layout(request, estate_id: int):
    layout = select_estate_layout(estate_id)
    if layout is None:
        return 404, {"detail": "Estate not found"}
    return 200, layout


@estate_api.patch(
    "/{estate_id}/plots/{property_id}/quick-update",
    response={200: PlotLayoutSchema, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("properties", "update")
def quick_update_plot(
    request, estate_id: int, property_id: int, payload: PlotQuickUpdateSchema
):
    try:
        prop = Property.objects.get(id=property_id, estate_id=estate_id)
    except Property.DoesNotExist:
        return 404, {"detail": "Property not found"}

    update_data = payload.dict(exclude_unset=True)
    if not update_data:
        return 400, {"detail": "No fields to update."}

    if "status" in update_data and update_data["status"] is not None:
        valid_statuses = [c[0] for c in Property.PROPERTY_STATUS_CHOICES]
        if update_data["status"] not in valid_statuses:
            return 400, {
                "detail": f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
            }

    try:
        prop = quick_update_plot_record(prop, update_data)
    except ValidationError as e:
        return 400, {"detail": e.messages[0] if hasattr(e, "messages") else str(e)}
    except Exception as e:
        return 400, {"detail": str(e)}

    return 200, {
        "id": prop.id,
        "plot_number": prop.plot_number,
        "property_name": prop.property_name,
        "status": prop.status,
        "status_display": prop.get_status_display(),
        "plot_size": prop.plot_size,
        "price": prop.price,
        "client_name": prop.client_name,
    }






# ============== Standalone Property Endpoints (with or without estate) ==============


@estate_api.get("/properties/all", response=List[PropertySchema])
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("properties", "list")
def list_all_properties(
    request,
    property_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
):
    return select_standalone_properties(
        property_type=property_type,
        status=status,
        is_active=is_active,
        search=search,
    )


@estate_api.get(
    "/properties/all/{property_id}", response={200: PropertySchema, 404: MessageSchema}
)
@require_permission("properties", "view")
def get_standalone_property(request, property_id: int):
    try:
        return 200, select_property(property_id=property_id)
    except Property.DoesNotExist:
        return 404, {"detail": "Property not found"}


@estate_api.post("/properties/all", response={201: PropertySchema, 400: MessageSchema})
@require_permission("properties", "create")
def create_standalone_property(request, payload: StandalonePropertyCreateSchema):
    try:
        return 201, create_property_record(payload, estate=None)
    except ValidationError as e:
        return 400, {"detail": e.messages[0] if hasattr(e, "messages") else str(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


@estate_api.put(
    "/properties/all/{property_id}",
    response={200: PropertySchema, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("properties", "update")
def update_standalone_property(
    request, property_id: int, payload: PropertyUpdateSchema
):
    try:
        prop = Property.objects.select_related("estate").get(id=property_id)
        return 200, update_property_record(prop, payload)
    except Property.DoesNotExist:
        return 404, {"detail": "Property not found"}
    except ValidationError as e:
        return 400, {"detail": e.messages[0] if hasattr(e, "messages") else str(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


@estate_api.delete(
    "/properties/all/{property_id}", response={200: MessageSchema, 404: MessageSchema}
)
@require_permission("properties", "delete")
def delete_standalone_property(request, property_id: int):
    try:
        prop = Property.objects.get(id=property_id)
        delete_property_record(prop)
        return 200, {"detail": "Property deleted successfully"}
    except Property.DoesNotExist:
        return 404, {"detail": "Property not found"}
    except Exception as e:
        return 400, {"detail": str(e)}
