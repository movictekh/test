from typing import Optional, List
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.http import Http404
from django.core.exceptions import ValidationError
from django.utils import timezone
from ninja import Router, Query
from ninja.pagination import paginate, LimitOffsetPagination
from user.api.schemas.others import MessageSchema
from user.models.drawing_bank import DrawingBank
from user.api.schemas.drawing_bank import (
    DrawingBankCreateSchema,
    DrawingBankUpdateSchema,
    DrawingBankRejectSchema,
    DrawingBankFullResponseSchema,
    DrawingBankListResponseSchema,
    DrawingBankStatsSchema,
)
from user.utils.perm import require_permission

drawing_bank_api = Router(tags=["Drawing Bank"])


@drawing_bank_api.get(
    "/stats", response={200: DrawingBankStatsSchema, 400: MessageSchema}
)
def get_drawing_bank_stats(request):
    try:
        drawings = DrawingBank.objects.filter(employee=request.user)
        return 200, {
            "total_submissions": drawings.count(),
            "pending_approval": drawings.filter(
                status=DrawingBank.STATUS.PENDING
            ).count(),
            "approved": drawings.filter(status=DrawingBank.STATUS.APPROVED).count(),
            "rejected": drawings.filter(status=DrawingBank.STATUS.REJECTED).count(),
        }
    except Exception as e:
        return 400, {"detail": str(e)}


@drawing_bank_api.post(
    "", response={201: DrawingBankFullResponseSchema, 400: MessageSchema}
)
@require_permission("drawings", "create")
def create_drawing(request, payload: DrawingBankCreateSchema):
    try:
        drawing = DrawingBank.objects.create(
            employee=request.user,
            title=payload.title,
            building_category=payload.building_category,
            drawing_file=payload.drawing_file,
            file_name=payload.file_name or "",
            file_size_mb=payload.file_size_mb,
            description=payload.description,
            tags=payload.tags or [],
        )
        drawing.full_clean()
        drawing.save()
        return 201, drawing
    except ValidationError as e:
        return 400, {"detail": e.messages[0]}
    except Exception as e:
        return 400, {"detail": str(e)}


@drawing_bank_api.get(
    "/{id}", response={200: DrawingBankFullResponseSchema, 404: MessageSchema}
)
@require_permission("drawings", "view")
def get_drawing(request, id: int):
    try:
        drawing = DrawingBank.objects.select_related("employee", "approved_by").get(
            id=id
        )
        if drawing.employee != request.user:
            return 404, {"detail": "Drawing not found."}
        return 200, drawing
    except DrawingBank.DoesNotExist:
        return 404, {"detail": "Drawing not found."}


@drawing_bank_api.get(
    "", response={200: List[DrawingBankListResponseSchema], 400: MessageSchema}
)
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("drawings", "list")
def get_drawings(
    request,
    status: Optional[str] = Query(None),
    building_category: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    tag: Optional[str] = Query(None),
):
    filters = Q(employee=request.user)

    if status:
        filters &= Q(status=status)

    if building_category:
        filters &= Q(building_category=building_category)

    if search:
        filters &= (
            Q(title__icontains=search)
            | Q(description__icontains=search)
            | Q(file_name__icontains=search)
        )

    if tag:
        filters &= Q(tags__contains=[tag])

    drawings = (
        DrawingBank.objects.filter(filters)
        .select_related("employee", "approved_by")
        .order_by("-created_at")
    )
    return drawings


