from datetime import timedelta

from django.utils import timezone
from ninja import Router

from user.api.schemas.others import DashboardStatsSchema
from user.models.approval import ApprovalRequest
from user.models.branch import Branch
from user.models.client_inventory import CLientInventoryItem
from user.models.employee import Employee

stats_api = Router(tags=["Stats"])

RECENT_DAYS = 30
OVERDUE_DAYS = 7


@stats_api.get("/dashboard", response=DashboardStatsSchema)
def get_dashboard_stats(request):
    now = timezone.now()
    recent_cutoff = now - timedelta(days=RECENT_DAYS)
    overdue_cutoff = now - timedelta(days=OVERDUE_DAYS)

    total_employees = Employee.objects.count()
    new_employees_count = Employee.objects.filter(created_at__gte=recent_cutoff).count()

    total_branches = Branch.objects.count()
    removed_branches_count = Branch.objects.filter(
        is_active=False, updated_at__gte=recent_cutoff
    ).count()

    pending_approvals = ApprovalRequest.objects.filter(status="pending").count()
    overdue_tasks_count = ApprovalRequest.objects.filter(
        status="pending", created_at__lt=overdue_cutoff
    ).count()

    asset_inventory = CLientInventoryItem.objects.count()
    new_inventory_count = CLientInventoryItem.objects.filter(
        created_at__gte=recent_cutoff
    ).count()

    return {
        "total_employees": total_employees,
        "new_employees_count": new_employees_count,
        "total_branches": total_branches,
        "removed_branches_count": removed_branches_count,
        "pending_approvals": pending_approvals,
        "overdue_tasks_count": overdue_tasks_count,
        "asset_inventory": asset_inventory,
        "new_inventory_count": new_inventory_count,
    }
