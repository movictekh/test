from ninja import Router
from django.db.models import Sum
from decimal import Decimal

from operations.models import Project, Worksite, Contract, Timeline
from ..schema.schemas import DashboardStatsSchema
from user.utils.perm import require_permission

router = Router(tags=["Dashboard"])


@router.get("/stats", response=DashboardStatsSchema)
@require_permission("dashboard", "view")
def get_dashboard_stats(request):
    """Get dashboard statistics"""
    total_projects = Project.objects.count()
    total_worksites = Worksite.objects.count()
    total_contracts = Contract.objects.count()
    total_timelines = Timeline.objects.count()

    total_budget = Project.objects.aggregate(total=Sum('budget'))['total'] or Decimal('0.00')
    budget_utilization = Project.objects.filter(status='completed').aggregate(total=Sum('budget'))['total'] or Decimal('0.00')

    return {
        "total_projects": total_projects,
        "total_budget": total_budget,
        "budget_utilization": budget_utilization,
        "total_worksites": total_worksites,
        "total_contracts": total_contracts,
        "total_timelines": total_timelines,
    }
