from ninja import Router

from services.api.schema.schemas import ServiceStatsOut
from services.models.payment import Invoice
from services.models.service import Quote, Service, ServiceOrder
from user.utils.perm import require_permission

router = Router()


@router.get("", response=ServiceStatsOut, tags=["Statistics"])
@require_permission("stats", "view")
def get_stats(request):
    return {
        "total_services": Service.objects.count(),
        "total_orders": ServiceOrder.objects.count(),
        "total_quotes": Quote.objects.count(),
        "total_invoices": Invoice.objects.count(),
    }
