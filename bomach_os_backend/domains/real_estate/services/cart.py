from domains.real_estate.models.cart import Cart, CartItem
from domains.real_estate.models.estate import Property


def get_or_create_cart(user):
    cart, _ = Cart.objects.get_or_create(user=user)
    return cart


def add_property_to_cart(user, property_id):
    prop = Property.objects.select_related("estate").get(
        id=property_id,
        is_active=True,
    )
    if prop.status == "sold":
        return None
    cart = get_or_create_cart(user)
    item = CartItem.objects.create(cart=cart, property=prop, price=prop.price)
    return (
        CartItem.objects.select_related("property", "property__estate")
        .prefetch_related("property__images")
        .get(id=item.id)
    )


def remove_cart_item(user, item_id):
    cart = get_or_create_cart(user)
    item = CartItem.objects.get(id=item_id, cart=cart)
    item.delete()


def remove_property_from_cart(user, property_id):
    cart = get_or_create_cart(user)
    item = CartItem.objects.get(cart=cart, property_id=property_id)
    item.delete()


def clear_cart(user):
    cart = get_or_create_cart(user)
    count = cart.items.count()
    cart.items.all().delete()
    return count
