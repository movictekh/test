from ninja import Router
from typing import List
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.core.exceptions import ValidationError

from operations.models import Milestone, Project
from ..schema.schemas import MilestoneCreateSchema, MilestoneUpdateSchema, MilestoneOutSchema, MessageSchema
from ninja.pagination import paginate, LimitOffsetPagination
from user.utils.perm import require_permission

router = Router(tags=["Milestones"])


@router.get("", response=List[MilestoneOutSchema])
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("milestones", "list")
def list_milestones(
    request,
    project_id: int = None,
    status: str = None,
    priority: str = None,
    search: str = None,
):
    """List all milestones with optional filters"""
    milestones = Milestone.objects.all()

    if project_id:
        milestones = milestones.filter(project_id=project_id)
    if status:
        milestones = milestones.filter(status=status)
    if priority:
        milestones = milestones.filter(priority=priority)
    if search:
        milestones = milestones.filter(
            Q(name__icontains=search) |
            Q(description__icontains=search)
        )

    return list(milestones)


@router.get("/{milestone_id}", response=MilestoneOutSchema)
@require_permission("milestones", "view")
def get_milestone(request, milestone_id: int):
    """Get a specific milestone by ID"""
    milestone = get_object_or_404(Milestone, id=milestone_id)
    return milestone


@router.post("", response={200: MilestoneOutSchema, 400: MessageSchema})
@require_permission("milestones", "create")
def create_milestone(request, payload: MilestoneCreateSchema):
    """Create a new milestone"""
    try:
        milestone_data = payload.dict()
        project = get_object_or_404(Project, id=milestone_data.pop('project_id'))
        milestone = Milestone.objects.create(project=project, **milestone_data)
        return milestone
    except ValidationError as e:
        return 400, {'detail': e.messages[0]}


@router.put("/{milestone_id}", response={200: MilestoneOutSchema, 400: MessageSchema})
@require_permission("milestones", "update")
def update_milestone(request, milestone_id: int, payload: MilestoneUpdateSchema):
    """Update an existing milestone"""
    try:
        milestone = get_object_or_404(Milestone, id=milestone_id)

        update_data = payload.dict(exclude_unset=True)
        if 'project_id' in update_data:
            project = get_object_or_404(Project, id=update_data.pop('project_id'))
            milestone.project = project

        for attr, value in update_data.items():
            setattr(milestone, attr, value)

        milestone.save()
        return milestone
    except ValidationError as e:
        return 400, {'detail': e.messages[0]}


@router.delete("/{milestone_id}")
@require_permission("milestones", "delete")
def delete_milestone(request, milestone_id: int):
    """Delete a milestone"""
    milestone = get_object_or_404(Milestone, id=milestone_id)
    milestone.delete()
    return {"detail": "Milestone deleted successfully"}
