"""Version 1 of the Service Operations HTTP contract."""

from .routers.catalogue import router as catalogue_router

__all__ = ["catalogue_router"]
