"""Django compatibility exports for Real Estate cart models.

Canonical source ownership lives in ``domains.real_estate.models.cart``.
The Django app identity remains ``user`` so tables, migrations, permissions,
content types, and relationships remain unchanged.
"""

from domains.real_estate.models.cart import Cart, CartItem

__all__ = ["Cart", "CartItem"]
