from ninja import Router
from typing import List
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.core.exceptions import ValidationError

from domains.project_operations.models import Project
from ..schemas.schemas import ProjectCreateSchema, ProjectUpdateSchema, ProjectOutSchema, MessageSchema, PaginatedEmployeeResponse
from ninja.pagination import paginate, LimitOffsetPagination
from user.utils.perm import require_permission

router = Router(tags=["Projects"])


@router.get("", response=List[ProjectOutSchema], operation_id="operations_api_v1_projects_list_projects")
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("projects", "list")
def list_projects(
    request,
    status: str = None,
    priority: str = None,
    client_id: int = None,
    search: str = None,
):
    """List all projects with optional filters"""
    projects = Project.objects.all()

    if status:
        projects = projects.filter(status=status)
    if priority:
        projects = projects.filter(priority=priority)
    if client_id:
        projects = projects.filter(client_id=client_id)
    if search:
        projects = projects.filter(
            Q(name__icontains=search) |
            Q(short_code__icontains=search) |
            Q(category__icontains=search)
        )

    return list(projects)


@router.get("/{project_id}", response=ProjectOutSchema, operation_id="operations_api_v1_projects_get_project")
@require_permission("projects", "view")
def get_project(request, project_id: int):
    """Get a specific project by ID"""
    project = get_object_or_404(Project, id=project_id)
    return project


@router.post("", response={200: ProjectOutSchema, 400: MessageSchema}, operation_id="operations_api_v1_projects_create_project")
@require_permission("projects", "create")
def create_project(request, payload: ProjectCreateSchema):
    """Create a new project"""
    try:
        data = payload.dict()
        employee_ids = data.pop('employee_ids', [])
        project = Project.objects.create(**data)
        if employee_ids:
            project.employees.set(employee_ids)
        return project
    except ValidationError as e:
        return 400, {'detail': e.messages[0]}


@router.put("/{project_id}", response={200: ProjectOutSchema, 400: MessageSchema}, operation_id="operations_api_v1_projects_update_project")
@require_permission("projects", "update")
def update_project(request, project_id: int, payload: ProjectUpdateSchema):
    """Update an existing project"""
    try:
        project = get_object_or_404(Project, id=project_id)

        update_data = payload.dict(exclude_unset=True)
        employee_ids = update_data.pop('employee_ids', None)

        for attr, value in update_data.items():
            setattr(project, attr, value)

        project.save()

        if employee_ids is not None:
            project.employees.set(employee_ids)

        return project
    except ValidationError as e:
        return 400, {'detail': e.messages[0]}


@router.delete("/{project_id}", operation_id="operations_api_v1_projects_delete_project")
@require_permission("projects", "delete")
def delete_project(request, project_id: int):
    """Delete a project"""
    project = get_object_or_404(Project, id=project_id)
    project.delete()
    return {"detail": "Project deleted successfully"}


@router.get("/stats/", operation_id="operations_api_v1_projects_stats_project")
@require_permission("projects", "view")
def stats_project(request):
    """Delete a project"""
    projects = Project.objects.all()
    return {"detail": "Project deleted successfully"}


@router.get("/{project_id}/employees", response=PaginatedEmployeeResponse, operation_id="operations_api_v1_projects_list_project_employees")
@require_permission("projects", "view")
def list_project_employees(request, project_id: int, limit: int = 10, offset: int = 0):
    """List employees assigned to a project with pagination"""
    project = get_object_or_404(Project, id=project_id)
    total = project.employees.count()

    employees = project.employees.all()[offset:offset + limit]

    if not employees:
        return {"items": [], "count": total}

    try:
        items = [
            {
                'id': str(e.pk),
                'employee_id': getattr(e, 'employee_id', str(e.pk)),
                'full_name': getattr(e, 'full_name', ''),
                'email': getattr(e, 'email', ''),
                'is_active': getattr(e, 'is_active', True),
                'position': getattr(e, 'position', ''),
            }
            for e in employees
        ]
        return {"items": items, "count": total}
    except Exception:
        return {"items": [], "count": total}
