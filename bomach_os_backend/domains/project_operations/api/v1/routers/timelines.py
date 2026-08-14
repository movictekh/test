from ninja import Router
from typing import List
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.core.exceptions import ValidationError

from domains.project_operations.models import Timeline, Project
from ..schemas.schemas import TimelineCreateSchema, TimelineUpdateSchema, TimelineOutSchema, MessageSchema
from ninja.pagination import paginate, LimitOffsetPagination
from user.utils.perm import require_permission

router = Router(tags=["Timelines"])


@router.get("", response=List[TimelineOutSchema], operation_id="operations_api_v1_timelines_list_timelines")
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("timelines", "list")
def list_timelines(
    request,
    project_id: int = None,
    status: str = None,
    search: str = None,
):
    """List all timelines with optional filters"""
    timelines = Timeline.objects.all()

    if project_id:
        timelines = timelines.filter(project_id=project_id)
    if status:
        timelines = timelines.filter(status=status)
    if search:
        timelines = timelines.filter(
            Q(name__icontains=search) |
            Q(description__icontains=search)
        )

    return list(timelines)


@router.get("/{timeline_id}", response=TimelineOutSchema, operation_id="operations_api_v1_timelines_get_timeline")
@require_permission("timelines", "view")
def get_timeline(request, timeline_id: int):
    """Get a specific timeline by ID"""
    timeline = get_object_or_404(Timeline, id=timeline_id)
    return timeline


@router.post("", response={200: TimelineOutSchema, 400: MessageSchema}, operation_id="operations_api_v1_timelines_create_timeline")
@require_permission("timelines", "create")
def create_timeline(request, payload: TimelineCreateSchema):
    """Create a new timeline"""
    try:
        timeline_data = payload.dict()
        project = get_object_or_404(Project, id=timeline_data.pop('project_id'))
        timeline = Timeline.objects.create(project=project, **timeline_data)
        return timeline
    except ValidationError as e:
        return 400, {'detail': e.messages[0]}


@router.put("/{timeline_id}", response={200: TimelineOutSchema, 400: MessageSchema}, operation_id="operations_api_v1_timelines_update_timeline")
@require_permission("timelines", "update")
def update_timeline(request, timeline_id: int, payload: TimelineUpdateSchema):
    """Update an existing timeline"""
    try:
        timeline = get_object_or_404(Timeline, id=timeline_id)

        update_data = payload.dict(exclude_unset=True)
        if 'project_id' in update_data:
            project = get_object_or_404(Project, id=update_data.pop('project_id'))
            timeline.project = project

        for attr, value in update_data.items():
            setattr(timeline, attr, value)

        timeline.save()
        return timeline
    except ValidationError as e:
        return 400, {'detail': e.messages[0]}


@router.delete("/{timeline_id}", operation_id="operations_api_v1_timelines_delete_timeline")
@require_permission("timelines", "delete")
def delete_timeline(request, timeline_id: int):
    """Delete a timeline"""
    timeline = get_object_or_404(Timeline, id=timeline_id)
    timeline.delete()
    return {"detail": "Timeline deleted successfully"}
