"""Django compatibility exports for Real Estate estate/property models.

Canonical source ownership lives in ``domains.real_estate.models.estate``.
The Django app identity remains ``user`` so tables, migrations, permissions,
content types, and relationships remain unchanged.
"""

from domains.real_estate.models.estate import (
    Estate,
    EstateDocument,
    Property,
    PropertyImage,
)

__all__ = [
    "Estate",
    "EstateDocument",
    "Property",
    "PropertyImage",
]
