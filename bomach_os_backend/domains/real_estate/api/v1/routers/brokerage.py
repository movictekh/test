from typing import List, Optional

from django.core.exceptions import ValidationError
from ninja import Query, Router
from ninja.pagination import LimitOffsetPagination, paginate

from domains.real_estate.api.v1.schemas.estate import (
    BrokerageChoicesSchema,
    BrokerageListingCreateSchema,
    BrokerageListingSchema,
    BrokerageListingUpdateSchema,
    BrokerageListingVerifySchema,
    BrokerageStatsSchema,
)
from shared.api.schema.others import MessageSchema
from domains.real_estate.models.brokerage import BrokerageListing
from domains.real_estate.selectors.brokerage import (
    brokerage_stats as select_brokerage_stats,
    get_brokerage_listing as select_brokerage_listing,
    list_brokerage_listings as select_brokerage_listings,
)
from domains.real_estate.services.brokerage import (
    create_brokerage_listing as create_brokerage_listing_record,
    delete_brokerage_listing as delete_brokerage_listing_record,
    update_brokerage_listing as update_brokerage_listing_record,
    verify_brokerage_listing as verify_brokerage_listing_record,
)
from system.authorization import require_permission

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
    return select_brokerage_stats()


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
    return select_brokerage_listings(
        status=status,
        verification_status=verification_status,
        property_type=property_type,
        is_active=is_active,
        search=search,
    )


@brokerage_api.post("/", response={201: BrokerageListingSchema, 400: MessageSchema})
@require_permission("brokerage", "create")
def create_brokerage_listing(request, payload: BrokerageListingCreateSchema):
    try:
        return 201, create_brokerage_listing_record(payload)
    except ValidationError as e:
        return 400, {"detail": e.messages[0] if hasattr(e, "messages") else str(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


@brokerage_api.get(
    "/{listing_id}", response={200: BrokerageListingSchema, 404: MessageSchema}
)
@require_permission("brokerage", "view")
def get_brokerage_listing(request, listing_id: int):
    try:
        return 200, select_brokerage_listing(listing_id)
    except BrokerageListing.DoesNotExist:
        return 404, {"detail": "Brokerage listing not found"}


@brokerage_api.put(
    "/{listing_id}",
    response={200: BrokerageListingSchema, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("brokerage", "update")
def update_brokerage_listing(
    request, listing_id: int, payload: BrokerageListingUpdateSchema
):
    try:
        listing = BrokerageListing.objects.get(id=listing_id)
        return 200, update_brokerage_listing_record(listing, payload)
    except BrokerageListing.DoesNotExist:
        return 404, {"detail": "Brokerage listing not found"}
    except ValidationError as e:
        return 400, {"detail": e.messages[0] if hasattr(e, "messages") else str(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


@brokerage_api.patch(
    "/{listing_id}/verify",
    response={200: BrokerageListingSchema, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("brokerage", "update")
def verify_brokerage_listing(
    request, listing_id: int, payload: BrokerageListingVerifySchema
):
    try:
        listing = BrokerageListing.objects.get(id=listing_id)
    except BrokerageListing.DoesNotExist:
        return 404, {"detail": "Brokerage listing not found"}

    valid_statuses = [c[0] for c in BrokerageListing.VERIFICATION_STATUS_CHOICES]
    if payload.verification_status not in valid_statuses:
        return 400, {
            "detail": f"Invalid verification status. Must be one of: {', '.join(valid_statuses)}"
        }

    return 200, verify_brokerage_listing_record(
        listing, payload.verification_status
    )


@brokerage_api.delete(
    "/{listing_id}", response={200: MessageSchema, 404: MessageSchema}
)
@require_permission("brokerage", "delete")
def delete_brokerage_listing(request, listing_id: int):
    try:
        listing = BrokerageListing.objects.get(id=listing_id)
        delete_brokerage_listing_record(listing)
        return 200, {"detail": "Brokerage listing deleted successfully"}
    except BrokerageListing.DoesNotExist:
        return 404, {"detail": "Brokerage listing not found"}
    except Exception as e:
        return 400, {"detail": str(e)}
