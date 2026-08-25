from datetime import date, datetime, timedelta
from typing import List, Optional

from django.db.models import Avg, Case, Count, IntegerField, Q, When
from django.http import HttpRequest
from ninja import Router
from ninja.pagination import LimitOffsetPagination, paginate

from domains.legal_compliance.api.v1.schemas.audit import AuditorSummaryResponse, AuditPerformanceTrendsResponse, AuditResponse, AuditStatisticsResponse, CreateAuditRequest, UpdateAuditRequest, UpdateAuditScoreRequest, UpdateAuditStatusRequest
from user.api.schemas.auth import ErrorResponse
from user.api.schemas.others import MessageSchema
from domains.legal_compliance.models.compliance_audit import Audit
from user.utils.auth import JWTAuthenticator
from system.authorization import require_permission

audit_api = Router(tags=["Audit Management (Legal)"])


@audit_api.get("/", response={200: List[AuditResponse], 400: ErrorResponse})
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("compliance_audits", "list")
def list_audits(
    request: HttpRequest,
    audit_type: Optional[str] = None,
    status: Optional[str] = None,
    auditor_name: Optional[str] = None,
    department: Optional[str] = None,
    min_score: Optional[int] = None,
    max_score: Optional[int] = None,
    search: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
):
    try:
        audits = Audit.objects.all()

        if audit_type:
            audits = audits.filter(audit_type=audit_type)

        if status:
            audits = audits.filter(status=status)

        if auditor_name:
            audits = audits.filter(auditor_name__icontains=auditor_name)

        if department:
            audits = audits.filter(department__icontains=department)

        if min_score is not None:
            audits = audits.filter(score__gte=min_score)

        if max_score is not None:
            audits = audits.filter(score__lte=max_score)

        if search:
            audits = audits.filter(
                Q(audit_name__icontains=search)
                | Q(audit_number__icontains=search)
                | Q(description__icontains=search)
                | Q(findings__icontains=search)
            )

        if start_date:
            audits = audits.filter(
                audit_date__gte=datetime.fromisoformat(start_date).date()
            )

        if end_date:
            audits = audits.filter(
                audit_date__lte=datetime.fromisoformat(end_date).date()
            )

        return audits
    except Exception as e:
        return 400, {"detail": str(e)}


@audit_api.get(
    "/statistics/overview/", response={200: AuditStatisticsResponse, 400: ErrorResponse}
)
def get_audit_statistics(request: HttpRequest):
    try:
        total_audits = Audit.objects.count()

        # Count by status
        status_counts = Audit.objects.values("status").annotate(count=Count("id"))
        status_dict = {item["status"]: item["count"] for item in status_counts}

        # Calculate average score (only for completed audits with scores)
        completed_with_scores = Audit.objects.filter(
            status="completed", score__isnull=False
        )
        average_score = completed_with_scores.aggregate(avg=Avg("score"))["avg"]

        if completed_with_scores.count() > 0:
            passed_count = completed_with_scores.filter(score__gte=70).count()
            pass_rate = (passed_count / completed_with_scores.count()) * 100
        else:
            pass_rate = None

        # Count by audit type
        audit_type_counts = Audit.objects.values("audit_type").annotate(
            count=Count("id")
        )
        audits_by_type = {
            item["audit_type"]: item["count"] for item in audit_type_counts
        }

        # Count by score category
        scored_audits = Audit.objects.filter(score__isnull=False)
        audits_by_score_category = {
            "Excellent": scored_audits.filter(score__gte=90).count(),
            "Good": scored_audits.filter(score__gte=80, score__lt=90).count(),
            "Satisfactory": scored_audits.filter(score__gte=70, score__lt=80).count(),
            "Needs Improvement": scored_audits.filter(
                score__gte=60, score__lt=70
            ).count(),
            "Poor": scored_audits.filter(score__lt=60).count(),
        }

        # Count upcoming scheduled audits
        today = date.today()
        upcoming_audits_count = Audit.objects.filter(
            status="scheduled", audit_date__gte=today
        ).count()

        return 200, {
            "total_audits": total_audits,
            "completed_audits": status_dict.get("completed", 0),
            "in_progress_audits": status_dict.get("in_progress", 0),
            "scheduled_audits": status_dict.get("scheduled", 0),
            "cancelled_audits": status_dict.get("cancelled", 0),
            "failed_audits": status_dict.get("failed", 0),
            "average_score": float(average_score) if average_score else None,
            "pass_rate": float(pass_rate) if pass_rate else None,
            "audits_by_type": audits_by_type,
            "audits_by_score_category": audits_by_score_category,
            "upcoming_audits_count": upcoming_audits_count,
        }
    except Exception as e:
        return 400, {"detail": str(e)}


