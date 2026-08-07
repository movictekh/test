from ninja import Router, Query
from ninja.pagination import paginate, LimitOffsetPagination

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from decimal import Decimal
from typing import Optional, List

from user.api.schemas.others import MessageSchema
from user.models.brokerage import BrokerageListing, BrokerageListingImage
from user.api.schemas.estate import (
    BrokerageChoicesSchema,
    BrokerageListingCreateSchema,
    BrokerageListingSchema,
    BrokerageListingUpdateSchema,
    BrokerageListingVerifySchema,
    BrokerageStatsSchema,
)
from user.utils.perm import require_permission


brokerage_api = Router(tags=["Brokerage"])


@brokerage_api.get("/choices/fields", response=BrokerageChoicesSchema)
def get_brokerage_field_choices(request):
    """Get available choices for brokerage listing fields"""
    return {
        "verification_status": [
            {"value": c[0], "label": c[1]}
            for c in BrokerageListing.VERIFICATION_STATUS_CHOICES
        ],
        "listing_status": [
            {"value": c[0], "label": c[1]}
            for c in BrokerageListing.LISTING_STATUS_CHOICES
        ],
        "property_type": [
            {"value": c[0], "label": c[1]}
            for c in BrokerageListing.PROPERTY_TYPE_CHOICES
        ],
    }


@brokerage_api.get("/stats", response=BrokerageStatsSchema)
@require_permission("brokerage", "list")
def brokerage_stats(request):
    """Get summary statistics for brokerage listings."""
    listings = BrokerageListing.objects.all()
    total = listings.count()
    total_value = listings.aggregate(sum=models.Sum('price'))['sum'] or Decimal('0')

    return {
        'total': total,
        'verified': listings.filter(verification_status='verified').count(),
        'pending_verification': listings.filter(verification_status='pending').count(),
        'inspection_due': listings.filter(verification_status='inspection_due').count(),
        'sold': listings.filter(status='sold').count(),
        'available': listings.filter(status='available').count(),
        'off_market': listings.filter(status='off_market').count(),
        'total_listing_value': total_value,
    }


@brokerage_api.get("/", response=List[BrokerageListingSchema])
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("brokerage", "list")
def list_brokerage_listings(
    request,
    status: Optional[str] = Query(None),
    verification_status: Optional[str] = Query(None),
    property_type: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
):
    """List brokerage listings with filtering and search."""
    listings = BrokerageListing.objects.select_related('assigned_agent', 'estate').prefetch_related('images').all()

    if status:
        listings = listings.filter(status=status)

    if verification_status:
        listings = listings.filter(verification_status=verification_status)

    if property_type:
        listings = listings.filter(property_type=property_type)

    if is_active is not None:
        listings = listings.filter(is_active=is_active)

    if search:
        listings = listings.filter(
            Q(title__icontains=search) |
            Q(location__icontains=search) |
            Q(owner_name__icontains=search) |
            Q(description__icontains=search)
        )

    return listings.order_by('-created_at')


@brokerage_api.post("/", response={201: BrokerageListingSchema, 400: MessageSchema})
@require_permission("brokerage", "create")
def create_brokerage_listing(request, payload: BrokerageListingCreateSchema):
    """Create a new brokerage listing."""
    try:
        data = payload.dict(exclude={'images', 'tags'})
        data = {k: v for k, v in data.items() if v is not None}

        assigned_agent_id = data.pop('assigned_agent_id', None)
        estate_id = data.pop('estate_id', None)

        listing = BrokerageListing.objects.create(
            **data,
            tags=payload.tags or [],
            assigned_agent_id=assigned_agent_id,
            estate_id=estate_id,
        )

        if payload.images:
            _save_listing_images(listing, payload.images)

        return 201, listing

    except ValidationError as e:
        return 400, {'detail': e.messages[0] if hasattr(e, 'messages') else str(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


@brokerage_api.get("/{listing_id}", response={200: BrokerageListingSchema, 404: MessageSchema})
@require_permission("brokerage", "view")
def get_brokerage_listing(request, listing_id: int):
    """Get brokerage listing details."""
    try:
        listing = BrokerageListing.objects.select_related('assigned_agent', 'estate').prefetch_related('images').get(
            id=listing_id
        )
        return 200, listing
    except BrokerageListing.DoesNotExist:
        return 404, {"detail": "Brokerage listing not found"}


@brokerage_api.put("/{listing_id}", response={200: BrokerageListingSchema, 400: MessageSchema, 404: MessageSchema})
@require_permission("brokerage", "update")
def update_brokerage_listing(request, listing_id: int, payload: BrokerageListingUpdateSchema):
    """Update a brokerage listing."""
    try:
        listing = BrokerageListing.objects.get(id=listing_id)
        update_data = payload.dict(exclude_unset=True)

        if 'images' in update_data:
            image_urls = update_data.pop('images')
            if image_urls is not None:
                for img in listing.images.all():
                    img.image.delete(save=False)
                listing.images.all().delete()
                _save_listing_images(listing, image_urls)

        if 'assigned_agent_id' in update_data:
            agent_id = update_data.pop('assigned_agent_id')
            listing.assigned_agent_id = agent_id

        if 'estate_id' in update_data:
            estate_id = update_data.pop('estate_id')
            listing.estate_id = estate_id

        for field, value in update_data.items():
            if value is not None:
                setattr(listing, field, value)

        listing.full_clean()
        listing.save()
        listing.refresh_from_db()
        return 200, listing

    except BrokerageListing.DoesNotExist:
        return 404, {"detail": "Brokerage listing not found"}
    except ValidationError as e:
        return 400, {'detail': e.messages[0] if hasattr(e, 'messages') else str(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


@brokerage_api.patch(
    "/{listing_id}/verify",
    response={200: BrokerageListingSchema, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("brokerage", "update")
def verify_brokerage_listing(request, listing_id: int, payload: BrokerageListingVerifySchema):
    """Update the verification status of a brokerage listing."""
    try:
        listing = BrokerageListing.objects.get(id=listing_id)
    except BrokerageListing.DoesNotExist:
        return 404, {"detail": "Brokerage listing not found"}

    valid_statuses = [c[0] for c in BrokerageListing.VERIFICATION_STATUS_CHOICES]
    if payload.verification_status not in valid_statuses:
        return 400, {"detail": f"Invalid verification status. Must be one of: {', '.join(valid_statuses)}"}

    listing.verification_status = payload.verification_status
    listing.save(update_fields=['verification_status', 'updated_at'])
    listing.refresh_from_db()
    return 200, listing


@brokerage_api.delete("/{listing_id}", response={200: MessageSchema, 404: MessageSchema})
@require_permission("brokerage", "delete")
def delete_brokerage_listing(request, listing_id: int):
    """Delete a brokerage listing."""
    try:
        listing = BrokerageListing.objects.get(id=listing_id)
        listing.delete()
        return 200, {"detail": "Brokerage listing deleted successfully"}
    except BrokerageListing.DoesNotExist:
        return 404, {"detail": "Brokerage listing not found"}
    except Exception as e:
        return 400, {"detail": str(e)}


def _save_listing_images(listing, image_urls):
    """Helper to save brokerage listing images from uploaded URLs"""
    from urllib.parse import urlparse
    for url in image_urls:
        if url.startswith('http'):
            parsed = urlparse(url)
            file_path = parsed.path.lstrip('/')
        else:
            file_path = url
        BrokerageListingImage.objects.create(listing=listing, image=file_path)