@drawing_bank_api.put(
    "/{id}",
    response={
        200: DrawingBankFullResponseSchema,
        400: MessageSchema,
        404: MessageSchema,
    },
)
@require_permission("drawings", "update")
def update_drawing(request, id: int, payload: DrawingBankUpdateSchema):
    try:
        drawing = DrawingBank.objects.select_related("employee").get(id=id)
        if drawing.employee != request.user:
            return 404, {"detail": "Drawing not found."}

        if drawing.status == DrawingBank.STATUS.APPROVED:
            return 400, {"detail": "Approved drawings cannot be updated."}

        update_fields = payload.dict(exclude_unset=True)
        for field, value in update_fields.items():
            setattr(drawing, field, value)

        # Reset to pending if previously rejected and now being updated
        if drawing.status == DrawingBank.STATUS.REJECTED:
            drawing.status = DrawingBank.STATUS.PENDING
            drawing.rejection_reason = ""

        drawing.full_clean()
        drawing.save()
        return 200, drawing
    except DrawingBank.DoesNotExist:
        return 404, {"detail": "Drawing not found."}
    except ValidationError as e:
        return 400, {"detail": e.messages[0]}
    except Exception as e:
        return 400, {"detail": str(e)}


@drawing_bank_api.delete(
    "/{id}", response={200: MessageSchema, 404: MessageSchema, 400: MessageSchema}
)
@require_permission("drawings", "delete")
def delete_drawing(request, id: int):
    try:
        drawing = DrawingBank.objects.get(id=id)
        if drawing.employee != request.user:
            return 404, {"detail": "Drawing not found."}

        if drawing.status == DrawingBank.STATUS.APPROVED:
            return 400, {"detail": "Approved drawings cannot be deleted."}

        drawing.delete()
        return 200, {"detail": "Drawing deleted successfully."}
    except DrawingBank.DoesNotExist:
        return 404, {"detail": "Drawing not found."}
    except Exception as e:
        return 400, {"detail": str(e)}


@drawing_bank_api.post(
    "/{id}/approve",
    response={
        200: DrawingBankFullResponseSchema,
        403: MessageSchema,
        404: MessageSchema,
        400: MessageSchema,
    },
)
@require_permission("drawings", "approve")
def approve_drawing(request, id: int):
    try:
        drawing = get_object_or_404(DrawingBank, id=id)

        if drawing.status != DrawingBank.STATUS.PENDING:
            return 400, {"detail": "Only pending drawings can be approved."}

        drawing.status = DrawingBank.STATUS.APPROVED
        drawing.approved_by = request.user
        drawing.approved_at = timezone.now()
        drawing.save()
        return 200, drawing
    except Http404:
        return 404, {"detail": "Drawing not found."}
    except ValidationError as e:
        return 400, {"detail": e.messages[0]}
    except Exception as e:
        return 400, {"detail": str(e)}


@drawing_bank_api.post(
    "/{id}/reject",
    response={
        200: DrawingBankFullResponseSchema,
        403: MessageSchema,
        404: MessageSchema,
        400: MessageSchema,
    },
)
@require_permission("drawings", "reject")
def reject_drawing(request, id: int, payload: DrawingBankRejectSchema):
    try:
        drawing = get_object_or_404(DrawingBank, id=id)

        if drawing.status != DrawingBank.STATUS.PENDING:
            return 400, {"detail": "Only pending drawings can be rejected."}

        drawing.status = DrawingBank.STATUS.REJECTED
        drawing.rejection_reason = payload.rejection_reason
        drawing.save()
        return 200, drawing
    except Http404:
        return 404, {"detail": "Drawing not found."}
    except ValidationError as e:
        return 400, {"detail": e.messages[0]}
    except Exception as e:
        return 400, {"detail": str(e)}


@drawing_bank_api.post(
    "/{id}/download", response={200: MessageSchema, 404: MessageSchema}
)
@require_permission("drawings", "download")
def track_download(request, id: int):
    try:
        drawing = get_object_or_404(DrawingBank, id=id)

        if drawing.status != DrawingBank.STATUS.APPROVED:
            return 400, {"detail": "Only approved drawings can be downloaded."}

        drawing.download_count += 1
        drawing.save(update_fields=["download_count"])
        return 200, {"detail": "Download recorded."}
    except Http404:
        return 404, {"detail": "Drawing not found."}