@audit_api.get(
    "/statistics/performance-trends/",
    response={200: AuditPerformanceTrendsResponse, 400: ErrorResponse},
)
def get_performance_trends(
    request: HttpRequest, period: str = "month", months: int = 12
):
    try:
        from django.db.models.functions import TruncMonth, TruncQuarter, TruncYear

        # Calculate date range
        end_date = date.today()
        start_date = end_date - timedelta(days=months * 30)

        # Get completed audits in date range
        audits = Audit.objects.filter(
            status="completed", audit_date__gte=start_date, audit_date__lte=end_date
        )

        # Select truncation function based on period
        if period == "quarter":
            trunc_func = TruncQuarter
        elif period == "year":
            trunc_func = TruncYear
        else:
            trunc_func = TruncMonth

        # Group by period and calculate metrics
        trends_data = (
            audits.annotate(period_date=trunc_func("audit_date"))
            .values("period_date")
            .annotate(
                total_audits=Count("id"),
                average_score=Avg("score"),
                passed=Count(
                    Case(When(score__gte=70, then=1), output_field=IntegerField())
                ),
            )
            .order_by("period_date")
        )

        # Format trends
        trends = []
        for item in trends_data:
            pass_rate = (
                (item["passed"] / item["total_audits"] * 100)
                if item["total_audits"] > 0
                else 0
            )
            trends.append(
                {
                    "period": (
                        item["period_date"].strftime("%Y-%m-%d")
                        if item["period_date"]
                        else "N/A"
                    ),
                    "average_score": (
                        float(item["average_score"]) if item["average_score"] else 0
                    ),
                    "total_audits": item["total_audits"],
                    "pass_rate": float(pass_rate),
                }
            )

        # Calculate overall improvement (first vs last period)
        overall_improvement = None
        if len(trends) >= 2:
            first_score = trends[0]["average_score"]
            last_score = trends[-1]["average_score"]
            if first_score > 0:
                overall_improvement = ((last_score - first_score) / first_score) * 100

        return 200, {
            "period": period,
            "trends": trends,
            "overall_improvement": (
                float(overall_improvement) if overall_improvement is not None else None
            ),
        }
    except Exception as e:
        return 400, {"detail": str(e)}


@audit_api.get(
    "/failing-audits/", response={200: List[AuditResponse], 400: ErrorResponse}
)
@paginate(LimitOffsetPagination, page_size=10)
def get_failing_audits(request: HttpRequest, threshold: int = 70):
    try:
        audits = Audit.objects.filter(
            score__isnull=False, score__lt=threshold
        ).order_by("score")

        return audits
    except Exception as e:
        return 400, {"detail": str(e)}


@audit_api.get(
    "/auditors/", response={200: List[AuditorSummaryResponse], 400: ErrorResponse}
)
@paginate(LimitOffsetPagination, page_size=10)
def list_auditors(request: HttpRequest):
    try:
        # Group audits by auditor
        auditor_data = (
            Audit.objects.values("auditor_name")
            .annotate(total_audits=Count("id"), average_score=Avg("score"))
            .order_by("-total_audits")
        )

        return list(auditor_data)
    except Exception as e:
        return 400, {"detail": str(e)}


# Parameterized routes MUST come after specific string routes
@audit_api.get("/{audit_id}/", response={200: AuditResponse, 404: ErrorResponse})
@require_permission("compliance_audits", "view")
def get_audit(request: HttpRequest, audit_id: int):
    try:
        audit = Audit.objects.get(id=audit_id)
        return audit
    except Audit.DoesNotExist:
        return 404, {"detail": "Audit not found"}


