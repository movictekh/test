from django.db.models import Q

from domains.real_estate.models.property_purchase import PropertyPurchase
from domains.real_estate.payment_contract import PROPERTY_PURCHASE_PURPOSE_TYPE
from system.payments.models import PaymentIntent


def property_purchase_queryset():
    return PropertyPurchase.objects.select_related(
        "property",
        "property__estate",
        "client",
        "client__user",
        "invoice",
        "created_by",
    )


def list_property_purchases(
    *,
    status=None,
    mode=None,
    client_id=None,
    estate_id=None,
    property_id=None,
    search=None,
):
    qs = property_purchase_queryset()
    if status:
        qs = qs.filter(status=status)
    if mode:
        qs = qs.filter(mode=mode)
    if client_id:
        qs = qs.filter(client_id=client_id)
    if estate_id:
        qs = qs.filter(property__estate_id=estate_id)
    if property_id:
        qs = qs.filter(property_id=property_id)
    term = (search or "").strip()
    if term:
        qs = qs.filter(
            Q(property__property_name__icontains=term)
            | Q(property__estate__estate_name__icontains=term)
            | Q(client__user__email__icontains=term)
            | Q(client__user__first_name__icontains=term)
            | Q(client__user__last_name__icontains=term)
            | Q(client__company_name__icontains=term)
        )
    return qs.order_by("-created_at")


def list_client_property_purchases(*, client, status=None):
    qs = property_purchase_queryset().filter(client=client)
    if status:
        qs = qs.filter(status=status)
    return qs.order_by("-created_at")


def get_client_property_purchase(*, client, purchase_id):
    return property_purchase_queryset().get(id=purchase_id, client=client)


def payment_intents_for_purchase(purchase):
    return (
        PaymentIntent.objects.filter(
            purpose_type=PROPERTY_PURCHASE_PURPOSE_TYPE,
            purpose_id=str(purchase.id),
        )
        .select_related("confirmed_receipt")
        .prefetch_related("attempts")
        .order_by("-created_at")
    )
