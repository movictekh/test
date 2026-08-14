from ninja import Router

from domains.project_operations import selectors
from user.utils.perm import require_permission

from ..schemas.schemas import DashboardStatsSchema

router = Router(tags=["Dashboard"])


@router.get("/stats", response=DashboardStatsSchema, operation_id="operations_api_v1_dashboard_get_dashboard_stats")
@require_permission("dashboard", "view")
def get_dashboard_stats(request):
    return selectors.get_dashboard_stats()
