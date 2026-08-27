from typing import Optional

from django.core.exceptions import ValidationError
from django.http import HttpRequest
from ninja import Router

from domains.real_estate.api.v1.schemas.purchase import (
    PropertyPurchaseCreateSchema,
    PropertyPurchasePaymentAttemptSchema,
    PropertyPurchaseSchema,
    PurchaseClientCreateSchema,
    PurchaseClientSchema,
)
from domains.real_estate.models.property_purchase import PropertyPurchase
from domains.real_estate.services.payment_intents import start_next_property_purchase_payment
from domains.real_estate.services.purchase import (
    create_property_purchase,
    create_purchase_client,
    get_active_property_purchase,
    get_property_purchase,
    search_purchase_clients,
)
from domains.real_estate.services.settlement import (
    approve_property_purchase,
    cancel_property_purchase,
    default_property_purchase,
    expire_property_purchase,
)
from system.authorization import require_permission
from system.payments.providers import PaymentProviderError
from system.payments.providers.monnify import ensure_monnify_provider_registered
from user.api.schemas.others import MessageSchema

property_purchase_api = Router(tags=["Real Estate Property Purchases"])


def _detail(error):
    if hasattr(error, "message_dict") and error.message_dict:
        first = next(iter(error.message_dict.values()))
        if first:
            return first[0]
    if getattr(error, "messages", None):
        return error.messages[0]
    return str(error)


def _payment_payload(intent, attempt):
    return {
        "intent_reference": intent.reference,
        "attempt_reference": attempt.reference,
        "provider": attempt.provider,
        "provider_reference": attempt.provider_reference,
        "amount": attempt.amount,
        "currency": attempt.currency,
        "checkout_url": attempt.checkout_url,
        "expires_at": intent.expires_at,
        "provider_metadata": attempt.provider_metadata or {},
    }


@property_purchase_api.get("/clients/search", response={200: list[PurchaseClientSchema], 400: MessageSchema})
@require_permission("clients", "list")
def search_clients(request: HttpRequest, q: str = ""):
    try:
        return 200, list(search_purchase_clients(q))
    except Exception as error:
        return 400, {"detail": str(error)}


@property_purchase_api.post("/clients", response={201: PurchaseClientSchema, 400: MessageSchema})
@require_permission("clients", "create")
def create_client(request: HttpRequest, payload: PurchaseClientCreateSchema):
    try:
        return 201, create_purchase_client(
            email=str(payload.email),
            first_name=payload.first_name,
            last_name=payload.last_name,
            phone_number=payload.phone_number,
            company_name=payload.company_name,
            send_portal_invite=payload.send_portal_invite,
        )
    except ValidationError as error:
        return 400, {"detail": _detail(error)}
    except Exception as error:
        return 400, {"detail": str(error)}


@property_purchase_api.post("/", response={201: PropertyPurchaseSchema, 400: MessageSchema})
@require_permission("properties", "update")
def create_purchase(request: HttpRequest, payload: PropertyPurchaseCreateSchema):
    try:
        purchase = create_property_purchase(
            property_id=payload.property_id,
            client_id=payload.client_id,
            mode=payload.mode,
            agreed_price=payload.agreed_price,
            installment_months=payload.installment_months,
            created_by=request.user,
        )
        return 201, get_property_purchase(purchase.id)
    except ValidationError as error:
        return 400, {"detail": _detail(error)}


@property_purchase_api.get(
    "/property/{property_id}/active",
    response={200: PropertyPurchaseSchema, 404: MessageSchema},
)
@require_permission("properties", "view")
def active_purchase(request: HttpRequest, property_id: int):
    purchase = get_active_property_purchase(property_id)
    if purchase is None:
        return 404, {"detail": "No active purchase for this property."}
    return 200, purchase


@property_purchase_api.get(
    "/property/{property_id}/current",
    response={200: Optional[PropertyPurchaseSchema]},
)
@require_permission("properties", "view")
def current_purchase(request: HttpRequest, property_id: int):
    return 200, get_active_property_purchase(property_id)


@property_purchase_api.post(
    "/{purchase_id}/approve",
    response={200: PropertyPurchaseSchema, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("properties", "update")
def approve_purchase(request: HttpRequest, purchase_id: int):
    try:
        return 200, approve_property_purchase(
            purchase_id=purchase_id, approved_by=request.user
        )
    except PropertyPurchase.DoesNotExist:
        return 404, {"detail": "Property purchase not found."}
    except ValidationError as error:
        return 400, {"detail": _detail(error)}


@property_purchase_api.post(
    "/{purchase_id}/payment-request",
    response={
        200: PropertyPurchasePaymentAttemptSchema,
        201: PropertyPurchasePaymentAttemptSchema,
        400: MessageSchema,
        404: MessageSchema,
        503: MessageSchema,
    },
)
@require_permission("properties", "update")
def payment_request(request: HttpRequest, purchase_id: int):
    try:
        ensure_monnify_provider_registered()
        intent, attempt, created = start_next_property_purchase_payment(
            purchase_id=purchase_id,
            provider_name="monnify",
            created_by=request.user,
        )
        return (201 if created else 200), _payment_payload(intent, attempt)
    except PropertyPurchase.DoesNotExist:
        return 404, {"detail": "Property purchase not found."}
    except ValidationError as error:
        return 400, {"detail": _detail(error)}
    except PaymentProviderError as error:
        return 503, {"detail": str(error)}


def _status_action(operation, purchase_id):
    try:
        return 200, operation()
    except PropertyPurchase.DoesNotExist:
        return 404, {"detail": "Property purchase not found."}
    except ValidationError as error:
        return 400, {"detail": _detail(error)}


@property_purchase_api.post(
    "/{purchase_id}/cancel",
    response={200: PropertyPurchaseSchema, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("properties", "update")
def cancel_purchase(request: HttpRequest, purchase_id: int):
    return _status_action(
        lambda: cancel_property_purchase(
            purchase_id=purchase_id, cancelled_by=request.user
        ),
        purchase_id,
    )


@property_purchase_api.post(
    "/{purchase_id}/expire",
    response={200: PropertyPurchaseSchema, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("properties", "update")
def expire_purchase(request: HttpRequest, purchase_id: int):
    return _status_action(
        lambda: expire_property_purchase(purchase_id=purchase_id),
        purchase_id,
    )


@property_purchase_api.post(
    "/{purchase_id}/default",
    response={200: PropertyPurchaseSchema, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("properties", "update")
def default_purchase(request: HttpRequest, purchase_id: int):
    return _status_action(
        lambda: default_property_purchase(purchase_id=purchase_id),
        purchase_id,
    )


@property_purchase_api.get(
    "/{purchase_id}",
    response={200: PropertyPurchaseSchema, 404: MessageSchema},
)
@require_permission("properties", "view")
def purchase_detail(request: HttpRequest, purchase_id: int):
    try:
        return 200, get_property_purchase(purchase_id)
    except PropertyPurchase.DoesNotExist:
        return 404, {"detail": "Property purchase not found."}
