"""Public Marketing & Sales API v1 router exports."""

from .routers.campaigns import campaigns_router
from .routers.content import content_router
from .routers.marketing import marketing_router
from .routers.revenue_execution import revenue_execution_router
from .routers.sales import csrc_router, funnel_router, leads_router, pipeline_router

__all__ = [
    "leads_router",
    "funnel_router",
    "pipeline_router",
    "csrc_router",
    "marketing_router",
    "campaigns_router",
    "content_router",
    "revenue_execution_router",
]
