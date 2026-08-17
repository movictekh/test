"""Compatibility import for Marketing & Sales leads API."""

from domains.marketing_sales.api.v1 import leads_router as router

__all__ = ["router"]
