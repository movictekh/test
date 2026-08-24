from decimal import Decimal

from django.db import models
from django.db.models import Q

from domains.real_estate.models.brokerage import BrokerageListing


def list_brokerage_listings(
    *,
    status=None,
    verification_status=None,
    property_type=None,
    is_active=None,
    search=None,
):
    qs = (
        BrokerageListing.objects.select_related("assigned_agent", "estate")
        .prefetch_related("images")
        .all()
    )
    if status:
        qs = qs.filter(status=status)
    if verification_status:
        qs = qs.filter(verification_status=verification_status)
    if property_type:
        qs = qs.filter(property_type=property_type)
    if is_active is not None:
        qs = qs.filter(is_active=is_active)
    if search:
        qs = qs.filter(
            Q(title__icontains=search)
            | Q(location__icontains=search)
            | Q(owner_name__icontains=search)
            | Q(description__icontains=search)
        )
    return qs.order_by("-created_at")


def get_brokerage_listing(listing_id):
    return (
        BrokerageListing.objects.select_related("assigned_agent", "estate")
        .prefetch_related("images")
        .get(id=listing_id)
    )


def brokerage_stats():
    qs = BrokerageListing.objects.all()
    return {
        "total": qs.count(),
        "verified": qs.filter(verification_status="verified").count(),
        "pending_verification": qs.filter(verification_status="pending").count(),
        "inspection_due": qs.filter(verification_status="inspection_due").count(),
        "sold": qs.filter(status="sold").count(),
        "available": qs.filter(status="available").count(),
        "off_market": qs.filter(status="off_market").count(),
        "total_listing_value": (
            qs.aggregate(sum=models.Sum("price"))["sum"] or Decimal("0")
        ),
    }
