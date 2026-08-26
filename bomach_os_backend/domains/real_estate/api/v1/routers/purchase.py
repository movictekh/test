from django.core.exceptions import ValidationError
from django.http import HttpRequest
from ninja import Router

from domains.real_estate.api.v1.schemas.purchase import (
    PropertyPurchaseCreateSchema,
    PropertyPurchaseSchema,
    PurchaseClientCreateSchema,
    PurchaseClientSchema,
)
from domains.real_estate.models.property_purchase import PropertyPurchase
from domains.real_estate.services.purchase import (
    create_property_purchase,
    create_purchase_client,
    get_active_property_purchase,
    get_property_purchase,
    search_purchase_clients,
)
from system.authorization import require_permission
from user.api.schemas.others import MessageSchema

property_purchase_api = Router(tags=["Real Estate Property Purchases"])


def _detail(error: ValidationError):
    if hasattr(error, "message_dict") and error.message_dict:
        first = next(iter(error.message_dict.values()))
        if first:
            return first[0]
    if getattr(error, "messages", None):
        return error.messages[0]
    return str(error)


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
    except Exception as error:
        return 400, {"detail": str(error)}


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


@property_purchase_api.get("/{purchase_id}", response={200: PropertyPurchaseSchema, 404: MessageSchema})
@require_permission("properties", "view")
def purchase_detail(request: HttpRequest, purchase_id: int):
    try:
        return 200, get_property_purchase(purchase_id)
    except PropertyPurchase.DoesNotExist:
        return 404, {"detail": "Property purchase not found."}