@audit_api.post("/", response={201: AuditResponse, 400: ErrorResponse})
@require_permission("compliance_audits", "create")
def create_audit(request: HttpRequest, payload: CreateAuditRequest):
    try:
        # Validate audit type
        valid_audit_types = [
            "external",
            "regulatory",
            "internal",
            "customer",
            "financial",
            "operational",
            "compliance",
        ]
        if payload.audit_type not in valid_audit_types:
            return 400, {
                "detail": f"Invalid audit type. Must be one of: {', '.join(valid_audit_types)}"
            }

        # Validate status
        valid_statuses = [
            "completed",
            "in_progress",
            "scheduled",
            "draft",
            "cancelled",
            "failed",
        ]
        if payload.status and payload.status not in valid_statuses:
            return 400, {
                "detail": f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
            }

        # Validate score
        if payload.score is not None and (payload.score < 0 or payload.score > 100):
            return 400, {"detail": "Score must be between 0 and 100"}

        # Create audit
        audit = Audit.objects.create(
            audit_name=payload.audit_name,
            audit_type=payload.audit_type,
            auditor_name=payload.auditor_name,
            auditor_title=payload.auditor_title or "",
            status=payload.status or "scheduled",
            score=payload.score,
            audit_date=payload.audit_date,
            audit_number=payload.audit_number,
            description=payload.description or "",
            findings=payload.findings or "",
            recommendations=payload.recommendations or "",
            start_date=payload.start_date,
            end_date=payload.end_date,
            auditor_organization=payload.auditor_organization or "",
            department=payload.department or "",
        )

        return 201, audit
    except Exception as e:
        return 400, {"detail": str(e)}


@audit_api.put(
    "/{audit_id}/",
    response={200: AuditResponse, 400: ErrorResponse, 404: ErrorResponse},
)
@require_permission("compliance_audits", "update")
def update_audit(request: HttpRequest, audit_id: int, payload: UpdateAuditRequest):
    try:
        audit = Audit.objects.get(id=audit_id)

        # Validate audit type if provided
        if payload.audit_type:
            valid_audit_types = [
                "external",
                "regulatory",
                "internal",
                "customer",
                "financial",
                "operational",
                "compliance",
            ]
            if payload.audit_type not in valid_audit_types:
                return 400, {
                    "detail": f"Invalid audit type. Must be one of: {', '.join(valid_audit_types)}"
                }

        # Validate status if provided
        if payload.status:
            valid_statuses = [
                "completed",
                "in_progress",
                "scheduled",
                "draft",
                "cancelled",
                "failed",
            ]
            if payload.status not in valid_statuses:
                return 400, {
                    "detail": f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
                }

        # Validate score if provided
        if payload.score is not None and (payload.score < 0 or payload.score > 100):
            return 400, {"detail": "Score must be between 0 and 100"}

        # Update fields
        for field, value in payload.dict(exclude_unset=True).items():
            if hasattr(audit, field) and value is not None:
                setattr(audit, field, value)

        audit.save()

        return audit
    except Audit.DoesNotExist:
        return 404, {"detail": "Audit not found"}
    except Exception as e:
        return 400, {"detail": str(e)}


@audit_api.patch(
    "/{audit_id}/status/",
    response={200: AuditResponse, 400: ErrorResponse, 404: ErrorResponse},
)
@require_permission("compliance_audits", "update_status")
def update_audit_status(
    request: HttpRequest, audit_id: int, payload: UpdateAuditStatusRequest
):
    try:
        audit = Audit.objects.get(id=audit_id)

        # Validate status
        valid_statuses = [
            "completed",
            "in_progress",
            "scheduled",
            "draft",
            "cancelled",
            "failed",
        ]
        if payload.status not in valid_statuses:
            return 400, {
                "detail": f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
            }

        audit.status = payload.status
        audit.save()

        return audit
    except Audit.DoesNotExist:
        return 404, {"detail": "Audit not found"}
    except Exception as e:
        return 400, {"detail": str(e)}


@audit_api.patch(
    "/{audit_id}/score/",
    response={200: AuditResponse, 400: ErrorResponse, 404: ErrorResponse},
)
@require_permission("compliance_audits", "update_score")
def update_audit_score(
    request: HttpRequest, audit_id: int, payload: UpdateAuditScoreRequest
):
    try:
        audit = Audit.objects.get(id=audit_id)

        # Validate score
        if payload.score < 0 or payload.score > 100:
            return 400, {"detail": "Score must be between 0 and 100"}

        audit.score = payload.score
        audit.save()

        return audit
    except Audit.DoesNotExist:
        return 404, {"detail": "Audit not found"}
    except Exception as e:
        return 400, {"detail": str(e)}


@audit_api.delete("/{audit_id}/", response={200: MessageSchema, 404: ErrorResponse})
@require_permission("compliance_audits", "delete")
def delete_audit(request: HttpRequest, audit_id: int):
    try:
        audit = Audit.objects.get(id=audit_id)
        audit.delete()
        return 200, {"detail": "Audit deleted successfully"}
    except Audit.DoesNotExist:
        return 404, {"detail": "Audit not found"}
