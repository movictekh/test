from decimal import Decimal

from django.db import models
from django.db.models import Q

from domains.real_estate.models.estate import Estate, Property


def list_estates(
    *,
    country=None,
    estate_type=None,
    is_our_estate=None,
    estate_status=None,
    is_active=None,
    search=None,
):
    qs = Estate.objects.prefetch_related("documents").all()
    if country:
        qs = qs.filter(country__icontains=country)
    if is_our_estate is not None:
        qs = qs.filter(is_our_estate=is_our_estate)
    if estate_type:
        qs = qs.filter(estate_type=estate_type)
    if estate_status:
        qs = qs.filter(estate_status=estate_status)
    if is_active is not None:
        qs = qs.filter(is_active=is_active)
    if search:
        qs = qs.filter(
            Q(estate_name__icontains=search)
            | Q(estate_code__icontains=search)
            | Q(developer_company_name__icontains=search)
            | Q(country__icontains=search)
            | Q(state__icontains=search)
            | Q(city_town__icontains=search)
        )
    return qs.order_by("-created_at")


def get_estate(estate_id):
    return Estate.objects.prefetch_related("documents").get(id=estate_id)


def estate_exists(estate_id):
    return Estate.objects.filter(id=estate_id).exists()


def list_properties(
    *,
    estate_id,
    property_type=None,
    status=None,
    is_active=None,
    search=None,
):
    qs = (
        Property.objects.select_related("estate")
        .prefetch_related("images")
        .filter(estate_id=estate_id)
    )
    if property_type:
        qs = qs.filter(property_type=property_type)
    if status:
        qs = qs.filter(status=status)
    if is_active is not None:
        qs = qs.filter(is_active=is_active)
    if search:
        qs = qs.filter(
            Q(property_name__icontains=search) | Q(description__icontains=search)
        )
    return qs.order_by("property_name")


def get_property(*, property_id, estate_id=None):
    qs = Property.objects.select_related("estate").prefetch_related("images")
    filters = {"id": property_id}
    if estate_id is not None:
        filters["estate_id"] = estate_id
    return qs.get(**filters)


def estate_stats(estate_id):
    if not estate_exists(estate_id):
        return None
    qs = Property.objects.filter(estate_id=estate_id)
    return {
        "total": qs.count(),
        "sold": qs.filter(status="sold").count(),
        "reserved": qs.filter(status="reserved").count(),
        "available": qs.filter(status="available").count(),
        "hold": qs.filter(status="hold").count(),
        "not_for_sale": qs.filter(status="not-for-sale").count(),
        "total_value": qs.aggregate(sum=models.Sum("price"))["sum"] or Decimal("0"),
        "sold_value": (
            qs.filter(status="sold").aggregate(sum=models.Sum("price"))["sum"]
            or Decimal("0")
        ),
    }


def estate_layout(estate_id):
    if not estate_exists(estate_id):
        return None
    qs = Property.objects.filter(estate_id=estate_id).order_by(
        "plot_number", "property_name"
    )
    return [
        {
            "id": prop.id,
            "plot_number": prop.plot_number,
            "property_name": prop.property_name,
            "status": prop.status,
            "status_display": prop.get_status_display(),
            "plot_size": prop.plot_size,
            "price": prop.price,
            "client_name": prop.client_name,
        }
        for prop in qs
    ]


def list_standalone_properties(
    *,
    property_type=None,
    status=None,
    is_active=None,
    search=None,
):
    qs = (
        Property.objects.select_related("estate")
        .prefetch_related("images")
        .filter(estate__isnull=True)
    )
    if property_type:
        qs = qs.filter(property_type=property_type)
    if status:
        qs = qs.filter(status=status)
    if is_active is not None:
        qs = qs.filter(is_active=is_active)
    if search:
        qs = qs.filter(
            Q(property_name__icontains=search) | Q(description__icontains=search)
        )
    return qs.order_by("-created_at")
