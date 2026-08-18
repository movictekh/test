"""Compatibility router for the legacy ``/stats`` endpoint.

Service statistics are owned by Service Operations reporting.
This module preserves the existing HTTP path while delegating execution
to the domain-owned handler.
"""

from ninja import Router

from domains.service_operations.api.v1.routers.reports import (
    get_stats as _domain_get_stats,
)
from domains.service_operations.api.v1.schemas.reports import ServiceStatsOut

router = Router()


@router.get("", response=ServiceStatsOut, tags=["Statistics"])
def get_stats(request):
    return _domain_get_stats(request)
