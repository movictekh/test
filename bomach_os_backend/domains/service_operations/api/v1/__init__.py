"""Version 1 of the Service Operations HTTP contract."""

from .routers.catalogue import router as catalogue_router

__all__ = ["catalogue_router", "service_requests_router", "quotes_router", "orders_router", "invoices_router"]
from .routers.service_requests import router as service_requests_router
from .routers.quotes import router as quotes_router
from .routers.orders import router as orders_router
from .routers.invoices import router as invoices_router
