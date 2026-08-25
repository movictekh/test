from typing import List, Optional

from django.core.exceptions import ValidationError
from django.db.models import Q
from django.shortcuts import get_object_or_404
from ninja import Query, Router
from ninja.pagination import LimitOffsetPagination, paginate

from domains.organization.api.v1.schemas.branch import BranchChoicesSchema, BranchCreateSchema, BranchPerformanceAnalysisSchema, BranchSchema, BranchUpdateSchema, BusinessHoursInputSchema, BusinessHoursSchema
from user.api.schemas.others import MessageSchema
from domains.organization.models.branch import Branch, BranchBusinessHours
from domains.people.models.employee import Employee
from system.identity.models.user import User
from system.authorization import require_permission

branch_api = Router(tags=["Branch"])


@branch_api.get("/branches", response=List[BranchSchema])
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("branches", "list")
def list_branches(
    request,
    country: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    operational_status: Optional[str] = Query(None),
    branch_role: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
):
    branches = Branch.objects.select_related("manager").all()

    if country:
        branches = branches.filter(country__icontains=country)

    if state:
        branches = branches.filter(state__icontains=state)

    if operational_status:
        branches = branches.filter(operational_status=operational_status)

    if branch_role:
        branches = branches.filter(branch_role=branch_role)

    if is_active is not None:
        branches = branches.filter(is_active=is_active)

    if search:
        branches = branches.filter(
            Q(branch_name__icontains=search)
            | Q(branch_id__icontains=search)
            | Q(office_address__icontains=search)
            | Q(lga__icontains=search)
            | Q(city__icontains=search)
            | Q(state__icontains=search)
            | Q(country__icontains=search)
        )

    branches = branches.order_by("-created_at")

    return branches


@branch_api.get(
    "/branches/{branch_id}", response={200: BranchSchema, 404: MessageSchema}
)
@require_permission("branches", "view")
def get_branch(request, branch_id: int):
    try:
        branch = Branch.objects.select_related("manager").get(id=branch_id)
        return 200, branch
    except Branch.DoesNotExist:
        return 404, {"detail": "Branch not found"}


@branch_api.post("/branches", response={201: BranchSchema, 400: MessageSchema})
@require_permission("branches", "create")
def create_branch(request, payload: BranchCreateSchema):
    try:
        # Validate manager if provided
        manager = None
        if payload.manager_id:
            manager = get_object_or_404(User, id=payload.manager_id)

        # Create branch
        branch_data = payload.dict(
            exclude={"manager_id", "branch_file", "business_hours"}
        )
        # Remove None values to let model defaults take effect
        branch_data = {k: v for k, v in branch_data.items() if v is not None}

        branch = Branch.objects.create(
            **branch_data,
            manager=manager,
        )

        # Handle branch file if provided
        if payload.branch_file:
            # Extract path from URL if needed
            from urllib.parse import urlparse

            if payload.branch_file.startswith("http"):
                parsed = urlparse(payload.branch_file)
                file_path = parsed.path.lstrip("/")
            else:
                file_path = payload.branch_file

            branch.branch_file = file_path
            branch.full_clean()
            branch.save()

        # Handle business hours if provided
        if payload.business_hours:
            for hours in payload.business_hours:
                BranchBusinessHours.objects.create(
                    branch=branch,
                    day_of_week=hours.day_of_week,
                    open_time=hours.open_time,
                    close_time=hours.close_time,
                    is_open=hours.is_open,
                )

        return 201, branch

    except ValidationError as e:
        return 400, {"detail": e.messages[0]}
    except Exception as e:
        return 400, {"detail": str(e)}


