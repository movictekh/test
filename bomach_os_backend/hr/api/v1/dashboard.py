import logging

from ninja import Router

from hr.api.schemas.dashboard import HRDashboardStats, HRStats, MessageSchema
from hr.models import JobPosting, LeaveRequest
from hr.models.disciplinary_case import DisciplinaryCase
from hr.models.training_program import TrainingProgram
from user.models import Employee
from system.authorization import require_permission

logger = logging.getLogger(__name__)

router = Router(tags=["Dashboard"])


@router.get("/overview", response={200: HRDashboardStats, 400: MessageSchema})
def get_dashboard_overview(request):
    try:
        from datetime import timedelta

        from django.db.models import Count
        from django.utils import timezone

        now = timezone.now()
        total_employees = Employee.objects.filter(is_active=True).count()
        new_hires_30_days = Employee.objects.filter(
            created_at__gte=now - timedelta(days=30)
        ).count()
        new_hires_today = Employee.objects.filter(created_at__date=now.date()).count()

        headcount_qs = (
            Employee.objects.filter(is_active=True)
            .values("department__name")
            .annotate(count=Count("id"))
            .order_by("-count")
        )
        headcount_by_department = [
            {
                "department": item["department__name"] or "Unassigned",
                "count": item["count"],
            }
            for item in headcount_qs
        ]
    except Exception as e:
        logger.error(f"Failed to fetch employee stats: {e}")
        return 400, {"detail": "Unable to retrieve employee statistics at this time."}

    try:
        open_roles = JobPosting.objects.filter(status=JobPosting.Status.ACTIVE).count()
    except Exception:
        open_roles = 0

    return 200, {
        "total_employees": total_employees,
        "new_hires_30_days": new_hires_30_days,
        "new_hires_today": new_hires_today,
        "open_roles": open_roles,
        "headcount_by_department": headcount_by_department,
    }


@router.get("/stats", response={200: HRStats, 400: MessageSchema})
def get_dashboard_stats(request):

    return {
        "training_programs": TrainingProgram.objects.count(),
        "job_postings": JobPosting.objects.count(),
        "leaves": LeaveRequest.objects.count(),
        "disciplinary_process": DisciplinaryCase.objects.count(),
    }
