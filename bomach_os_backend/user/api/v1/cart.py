from ninja import Router
from typing import List

from django.core.exceptions import ValidationError
from django.db import IntegrityError

from user.api.schemas.auth import ErrorResponse
from user.api.schemas.others import MessageSchema
from user.api.schemas.cart import CartSchema, CartItemSchema, CartItemCreateSchema
from user.models.cart import Cart, CartItem
from user.models.estate import Property
from ninja.pagination import paginate, LimitOffsetPagination


cart_api = Router(tags=["Cart"])


def _get_or_create_cart(user):
    """Get the user's cart or create one if it doesn't exist"""
    cart, _ = Cart.objects.get_or_create(user=user)
    return cart


@cart_api.get("/", response={200: List[CartItemSchema], 400: ErrorResponse})
@paginate(LimitOffsetPagination, page_size=10)
def get_cart(request):
    """Get the current user's cart with all items"""
    cart = _get_or_create_cart(request.user)
    return cart.items.all()


@cart_api.post("/items", response={201: CartItemSchema, 400: MessageSchema, 404: MessageSchema})
def add_to_cart(request, payload: CartItemCreateSchema):
    """Add a property to the cart"""
    try:
        prop = Property.objects.select_related('estate').get(
            id=payload.property_id, is_active=True
        )
    except Property.DoesNotExist:
        return 404, {"detail": "Property not found"}

    if prop.status == 'sold':
        return 400, {"detail": "This property has already been sold."}

    cart = _get_or_create_cart(request.user)

    try:
        item = CartItem.objects.create(
            cart=cart,
            property=prop,
            price=prop.price,
        )
    except IntegrityError:
        return 400, {"detail": "This property is already in your cart."}
    except ValidationError as e:
        return 400, {'detail': e.messages[0] if hasattr(e, 'messages') else str(e)}

    # Reload with relations for the response
    item = CartItem.objects.select_related(
        'property', 'property__estate'
    ).prefetch_related('property__images').get(id=item.id)
    return 201, item


@cart_api.delete("/items/{item_id}", response={200: MessageSchema, 404: MessageSchema})
def remove_from_cart(request, item_id: int):
    """Remove an item from the cart"""
    cart = _get_or_create_cart(request.user)

    try:
        item = CartItem.objects.get(id=item_id, cart=cart)
        item.delete()
        return 200, {"detail": "Item removed from cart."}
    except CartItem.DoesNotExist:
        return 404, {"detail": "Cart item not found."}


@cart_api.delete("/items/property/{property_id}", response={200: MessageSchema, 404: MessageSchema})
def remove_property_from_cart(request, property_id: int):
    """Remove a property from the cart by property ID"""
    cart = _get_or_create_cart(request.user)

    try:
        item = CartItem.objects.get(cart=cart, property_id=property_id)
        item.delete()
        return 200, {"detail": "Property removed from cart."}
    except CartItem.DoesNotExist:
        return 404, {"detail": "Property not found in cart."}


@cart_api.delete("/clear", response=MessageSchema)
def clear_cart(request):
    """Remove all items from the cart"""
    cart = _get_or_create_cart(request.user)
    count = cart.items.count()
    cart.items.all().delete()
    return {"detail": f"Cart cleared. {count} item(s) removed."}


@cart_api.get("/count", response={200: dict})
def get_cart_count(request):
    """Get the number of items in the cart"""
    cart = _get_or_create_cart(request.user)
    return 200, {
        "total_items": cart.total_items,
        "total_price": str(cart.total_price),
    }
