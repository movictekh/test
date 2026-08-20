from ninja import Router
from typing import List
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.core.exceptions import ValidationError

from operations.models import Worksite, Project
from ..schema.schemas import (
    WorksiteCreateSchema,
    WorksiteUpdateSchema,
    WorksiteOutSchema,
    MessageSchema,
)
from ninja.pagination import paginate, LimitOffsetPagination
from user.utils.perm import require_permission

router = Router(tags=["Worksites"])


@router.get("", response=List[WorksiteOutSchema])
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("worksites", "list")
def list_worksites(
    request,
    project_id: int = None,
    status: str = None,
    search: str = None,
):
    """List all worksites with optional filters"""
    worksites = Worksite.objects.all()

    if project_id:
        worksites = worksites.filter(project_id=project_id)
    if status:
        worksites = worksites.filter(status=status)
    if search:
        worksites = worksites.filter(
            Q(name__icontains=search) | Q(location__icontains=search)
        )

    return list(worksites)


@router.get("/{worksite_id}", response=WorksiteOutSchema)
@require_permission("worksites", "view")
def get_worksite(request, worksite_id: int):
    """Get a specific worksite by ID"""
    worksite = get_object_or_404(Worksite, id=worksite_id)
    return worksite


@router.post("", response={200: WorksiteOutSchema, 400: MessageSchema})
@require_permission("worksites", "create")
def create_worksite(request, payload: WorksiteCreateSchema):
    """Create a new worksite"""
    try:
        worksite_data = payload.dict()
        project = get_object_or_404(Project, id=worksite_data.pop("project_id"))
        worksite = Worksite.objects.create(project=project, **worksite_data)
        return worksite
    except ValidationError as e:
        return 400, {"detail": e.messages[0]}


@router.put("/{worksite_id}", response={200: WorksiteOutSchema, 400: MessageSchema})
@require_permission("worksites", "update")
def update_worksite(request, worksite_id: int, payload: WorksiteUpdateSchema):
    """Update an existing worksite"""
    try:
        worksite = get_object_or_404(Worksite, id=worksite_id)

        update_data = payload.dict(exclude_unset=True)
        if "project_id" in update_data:
            project = get_object_or_404(Project, id=update_data.pop("project_id"))
            worksite.project = project

        for attr, value in update_data.items():
            setattr(worksite, attr, value)

        worksite.save()
        return worksite
    except ValidationError as e:
        return 400, {"detail": e.messages[0]}


@router.delete("/{worksite_id}")
@require_permission("worksites", "delete")
def delete_worksite(request, worksite_id: int):
    """Delete a worksite"""
    worksite = get_object_or_404(Worksite, id=worksite_id)
    worksite.delete()
    return {"detail": "Worksite deleted successfully"}
