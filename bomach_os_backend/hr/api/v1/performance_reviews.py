from typing import List

from django.core.exceptions import ValidationError
from django.db.models import Q
from django.shortcuts import get_object_or_404
from ninja import Query, Router
from ninja.pagination import LimitOffsetPagination, paginate

from hr.api.schemas import (
    MessageSchema,
    PerformanceReviewCreateSchema,
    PerformanceReviewFilterSchema,
    PerformanceReviewResponseSchema,
    PerformanceReviewUpdateSchema,
)
from hr.models.performance_review import PerformanceReview
from user.utils.perm import check_obj_permission, require_permission, scope_queryset

router = Router(tags=["Performance Reviews"])


@router.post("/", response={201: PerformanceReviewResponseSchema, 400: MessageSchema})
@require_permission("performance_reviews", "create")
def create_performance_review(request, payload: PerformanceReviewCreateSchema):
    try:
        review = PerformanceReview.objects.create(**payload.model_dump())
        return 201, review
    except ValidationError as e:
        return 400, {"detail": e.messages[0]}
    except Exception as e:
        return 400, {"detail": str(e)}


@router.get("/", response=List[PerformanceReviewResponseSchema])
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("performance_reviews", "list", owner_lookup="employee__user")
def list_performance_reviews(
    request, filters: PerformanceReviewFilterSchema = Query(...)
):
    reviews = PerformanceReview.objects.all()

    if filters.employee_id:
        reviews = reviews.filter(employee_id=filters.employee_id)
    if filters.reviewer_id:
        reviews = reviews.filter(reviewer_id=filters.reviewer_id)
    if filters.review_period:
        reviews = reviews.filter(review_period__icontains=filters.review_period)
    if filters.min_rating:
        reviews = reviews.filter(overall_rating__gte=filters.min_rating)
    if filters.max_rating:
        reviews = reviews.filter(overall_rating__lte=filters.max_rating)
    if filters.date_from:
        reviews = reviews.filter(review_date__gte=filters.date_from)
    if filters.date_to:
        reviews = reviews.filter(review_date__lte=filters.date_to)

    reviews = scope_queryset(
        request,
        reviews,
        owner_field="employee__user",
        branch_field="employee__branch",
        department_field="employee__department",
    )
    return reviews


@router.get("/{review_id}", response=PerformanceReviewResponseSchema)
@require_permission("performance_reviews", "view", owner_lookup="employee__user")
def get_performance_review(request, review_id: int):
    review = get_object_or_404(PerformanceReview, id=review_id)
    check_obj_permission(request, review, owner_field="employee.user")
    return review


@router.put(
    "/{review_id}", response={200: PerformanceReviewResponseSchema, 400: MessageSchema}
)
@require_permission("performance_reviews", "update")
def update_performance_review(
    request, review_id: int, payload: PerformanceReviewUpdateSchema
):
    try:
        review = get_object_or_404(PerformanceReview, id=review_id)

        for attr, value in payload.model_dump(exclude_unset=True).items():
            setattr(review, attr, value)

        review.save()
        return 200, review
    except ValidationError as e:
        return 400, {"detail": e.messages[0]}


@router.delete("/{review_id}", response={204: None, 400: MessageSchema})
@require_permission("performance_reviews", "delete")
def delete_performance_review(request, review_id: int):
    try:
        review = get_object_or_404(PerformanceReview, id=review_id)
        review.delete()
        return 204, None
    except ValidationError as e:
        return 400, {"detail": e.messages[0]}