@branch_api.put(
    "/branches/{branch_id}",
    response={200: BranchSchema, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("branches", "update")
def update_branch(request, branch_id: int, payload: BranchUpdateSchema):
    try:
        branch = Branch.objects.select_related("manager").get(id=branch_id)

        update_data = payload.dict(exclude_unset=True)

        # Handle manager update
        if "manager_id" in update_data:
            manager_id = update_data.pop("manager_id")
            if manager_id:
                from django.contrib.auth import get_user_model

                User = get_user_model()
                manager = get_object_or_404(User, id=manager_id)
                branch.manager = manager
            else:
                branch.manager = None

        # Handle branch file update
        if "branch_file" in update_data:
            branch_file = update_data.pop("branch_file")
            if branch_file:
                # Extract path from URL if needed
                from urllib.parse import urlparse

                if branch_file.startswith("http"):
                    parsed = urlparse(branch_file)
                    file_path = parsed.path.lstrip("/")
                else:
                    file_path = branch_file

                # Delete old file if exists
                if branch.branch_file:
                    branch.branch_file.delete(save=False)

                branch.branch_file = file_path
            else:
                # Remove file
                if branch.branch_file:
                    branch.branch_file.delete(save=False)
                branch.branch_file = None

        # Handle business hours update (replaces all existing hours)
        if "business_hours" in update_data:
            hours_list = update_data.pop("business_hours")
            if hours_list is not None:
                branch.business_hours.all().delete()
                for hours in hours_list:
                    BranchBusinessHours.objects.create(
                        branch=branch,
                        day_of_week=hours["day_of_week"],
                        open_time=hours.get("open_time"),
                        close_time=hours.get("close_time"),
                        is_open=hours.get("is_open", True),
                    )

        # Update other fields
        for field, value in update_data.items():
            setattr(branch, field, value)

        branch.full_clean()
        branch.save()

        # Refresh from DB to get related objects
        branch.refresh_from_db()

        return 200, branch

    except Branch.DoesNotExist:
        return 404, {"detail": "Branch not found"}
    except ValidationError as e:
        return 400, {"detail": e.messages[0]}
    except Exception as e:
        return 400, {"detail": str(e)}


@branch_api.get(
    "/branches/{branch_id}/business-hours",
    response={200: List[BusinessHoursSchema], 404: MessageSchema},
)
def get_branch_business_hours(request, branch_id: int):
    try:
        branch = Branch.objects.get(id=branch_id)
        return 200, list(branch.business_hours.all())
    except Branch.DoesNotExist:
        return 404, {"detail": "Branch not found"}


@branch_api.put(
    "/branches/{branch_id}/business-hours",
    response={200: List[BusinessHoursSchema], 400: MessageSchema, 404: MessageSchema},
)
@require_permission("branches", "update")
def set_branch_business_hours(
    request, branch_id: int, payload: List[BusinessHoursInputSchema]
):
    try:
        branch = Branch.objects.get(id=branch_id)

        branch.business_hours.all().delete()

        created = []
        for hours in payload:
            obj = BranchBusinessHours(
                branch=branch,
                day_of_week=hours.day_of_week,
                open_time=hours.open_time,
                close_time=hours.close_time,
                is_open=hours.is_open,
            )
            obj.full_clean()
            obj.save()
            created.append(obj)

        return 200, created

    except Branch.DoesNotExist:
        return 404, {"detail": "Branch not found"}
    except ValidationError as e:
        return 400, {"detail": e.messages[0]}
    except Exception as e:
        return 400, {"detail": str(e)}


@branch_api.get("/branches/choices/fields", response=BranchChoicesSchema)
def get_branch_field_choices(request):
    return {
        "operational_status": [
            {"value": choice[0], "label": choice[1]}
            for choice in Branch.OPERATIONAL_STATUS_CHOICES
        ],
        "branch_role": [
            {"value": choice[0], "label": choice[1]}
            for choice in Branch.BRANCH_ROLE_CHOICES
        ],
    }


@branch_api.get(
    "/branches/{branch_id}/performance",
    response={200: BranchPerformanceAnalysisSchema, 404: MessageSchema},
)
def get_branch_performance(request, branch_id: int):
    try:
        # Verify branch exists
        branch = Branch.objects.get(id=branch_id)

        # Return dummy data
        return 200, {
            "metrics": {
                "revenue_generated": "₦45.0M",
                "operational_efficiency": "96%",
                "customer_satisfaction": "94%",
                "total_employees": 120,
            },
            "key_insights": [
                {
                    "title": "Revenue Status",
                    "value": "113% of revenue target",
                    "status": "high",
                    "recommendation": "Maintain current performance",
                },
                {
                    "title": "Operational Efficiency",
                    "value": "Operating at 96% efficiency",
                    "status": "high",
                    "recommendation": "Continue optimizing processes",
                },
                {
                    "title": "Employee Productivity",
                    "value": "92% productivity rate",
                    "status": "high",
                    "recommendation": "Consider additional training programs",
                },
                {
                    "title": "Customer Satisfaction",
                    "value": "94% satisfaction from 156 customers",
                    "status": "high",
                    "recommendation": "Leverage customer feedback to improve service",
                },
                {
                    "title": "Staff Retention",
                    "value": "94% employee retention rate",
                    "status": "high",
                    "recommendation": "Maintain positive workplace culture",
                },
            ],
            "revenue_trend": [
                {
                    "month": "Jan",
                    "actual_revenue": 38000000,
                    "projected_revenue": 35000000,
                },
                {
                    "month": "Jan",
                    "actual_revenue": 39000000,
                    "projected_revenue": 36000000,
                },
                {
                    "month": "Jan",
                    "actual_revenue": 40500000,
                    "projected_revenue": 37000000,
                },
                {
                    "month": "Feb",
                    "actual_revenue": 40000000,
                    "projected_revenue": 37500000,
                },
                {
                    "month": "Feb",
                    "actual_revenue": 39500000,
                    "projected_revenue": 38000000,
                },
                {
                    "month": "Mar",
                    "actual_revenue": 42000000,
                    "projected_revenue": 39000000,
                },
                {
                    "month": "Mar",
                    "actual_revenue": 43500000,
                    "projected_revenue": 40000000,
                },
                {
                    "month": "Mar",
                    "actual_revenue": 44500000,
                    "projected_revenue": 41000000,
                },
                {
                    "month": "Apr",
                    "actual_revenue": 45500000,
                    "projected_revenue": 41500000,
                },
                {
                    "month": "Apr",
                    "actual_revenue": 46000000,
                    "projected_revenue": 42000000,
                },
                {
                    "month": "May",
                    "actual_revenue": 45500000,
                    "projected_revenue": 42000000,
                },
                {
                    "month": "May",
                    "actual_revenue": 44500000,
                    "projected_revenue": 41500000,
                },
            ],
            "branch_details": {
                "branch_name": branch.branch_name,
                "location": f"{branch.state}, {branch.country}",
                "status": "Excellent",
                "revenue": "₦45.0M",
                "revenue_percentage": "113%",
                "employees": 120,
                "employee_productivity": "92% productivity",
                "projects": 28,
                "active_projects": 8,
                "customer_satisfaction_percentage": "94%",
                "customer_count": 156,
            },
        }
    except Branch.DoesNotExist:
        return 404, {"detail": "Branch not found"}
