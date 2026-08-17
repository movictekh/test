from decimal import Decimal
from typing import List, Optional

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.shortcuts import get_object_or_404
from ninja import Query, Router
from ninja.pagination import LimitOffsetPagination, paginate

from user.api.schemas.estate import (
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
from user.api.schemas.others import MessageSchema
from user.models.estate import Estate, EstateDocument, Property, PropertyImage
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
    """List all estates with filtering and search"""
    estates = Estate.objects.prefetch_related("documents").all()

    if country:
        estates = estates.filter(country__icontains=country)

    if is_our_estate is not None:
        estates = estates.filter(is_our_estate=is_our_estate)

    if estate_type:
        estates = estates.filter(estate_type=estate_type)

    if estate_status:
        estates = estates.filter(estate_status=estate_status)

    if is_active is not None:
        estates = estates.filter(is_active=is_active)

    if search:
        estates = estates.filter(
            Q(estate_name__icontains=search)
            | Q(estate_code__icontains=search)
            | Q(developer_company_name__icontains=search)
            | Q(country__icontains=search)
            | Q(state__icontains=search)
            | Q(city_town__icontains=search)
        )

    return estates.order_by("-created_at")


@estate_api.get("/{estate_id}", response={200: EstateSchema, 404: MessageSchema})
@require_permission("estates", "view")
def get_estate(request, estate_id: int):
    """Get estate details by ID"""
    try:
        estate = Estate.objects.prefetch_related("documents").get(id=estate_id)
        return 200, estate
    except Estate.DoesNotExist:
        return 404, {"detail": "Estate not found"}


@estate_api.post("/", response={201: EstateSchema, 400: MessageSchema})
@require_permission("estates", "create")
def create_estate(request, payload: EstateCreateSchema):
    """Create a new estate"""
    try:
        data = payload.dict(exclude={"documents", "tags", "boundary"})
        data = {k: v for k, v in data.items() if v is not None}

        estate = Estate.objects.create(
            **data,
            tags=payload.tags or [],
            boundary=(
                [{"lat": float(c.lat), "lng": float(c.lng)} for c in payload.boundary]
                if payload.boundary
                else []
            ),
        )

        # Handle estate documents if provided
        if payload.documents:
            _save_estate_documents(estate, payload.documents)

        return 201, estate

    except ValidationError as e:
        return 400, {"detail": e.messages[0] if hasattr(e, "messages") else str(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


@estate_api.put(
    "/{estate_id}", response={200: EstateSchema, 400: MessageSchema, 404: MessageSchema}
)
@require_permission("estates", "update")
def update_estate(request, estate_id: int, payload: EstateUpdateSchema):
    """Update an estate"""
    try:
        estate = Estate.objects.get(id=estate_id)
        update_data = payload.dict(exclude_unset=True)

        # Handle boundary update
        if "boundary" in update_data:
            boundary_data = update_data.pop("boundary")
            estate.boundary = (
                [
                    {"lat": float(c["lat"]), "lng": float(c["lng"])}
                    for c in boundary_data
                ]
                if boundary_data
                else []
            )

        # Handle estate documents update (replaces all existing)
        if "documents" in update_data:
            doc_urls = update_data.pop("documents")
            if doc_urls is not None:
                # Delete old documents
                for doc in estate.documents.all():
                    doc.file.delete(save=False)
                estate.documents.all().delete()
                _save_estate_documents(estate, doc_urls)

        # Update remaining fields
        for field, value in update_data.items():
            if value is not None:
                setattr(estate, field, value)

        estate.full_clean()
        estate.save()
        estate.refresh_from_db()

        return 200, estate

    except Estate.DoesNotExist:
        return 404, {"detail": "Estate not found"}
    except ValidationError as e:
        return 400, {"detail": e.messages[0] if hasattr(e, "messages") else str(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


@estate_api.delete("/{estate_id}", response={200: MessageSchema, 404: MessageSchema})
@require_permission("estates", "delete")
def delete_estate(request, estate_id: int):
    """Delete an estate"""
    try:
        estate = Estate.objects.get(id=estate_id)
        estate.delete()
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
    """List all properties for an estate"""
    if not Estate.objects.filter(id=estate_id).exists():
        return []

    properties = (
        Property.objects.select_related("estate")
        .prefetch_related("images")
        .filter(estate_id=estate_id)
    )

    if property_type:
        properties = properties.filter(property_type=property_type)

    if status:
        properties = properties.filter(status=status)

    if is_active is not None:
        properties = properties.filter(is_active=is_active)

    if search:
        properties = properties.filter(
            Q(property_name__icontains=search) | Q(description__icontains=search)
        )

    return properties.order_by("property_name")


@estate_api.get(
    "/{estate_id}/properties/{property_id}",
    response={200: PropertySchema, 404: MessageSchema},
)
@require_permission("properties", "view")
def get_property(request, estate_id: int, property_id: int):
    """Get property details"""
    try:
        prop = (
            Property.objects.select_related("estate")
            .prefetch_related("images")
            .get(id=property_id, estate_id=estate_id)
        )
        return 200, prop
    except Property.DoesNotExist:
        return 404, {"detail": "Property not found"}


@estate_api.post(
    "/{estate_id}/properties",
    response={201: PropertySchema, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("properties", "create")
def create_property(request, estate_id: int, payload: PropertyCreateSchema):
    """Create a new property in an estate"""
    try:
        estate = Estate.objects.get(id=estate_id)

        data = payload.dict(exclude={"images", "boundary"})
        data = {k: v for k, v in data.items() if v is not None}

        prop = Property.objects.create(
            estate=estate,
            boundary=(
                [{"lat": float(c.lat), "lng": float(c.lng)} for c in payload.boundary]
                if payload.boundary
                else []
            ),
            **data,
        )

        # Handle images if provided
        if payload.images:
            _save_property_images(prop, payload.images)

        return 201, prop

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
    """Update a property"""
    try:
        prop = Property.objects.select_related("estate").get(
            id=property_id, estate_id=estate_id
        )
        update_data = payload.dict(exclude_unset=True)

        # Handle boundary update
        if "boundary" in update_data:
            boundary_data = update_data.pop("boundary")
            prop.boundary = (
                [
                    {"lat": float(c["lat"]), "lng": float(c["lng"])}
                    for c in boundary_data
                ]
                if boundary_data
                else []
            )

        # Handle images update (replaces all existing)
        if "images" in update_data:
            image_urls = update_data.pop("images")
            if image_urls is not None:
                # Delete old images
                for img in prop.images.all():
                    img.image.delete(save=False)
                prop.images.all().delete()
                _save_property_images(prop, image_urls)

        for field, value in update_data.items():
            if value is not None:
                setattr(prop, field, value)

        prop.full_clean()
        prop.save()
        prop.refresh_from_db()

        return 200, prop

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
    """Delete a property"""
    try:
        prop = Property.objects.get(id=property_id, estate_id=estate_id)
        prop.delete()
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
    """Get plot/property statistics for an estate (sold, reserved, available, hold, etc.)."""
    if not Estate.objects.filter(id=estate_id).exists():
        return 404, {"detail": "Estate not found"}

    props = Property.objects.filter(estate_id=estate_id)
    total = props.count()
    sold = props.filter(status="sold").count()
    reserved = props.filter(status="reserved").count()
    available = props.filter(status="available").count()
    hold = props.filter(status="hold").count()
    not_for_sale = props.filter(status="not-for-sale").count()

    total_value = props.aggregate(sum=models.Sum("price"))["sum"] or Decimal("0")
    sold_value = props.filter(status="sold").aggregate(sum=models.Sum("price"))[
        "sum"
    ] or Decimal("0")

    return 200, {
        "total": total,
        "sold": sold,
        "reserved": reserved,
        "available": available,
        "hold": hold,
        "not_for_sale": not_for_sale,
        "total_value": total_value,
        "sold_value": sold_value,
    }


@estate_api.get(
    "/{estate_id}/layout", response={200: List[PlotLayoutSchema], 404: MessageSchema}
)
@require_permission("properties", "list")
def estate_layout(request, estate_id: int):
    """Get the full plot grid for an estate, optimized for grid visualization."""
    if not Estate.objects.filter(id=estate_id).exists():
        return 404, {"detail": "Estate not found"}

    props = Property.objects.filter(estate_id=estate_id).order_by(
        "plot_number", "property_name"
    )
    return 200, [
        {
            "id": p.id,
            "plot_number": p.plot_number,
            "property_name": p.property_name,
            "status": p.status,
            "status_display": p.get_status_display(),
            "plot_size": p.plot_size,
            "price": p.price,
            "client_name": p.client_name,
        }
        for p in props
    ]


@estate_api.patch(
    "/{estate_id}/plots/{property_id}/quick-update",
    response={200: PlotLayoutSchema, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("properties", "update")
def quick_update_plot(
    request, estate_id: int, property_id: int, payload: PlotQuickUpdateSchema
):
    """Rapidly update a plot's status, price and/or client/reservation holder from the estate grid."""
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

    for field, value in update_data.items():
        if value is not None:
            setattr(prop, field, value)

    try:
        prop.full_clean()
        prop.save()
    except ValidationError as e:
        return 400, {"detail": e.messages[0] if hasattr(e, "messages") else str(e)}
    except Exception as e:
        return 400, {"detail": str(e)}

    prop.refresh_from_db()
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


def _save_estate_documents(estate, doc_urls):
    """Helper to save estate documents from uploaded URLs"""
    from urllib.parse import urlparse

    for url in doc_urls:
        if url.startswith("http"):
            parsed = urlparse(url)
            file_path = parsed.path.lstrip("/")
        else:
            file_path = url
        EstateDocument.objects.create(estate=estate, file=file_path)


def _save_property_images(prop, image_urls):
    """Helper to save property images from uploaded URLs"""
    from urllib.parse import urlparse

    for url in image_urls:
        if url.startswith("http"):
            parsed = urlparse(url)
            file_path = parsed.path.lstrip("/")
        else:
            file_path = url
        PropertyImage.objects.create(property=prop, image=file_path)


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
    """List standalone properties (properties that don't belong to any estate)."""
    properties = (
        Property.objects.select_related("estate")
        .prefetch_related("images")
        .filter(estate__isnull=True)
    )

    if property_type:
        properties = properties.filter(property_type=property_type)

    if status:
        properties = properties.filter(status=status)

    if is_active is not None:
        properties = properties.filter(is_active=is_active)

    if search:
        properties = properties.filter(
            Q(property_name__icontains=search) | Q(description__icontains=search)
        )

    return properties.order_by("-created_at")


@estate_api.get(
    "/properties/all/{property_id}", response={200: PropertySchema, 404: MessageSchema}
)
@require_permission("properties", "view")
def get_standalone_property(request, property_id: int):
    """Get any property by ID (with or without estate)."""
    try:
        prop = (
            Property.objects.select_related("estate")
            .prefetch_related("images")
            .get(id=property_id)
        )
        return 200, prop
    except Property.DoesNotExist:
        return 404, {"detail": "Property not found"}


@estate_api.post("/properties/all", response={201: PropertySchema, 400: MessageSchema})
@require_permission("properties", "create")
def create_standalone_property(request, payload: StandalonePropertyCreateSchema):
    """Create a standalone property (not linked to any estate)."""
    try:
        data = payload.dict(exclude={"images", "boundary"})
        data = {k: v for k, v in data.items() if v is not None}

        prop = Property.objects.create(
            estate=None,
            boundary=(
                [{"lat": float(c.lat), "lng": float(c.lng)} for c in payload.boundary]
                if payload.boundary
                else []
            ),
            **data,
        )

        if payload.images:
            _save_property_images(prop, payload.images)

        return 201, prop

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
    """Update any property by ID (with or without estate)."""
    try:
        prop = Property.objects.select_related("estate").get(id=property_id)
        update_data = payload.dict(exclude_unset=True)

        # Handle boundary update
        if "boundary" in update_data:
            boundary_data = update_data.pop("boundary")
            prop.boundary = (
                [
                    {"lat": float(c["lat"]), "lng": float(c["lng"])}
                    for c in boundary_data
                ]
                if boundary_data
                else []
            )

        # Handle images update (replaces all existing)
        if "images" in update_data:
            image_urls = update_data.pop("images")
            if image_urls is not None:
                for img in prop.images.all():
                    img.image.delete(save=False)
                prop.images.all().delete()
                _save_property_images(prop, image_urls)

        for field, value in update_data.items():
            if value is not None:
                setattr(prop, field, value)

        prop.full_clean()
        prop.save()
        prop.refresh_from_db()

        return 200, prop

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
    """Delete any property by ID (with or without estate)."""
    try:
        prop = Property.objects.get(id=property_id)
        prop.delete()
        return 200, {"detail": "Property deleted successfully"}

    except Property.DoesNotExist:
        return 404, {"detail": "Property not found"}
    except Exception as e:
        return 400, {"detail": str(e)}
