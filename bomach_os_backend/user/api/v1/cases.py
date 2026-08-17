from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from django.db.models import Count, Q, Sum
from django.http import HttpRequest
from ninja import Router
from ninja.pagination import LimitOffsetPagination, paginate

from user.api.schemas.auth import ErrorResponse
from user.api.schemas.cases import (
    CreateLegalCaseRequest,
    LegalCaseResponse,
    LegalCaseStatisticsResponse,
    UpdateCaseStatusRequest,
    UpdateLegalCaseRequest,
)
from user.api.schemas.others import MessageSchema
from user.models.cases import LegalCase
from user.utils.auth import JWTAuthenticator
from user.utils.perm import require_permission

cases_api = Router(tags=["Legal Case Management"])


@cases_api.get(
    "/",
    response={200: List[LegalCaseResponse], 400: ErrorResponse},
    auth=JWTAuthenticator(),
)
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("legal_cases", "list")
def list_legal_cases(
    request: HttpRequest,
    case_type: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    has_upcoming_hearing: Optional[bool] = None,
):
    try:
        cases = LegalCase.objects.all()

        if case_type:
            cases = cases.filter(case_type=case_type)

        if status:
            cases = cases.filter(status=status)

        if search:
            cases = cases.filter(
                Q(case_name__icontains=search)
                | Q(case_number__icontains=search)
                | Q(description__icontains=search)
            )

        if start_date:
            cases = cases.filter(
                date_filed__gte=datetime.fromisoformat(start_date).date()
            )

        if end_date:
            cases = cases.filter(
                date_filed__lte=datetime.fromisoformat(end_date).date()
            )

        if has_upcoming_hearing is not None:
            if has_upcoming_hearing:
                today = date.today()
                cases = cases.filter(next_hearing__gte=today)
            else:
                cases = cases.filter(
                    Q(next_hearing__isnull=True) | Q(next_hearing__lt=date.today())
                )

        return cases
    except Exception as e:
        return 400, {"detail": str(e)}


@cases_api.post(
    "/", response={201: LegalCaseResponse, 400: ErrorResponse}, auth=JWTAuthenticator()
)
@require_permission("legal_cases", "create")
def create_legal_case(request: HttpRequest, payload: CreateLegalCaseRequest):
    try:
        # Validate case type
        valid_case_types = [
            "contract_dispute",
            "employment",
            "regulatory",
            "civil",
            "criminal",
            "corporate",
            "intellectual_property",
        ]
        if payload.case_type not in valid_case_types:
            return 400, {
                "detail": f"Invalid case type. Must be one of: {', '.join(valid_case_types)}"
            }

        # Validate status
        valid_statuses = [
            "in_progress",
            "settled",
            "open",
            "closed",
            "pending",
            "dismissed",
            "won",
            "lost",
        ]
        if payload.status and payload.status not in valid_statuses:
            return 400, {
                "detail": f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
            }

        # Validate exposure is non-negative
        if payload.exposure is not None and payload.exposure < 0:
            return 400, {"detail": "Exposure amount cannot be negative"}

        # Create legal case
        case = LegalCase.objects.create(
            case_name=payload.case_name,
            case_type=payload.case_type,
            status=payload.status or "open",
            exposure=payload.exposure,
            next_hearing=payload.next_hearing,
            case_number=payload.case_number,
            description=payload.description or "",
            date_filed=payload.date_filed,
            date_closed=payload.date_closed,
        )

        return 201, case
    except Exception as e:
        return 400, {"detail": str(e)}


@cases_api.get(
    "/statistics/overview/",
    response={200: LegalCaseStatisticsResponse, 400: ErrorResponse},
    auth=JWTAuthenticator(),
)
def get_case_statistics(request: HttpRequest):
    try:
        total_cases = LegalCase.objects.count()

        # Count by status
        status_counts = LegalCase.objects.values("status").annotate(count=Count("id"))
        status_dict = {item["status"]: item["count"] for item in status_counts}

        # Calculate total exposure
        total_exposure = LegalCase.objects.aggregate(total=Sum("exposure"))[
            "total"
        ] or Decimal("0.00")

        # Count upcoming hearings
        today = date.today()
        upcoming_hearings = LegalCase.objects.filter(next_hearing__gte=today).count()

        # Count by case type
        case_type_counts = LegalCase.objects.values("case_type").annotate(
            count=Count("id")
        )
        cases_by_type = {item["case_type"]: item["count"] for item in case_type_counts}

        return 200, {
            "total_cases": total_cases,
            "open_cases": status_dict.get("open", 0),
            "in_progress_cases": status_dict.get("in_progress", 0),
            "settled_cases": status_dict.get("settled", 0),
            "closed_cases": status_dict.get("closed", 0),
            "won_cases": status_dict.get("won", 0),
            "lost_cases": status_dict.get("lost", 0),
            "dismissed_cases": status_dict.get("dismissed", 0),
            "pending_cases": status_dict.get("pending", 0),
            "total_exposure": total_exposure,
            "upcoming_hearings": upcoming_hearings,
            "cases_by_type": cases_by_type,
        }
    except Exception as e:
        return 400, {"detail": str(e)}


