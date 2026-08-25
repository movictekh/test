from typing import List

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from ninja import Router
from ninja.pagination import LimitOffsetPagination, paginate

from user.api.schemas.auth import ErrorResponse
from domains.real_estate.api.v1.schemas.cart import CartItemCreateSchema, CartItemSchema, CartSchema
from shared.api.schema.others import MessageSchema
from domains.real_estate.models.cart import Cart, CartItem
from domains.real_estate.models.estate import Property
from domains.real_estate.services.cart import (
    add_property_to_cart,
    clear_cart as clear_cart_records,
    get_or_create_cart,
    remove_cart_item,
    remove_property_from_cart as remove_property_cart_item,
)

cart_api = Router(tags=["Cart"])




@cart_api.get("/", response={200: List[CartItemSchema], 400: ErrorResponse})
@paginate(LimitOffsetPagination, page_size=10)
def get_cart(request):
    cart = get_or_create_cart(request.user)
    return cart.items.all()


@cart_api.post(
    "/items", response={201: CartItemSchema, 400: MessageSchema, 404: MessageSchema}
)
def add_to_cart(request, payload: CartItemCreateSchema):
    try:
        item = add_property_to_cart(request.user, payload.property_id)
    except Property.DoesNotExist:
        return 404, {"detail": "Property not found"}
    except IntegrityError:
        return 400, {"detail": "This property is already in your cart."}
    except ValidationError as e:
        return 400, {"detail": e.messages[0] if hasattr(e, "messages") else str(e)}

    if item is None:
        return 400, {"detail": "This property has already been sold."}
    return 201, item


@cart_api.delete("/items/{item_id}", response={200: MessageSchema, 404: MessageSchema})
def remove_from_cart(request, item_id: int):
    try:
        remove_cart_item(request.user, item_id)
        return 200, {"detail": "Item removed from cart."}
    except CartItem.DoesNotExist:
        return 404, {"detail": "Cart item not found."}


@cart_api.delete(
    "/items/property/{property_id}", response={200: MessageSchema, 404: MessageSchema}
)
def remove_property_from_cart(request, property_id: int):
    try:
        remove_property_cart_item(request.user, property_id)
        return 200, {"detail": "Property removed from cart."}
    except CartItem.DoesNotExist:
        return 404, {"detail": "Property not found in cart."}


@cart_api.delete("/clear", response=MessageSchema)
def clear_cart(request):
    count = clear_cart_records(request.user)
    return {"detail": f"Cart cleared. {count} item(s) removed."}


@cart_api.get("/count", response={200: dict})
def get_cart_count(request):
    cart = get_or_create_cart(request.user)
    return 200, {
        "total_items": cart.total_items,
        "total_price": str(cart.total_price),
    }
