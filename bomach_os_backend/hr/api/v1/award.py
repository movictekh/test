from typing import List

from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from ninja import Router
from ninja.pagination import LimitOffsetPagination, paginate

from hr.api.schemas import MessageSchema
from hr.api.schemas.award import AwardCreateSchema, AwardSchema, AwardUpdateSchema
from hr.models.award import Award
from system.authorization import check_obj_permission, require_permission, scope_queryset

router = Router(tags=["Awards"])


@router.post("/", response={201: AwardSchema, 400: MessageSchema})
@require_permission("awards", "create")
def create_award(request, payload: AwardCreateSchema):
    try:
        award = Award.objects.create(
            title=payload.title,
            category=payload.category,
            date_awarded=payload.date_awarded,
            rank_level=payload.rank_level,
            description=payload.description,
        )
        return 201, award
    except ValidationError as e:
        return 400, {"detail": e.messages[0]}


@router.get("/", response=List[AwardSchema])
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("awards", "list")
def list_awards(request, year: int = None):
    qs = Award.objects.all()
    if year:
        qs = qs.filter(date_awarded__year=year)
    return qs


@router.get("/{award_id}", response=AwardSchema)
@require_permission("awards", "view")
def get_award(request, award_id: int):
    return get_object_or_404(Award, id=award_id)


@router.put("/{award_id}", response={200: AwardSchema, 400: MessageSchema})
@require_permission("awards", "update")
def update_award(request, award_id: int, payload: AwardUpdateSchema):
    try:
        award = get_object_or_404(Award, id=award_id)
        for attr, value in payload.model_dump(exclude_unset=True).items():
            setattr(award, attr, value)
        award.save()
        return 200, award
    except ValidationError as e:
        return 400, {"detail": e.messages[0]}


@router.delete("/{award_id}", response={200: MessageSchema, 400: MessageSchema})
@require_permission("awards", "delete")
def delete_award(request, award_id: int):
    try:
        award = get_object_or_404(Award, id=award_id)
        award.delete()
        return 200, {"detail": "Deleted successfully"}
    except ValidationError as e:
        return 400, {"detail": e.messages[0]}
