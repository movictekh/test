from datetime import date
from typing import List, Optional

from django.core.exceptions import ValidationError
from django.db.models import Q
from django.utils import timezone
from ninja import Query, Router
from ninja.pagination import LimitOffsetPagination, paginate

from user.api.schemas.board_resolution import (
    BoardResolutionChoicesSchema,
    BoardResolutionCreateSchema,
    BoardResolutionSchema,
    BoardResolutionUpdateSchema,
)
from user.api.schemas.others import MessageSchema
from user.models.board_resolution import BoardResolution
from user.utils.perm import require_permission

board_resolution_api = Router(tags=["Board Resolutions"])


@board_resolution_api.get("/choices", response=BoardResolutionChoicesSchema, auth=None)
def get_board_resolution_choices(request):
    return {
        "types": [{"value": v, "label": l} for v, l in BoardResolution.TYPE_CHOICES],
        "statuses": [
            {"value": v, "label": l} for v, l in BoardResolution.STATUS_CHOICES
        ],
    }


@board_resolution_api.get("", response=List[BoardResolutionSchema])
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("board_resolutions", "list")
def list_board_resolutions(
    request,
    status: Optional[str] = Query(None),
    resolution_type: Optional[str] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    search: Optional[str] = Query(None),
):
    qs = BoardResolution.objects.select_related("created_by", "approved_by").all()

    if status:
        qs = qs.filter(status=status)

    if resolution_type:
        qs = qs.filter(resolution_type=resolution_type)

    if date_from:
        qs = qs.filter(resolution_date__gte=date_from)

    if date_to:
        qs = qs.filter(resolution_date__lte=date_to)

    if search:
        qs = qs.filter(
            Q(title__icontains=search)
            | Q(description__icontains=search)
            | Q(resolution_id__icontains=search)
        )

    return qs


@board_resolution_api.get(
    "/{resolution_id}", response={200: BoardResolutionSchema, 404: MessageSchema}
)
@require_permission("board_resolutions", "view")
def get_board_resolution(request, resolution_id: int):
    try:
        resolution = BoardResolution.objects.select_related(
            "created_by", "approved_by"
        ).get(id=resolution_id)
        return 200, resolution
    except BoardResolution.DoesNotExist:
        return 404, {"detail": "Board resolution not found"}


@board_resolution_api.post(
    "", response={201: BoardResolutionSchema, 400: MessageSchema}
)
@require_permission("board_resolutions", "create")
def create_board_resolution(request, payload: BoardResolutionCreateSchema):
    try:
        resolution = BoardResolution.objects.create(
            title=payload.title,
            description=payload.description,
            resolution_type=payload.resolution_type,
            resolution_date=payload.resolution_date,
            status=payload.status or "pending",
            attachment_url=payload.attachment_url or "",
            notes=payload.notes or "",
            created_by=request.user,
        )

        return 201, resolution

    except ValidationError as e:
        return 400, {"detail": e.messages[0]}
    except Exception as e:
        return 400, {"detail": str(e)}


@board_resolution_api.put(
    "/{resolution_id}",
    response={200: BoardResolutionSchema, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("board_resolutions", "update")
def update_board_resolution(
    request, resolution_id: int, payload: BoardResolutionUpdateSchema
):
    try:
        resolution = BoardResolution.objects.select_related(
            "created_by", "approved_by"
        ).get(id=resolution_id)

        if resolution.status == "approved":
            return 400, {
                "detail": "Approved resolutions cannot be edited. Archive it first."
            }

        data = payload.dict(exclude_unset=True)
        # Status changes to 'approved' must go through the dedicated approve endpoint
        if data.get("status") == "approved":
            return 400, {"detail": "Use the approve endpoint to approve a resolution."}

        for field, value in data.items():
            setattr(resolution, field, value)

        resolution.full_clean()
        resolution.save()
        resolution.refresh_from_db()
        return 200, resolution

    except BoardResolution.DoesNotExist:
        return 404, {"detail": "Board resolution not found"}
    except ValidationError as e:
        return 400, {"detail": e.messages[0]}
    except Exception as e:
        return 400, {"detail": str(e)}


@board_resolution_api.post(
    "/{resolution_id}/approve",
    response={200: BoardResolutionSchema, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("board_resolutions", "approve")
def approve_board_resolution(request, resolution_id: int):
    try:
        resolution = BoardResolution.objects.select_related(
            "created_by", "approved_by"
        ).get(id=resolution_id)

        if resolution.status == "approved":
            return 400, {"detail": "Resolution is already approved."}

        if resolution.status == "archived":
            return 400, {"detail": "Archived resolutions cannot be approved."}

        if resolution.status == "draft":
            return 400, {
                "detail": "Resolution must be submitted for review (pending) before it can be approved."
            }

        resolution.status = "approved"
        resolution.approved_by = request.user
        resolution.approved_at = timezone.now()
        resolution.save()
        resolution.refresh_from_db()
        return 200, resolution

    except BoardResolution.DoesNotExist:
        return 404, {"detail": "Board resolution not found"}
    except ValidationError as e:
        return 400, {"detail": e.messages[0]}
    except Exception as e:
        return 400, {"detail": str(e)}


@board_resolution_api.delete(
    "/{resolution_id}",
    response={200: MessageSchema, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("board_resolutions", "delete")
def archive_board_resolution(request, resolution_id: int):
    try:
        resolution = BoardResolution.objects.get(id=resolution_id)
        resolution.status = "archived"
        resolution.save()
        return 200, {"detail": "Board resolution archived successfully"}

    except BoardResolution.DoesNotExist:
        return 404, {"detail": "Board resolution not found"}
    except ValidationError as e:
        return 400, {"detail": e.messages[0]}
    except Exception as e:
        return 400, {"detail": str(e)}
