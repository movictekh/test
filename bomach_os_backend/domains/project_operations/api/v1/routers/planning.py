"""Project planning HTTP endpoints: timelines and milestones."""

# --------------------------------------------------------------------------
# Timelines
# --------------------------------------------------------------------------

from typing import List

from django.core.exceptions import ValidationError
from django.db.models import Q
from django.shortcuts import get_object_or_404
from ninja import Router
from ninja.pagination import LimitOffsetPagination, paginate

from domains.project_operations.models import Project, Timeline
from user.utils.perm import require_permission

from ..schemas.schemas import (
    MessageSchema,
    TimelineCreateSchema,
    TimelineOutSchema,
    TimelineUpdateSchema,
)

timeline_router = Router(tags=["Timelines"])


@timeline_router.get(
    "",
    response=List[TimelineOutSchema],
    operation_id="operations_api_v1_timelines_list_timelines",
)
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
            Q(name__icontains=search) | Q(description__icontains=search)
        )

    return list(timelines)


@timeline_router.get(
    "/{timeline_id}",
    response=TimelineOutSchema,
    operation_id="operations_api_v1_timelines_get_timeline",
)
@require_permission("timelines", "view")
def get_timeline(request, timeline_id: int):
    """Get a specific timeline by ID"""
    timeline = get_object_or_404(Timeline, id=timeline_id)
    return timeline


@timeline_router.post(
    "",
    response={200: TimelineOutSchema, 400: MessageSchema},
    operation_id="operations_api_v1_timelines_create_timeline",
)
@require_permission("timelines", "create")
def create_timeline(request, payload: TimelineCreateSchema):
    """Create a new timeline"""
    try:
        timeline_data = payload.dict()
        project = get_object_or_404(Project, id=timeline_data.pop("project_id"))
        timeline = Timeline.objects.create(project=project, **timeline_data)
        return timeline
    except ValidationError as e:
        return 400, {"detail": e.messages[0]}


@timeline_router.put(
    "/{timeline_id}",
    response={200: TimelineOutSchema, 400: MessageSchema},
    operation_id="operations_api_v1_timelines_update_timeline",
)
@require_permission("timelines", "update")
def update_timeline(request, timeline_id: int, payload: TimelineUpdateSchema):
    """Update an existing timeline"""
    try:
        timeline = get_object_or_404(Timeline, id=timeline_id)

        update_data = payload.dict(exclude_unset=True)
        if "project_id" in update_data:
            project = get_object_or_404(Project, id=update_data.pop("project_id"))
            timeline.project = project

        for attr, value in update_data.items():
            setattr(timeline, attr, value)

        timeline.save()
        return timeline
    except ValidationError as e:
        return 400, {"detail": e.messages[0]}


@timeline_router.delete(
    "/{timeline_id}", operation_id="operations_api_v1_timelines_delete_timeline"
)
@require_permission("timelines", "delete")
def delete_timeline(request, timeline_id: int):
    """Delete a timeline"""
    timeline = get_object_or_404(Timeline, id=timeline_id)
    timeline.delete()
    return {"detail": "Timeline deleted successfully"}


# --------------------------------------------------------------------------
# Milestones
# --------------------------------------------------------------------------

from typing import List

from django.core.exceptions import ValidationError
from django.db.models import Q
from django.shortcuts import get_object_or_404
from ninja import Router
from ninja.pagination import LimitOffsetPagination, paginate

from domains.project_operations.models import Milestone, Project
from user.utils.perm import require_permission

from ..schemas.schemas import (
    MessageSchema,
    MilestoneCreateSchema,
    MilestoneOutSchema,
    MilestoneUpdateSchema,
)

milestone_router = Router(tags=["Milestones"])


@milestone_router.get(
    "",
    response=List[MilestoneOutSchema],
    operation_id="operations_api_v1_milestones_list_milestones",
)
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
            Q(name__icontains=search) | Q(description__icontains=search)
        )

    return list(milestones)


@milestone_router.get(
    "/{milestone_id}",
    response=MilestoneOutSchema,
    operation_id="operations_api_v1_milestones_get_milestone",
)
@require_permission("milestones", "view")
def get_milestone(request, milestone_id: int):
    """Get a specific milestone by ID"""
    milestone = get_object_or_404(Milestone, id=milestone_id)
    return milestone


@milestone_router.post(
    "",
    response={200: MilestoneOutSchema, 400: MessageSchema},
    operation_id="operations_api_v1_milestones_create_milestone",
)
@require_permission("milestones", "create")
def create_milestone(request, payload: MilestoneCreateSchema):
    """Create a new milestone"""
    try:
        milestone_data = payload.dict()
        project = get_object_or_404(Project, id=milestone_data.pop("project_id"))
        milestone = Milestone.objects.create(project=project, **milestone_data)
        return milestone
    except ValidationError as e:
        return 400, {"detail": e.messages[0]}


@milestone_router.put(
    "/{milestone_id}",
    response={200: MilestoneOutSchema, 400: MessageSchema},
    operation_id="operations_api_v1_milestones_update_milestone",
)
@require_permission("milestones", "update")
def update_milestone(request, milestone_id: int, payload: MilestoneUpdateSchema):
    """Update an existing milestone"""
    try:
        milestone = get_object_or_404(Milestone, id=milestone_id)

        update_data = payload.dict(exclude_unset=True)
        if "project_id" in update_data:
            project = get_object_or_404(Project, id=update_data.pop("project_id"))
            milestone.project = project

        for attr, value in update_data.items():
            setattr(milestone, attr, value)

        milestone.save()
        return milestone
    except ValidationError as e:
        return 400, {"detail": e.messages[0]}


@milestone_router.delete(
    "/{milestone_id}", operation_id="operations_api_v1_milestones_delete_milestone"
)
@require_permission("milestones", "delete")
def delete_milestone(request, milestone_id: int):
    """Delete a milestone"""
    milestone = get_object_or_404(Milestone, id=milestone_id)
    milestone.delete()
    return {"detail": "Milestone deleted successfully"}
