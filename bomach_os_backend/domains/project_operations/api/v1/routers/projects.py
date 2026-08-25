from typing import List

from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from ninja import Router
from ninja.pagination import LimitOffsetPagination, paginate

from domains.project_operations import selectors, services
from domains.project_operations.models import Project
from user.utils.perm import require_permission

from ..schemas.schemas import (
    MessageSchema,
    PaginatedEmployeeResponse,
    ProjectCreateSchema,
    ProjectOutSchema,
    ProjectUpdateSchema,
)

router = Router(tags=["Projects"])


@router.get(
    "",
    response=List[ProjectOutSchema],
    operation_id="operations_api_v1_projects_list_projects",
)
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("projects", "list")
def list_projects(
    request,
    status: str = None,
    priority: str = None,
    client_id: int = None,
    search: str = None,
):
    return list(
        selectors.list_projects(
            status=status,
            priority=priority,
            client_id=client_id,
            search=search,
        )
    )


@router.get(
    "/{project_id}",
    response=ProjectOutSchema,
    operation_id="operations_api_v1_projects_get_project",
)
@require_permission("projects", "view")
def get_project(request, project_id: int):
    return get_object_or_404(Project, id=project_id)


@router.post(
    "",
    response={200: ProjectOutSchema, 400: MessageSchema},
    operation_id="operations_api_v1_projects_create_project",
)
@require_permission("projects", "create")
def create_project(request, payload: ProjectCreateSchema):
    try:
        return services.create_project(data=payload.dict())
    except ValidationError as exc:
        return 400, {"detail": exc.messages[0]}


@router.put(
    "/{project_id}",
    response={200: ProjectOutSchema, 400: MessageSchema},
    operation_id="operations_api_v1_projects_update_project",
)
@require_permission("projects", "update")
def update_project(request, project_id: int, payload: ProjectUpdateSchema):
    try:
        project = get_object_or_404(Project, id=project_id)
        return services.update_project(
            project=project,
            data=payload.dict(exclude_unset=True),
        )
    except ValidationError as exc:
        return 400, {"detail": exc.messages[0]}


@router.delete(
    "/{project_id}", operation_id="operations_api_v1_projects_delete_project"
)
@require_permission("projects", "delete")
def delete_project(request, project_id: int):
    project = get_object_or_404(Project, id=project_id)
    project.delete()
    return {"detail": "Project deleted successfully"}


@router.get("/stats/", operation_id="operations_api_v1_projects_stats_project")
@require_permission("projects", "view")
def stats_project(request):
    projects = Project.objects.all()
    return {"detail": "Project deleted successfully"}


@router.get(
    "/{project_id}/employees",
    response=PaginatedEmployeeResponse,
    operation_id="operations_api_v1_projects_list_project_employees",
)
@require_permission("projects", "view")
def list_project_employees(request, project_id: int, limit: int = 10, offset: int = 0):
    project = get_object_or_404(Project, id=project_id)
    total = project.employees.count()
    employees = project.employees.all()[offset : offset + limit]

    if not employees:
        return {"items": [], "count": total}

    try:
        items = [
            {
                "id": str(employee.pk),
                "employee_id": getattr(employee, "employee_id", str(employee.pk)),
                "full_name": getattr(employee, "full_name", ""),
                "email": getattr(employee, "email", ""),
                "is_active": getattr(employee, "is_active", True),
                "position": getattr(employee, "position", ""),
            }
            for employee in employees
        ]
        return {"items": items, "count": total}
    except Exception:
        return {"items": [], "count": total}


# --------------------------------------------------------------------------
# Project dashboard / overview
# --------------------------------------------------------------------------

from ninja import Router

from domains.project_operations import selectors
from user.utils.perm import require_permission

from ..schemas.schemas import DashboardStatsSchema

dashboard_router = Router(tags=["Dashboard"])


@dashboard_router.get(
    "/stats",
    response=DashboardStatsSchema,
    operation_id="operations_api_v1_dashboard_get_dashboard_stats",
)
@require_permission("dashboard", "view")
def get_dashboard_stats(request):
    return selectors.get_dashboard_stats()
