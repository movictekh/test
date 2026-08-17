"""Version 1 of the Service Operations HTTP contract."""

from .routers.catalogue import (
    categories_router,
)
from .routers.catalogue import router as catalogue_router
from .routers.catalogue_configuration import (
    branch_activation_router as service_branch_activation_router,
)
from .routers.catalogue_configuration import (
    configuration_router as service_configuration_router,
)
from .routers.client_service_portal import router as client_service_portal_router
from .routers.feedback import router as feedback_router
from .routers.invoices import router as invoices_router
from .routers.orders import router as orders_router
from .routers.quotes import router as quotes_router
from .routers.reports import router as reports_router
from .routers.service_leads import router as service_leads_router
from .routers.service_requests import admin_router as service_request_admin_router
from .routers.service_requests import router as service_requests_router

__all__ = [
    "catalogue_router",
    "service_requests_router",
    "quotes_router",
    "orders_router",
    "invoices_router",
    "feedback_router",
    "reports_router",
    "categories_router",
    "service_leads_router",
    "service_request_admin_router",
    "client_service_portal_router",
    "service_configuration_router",
    "service_branch_activation_router",
]
