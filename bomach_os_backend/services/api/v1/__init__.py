# Compatibility exports for legacy Services API imports.
from domains.marketing_sales.api.v1 import (
    csrc_router,
    funnel_router,
    marketing_router,
    pipeline_router,
)

__all__ = ["funnel_router", "marketing_router", "csrc_router", "pipeline_router"]
