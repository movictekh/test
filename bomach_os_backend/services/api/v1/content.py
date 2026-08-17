"""Compatibility import for Marketing & Sales content API."""

from domains.marketing_sales.api.v1.routers.content import content_router as router

__all__ = ["router"]
