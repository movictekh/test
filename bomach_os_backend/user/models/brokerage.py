"""Django compatibility exports for Real Estate brokerage models.

Canonical source ownership lives in ``domains.real_estate.models.brokerage``.
The Django app identity remains ``user``.
"""

from domains.real_estate.models.brokerage import (
    BrokerageListing,
    BrokerageListingImage,
)

__all__ = [
    "BrokerageListing",
    "BrokerageListingImage",
]