@cases_api.get(
    "/upcoming-hearings/",
    response={200: List[LegalCaseResponse], 400: ErrorResponse},
    auth=JWTAuthenticator(),
)
def get_upcoming_hearings(request: HttpRequest, days: int = 30):
    try:
        from datetime import timedelta

        today = date.today()
        end_date = today + timedelta(days=days)

        cases = LegalCase.objects.filter(
            next_hearing__gte=today, next_hearing__lte=end_date
        ).order_by("next_hearing")

        return list(cases)
    except Exception as e:
        return 400, {"detail": str(e)}


# Parameterized routes MUST come after specific string routes
@cases_api.get(
    "/{case_id}/",
    response={200: LegalCaseResponse, 404: ErrorResponse},
    auth=JWTAuthenticator(),
)
@require_permission("legal_cases", "view")
def get_legal_case(request: HttpRequest, case_id: int):
    try:
        case = LegalCase.objects.get(id=case_id)
        return case
    except LegalCase.DoesNotExist:
        return 404, {"detail": "Legal case not found"}


@cases_api.put(
    "/{case_id}/",
    response={200: LegalCaseResponse, 400: ErrorResponse, 404: ErrorResponse},
    auth=JWTAuthenticator(),
)
@require_permission("legal_cases", "update")
def update_legal_case(
    request: HttpRequest, case_id: int, payload: UpdateLegalCaseRequest
):
    try:
        case = LegalCase.objects.get(id=case_id)

        # Validate case type if provided
        if payload.case_type:
            valid_case_types = [
                "contract_dispute",
                "employment",
                "regulatory",
                "civil",
                "criminal",
                "corporate",
                "intellectual_property",
            ]
            if payload.case_type not in valid_case_types:
                return 400, {
                    "detail": f"Invalid case type. Must be one of: {', '.join(valid_case_types)}"
                }

        # Validate status if provided
        if payload.status:
            valid_statuses = [
                "in_progress",
                "settled",
                "open",
                "closed",
                "pending",
                "dismissed",
                "won",
                "lost",
            ]
            if payload.status not in valid_statuses:
                return 400, {
                    "detail": f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
                }

        # Validate exposure if provided
        if payload.exposure is not None and payload.exposure < 0:
            return 400, {"detail": "Exposure amount cannot be negative"}

        # Update fields
        for field, value in payload.dict(exclude_unset=True).items():
            if hasattr(case, field) and value is not None:
                setattr(case, field, value)

        case.save()

        return case
    except LegalCase.DoesNotExist:
        return 404, {"detail": "Legal case not found"}
    except Exception as e:
        return 400, {"detail": str(e)}


@cases_api.patch(
    "/{case_id}/status/",
    response={200: LegalCaseResponse, 400: ErrorResponse, 404: ErrorResponse},
    auth=JWTAuthenticator(),
)
@require_permission("legal_cases", "update_status")
def update_case_status(
    request: HttpRequest, case_id: int, payload: UpdateCaseStatusRequest
):
    try:
        case = LegalCase.objects.get(id=case_id)

        # Validate status
        valid_statuses = [
            "in_progress",
            "settled",
            "open",
            "closed",
            "pending",
            "dismissed",
            "won",
            "lost",
        ]
        if payload.status not in valid_statuses:
            return 400, {
                "detail": f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
            }

        case.status = payload.status
        case.save()

        return case
    except LegalCase.DoesNotExist:
        return 404, {"detail": "Legal case not found"}
    except Exception as e:
        return 400, {"detail": str(e)}


@cases_api.delete(
    "/{case_id}/",
    response={200: MessageSchema, 404: ErrorResponse},
    auth=JWTAuthenticator(),
)
@require_permission("legal_cases", "delete")
def delete_legal_case(request: HttpRequest, case_id: int):
    try:
        case = LegalCase.objects.get(id=case_id)
        case.delete()
        return 200, {"detail": "Legal case deleted successfully"}
    except LegalCase.DoesNotExist:
        return 404, {"detail": "Legal case not found"}
