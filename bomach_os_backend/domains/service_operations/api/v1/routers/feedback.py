from typing import List
from ninja import Router
from django.shortcuts import get_object_or_404
from django.db.models import Q, Avg, Count, Case, When, IntegerField, DecimalField
from django.db.models.functions import Coalesce
from decimal import Decimal

from ..schemas.feedback import (
    FeedbackIn, FeedbackOut, FeedbackUpdate, FeedbackStatsSchema,
)
from services.api.schema.others import MessageSchema
from services.models.feedback import ClientFeedback
from user.utils.perm import require_permission

router = Router(tags=["Feedback"])


def _feedback_out(fb):
    order = fb.order
    return FeedbackOut(
        id=fb.id,
        order_id=order.id,
        order_number=order.order_number,
        client_name=fb.client_name,
        service_name=fb.service_name,
        feedback_type=fb.feedback_type,
        rating=fb.rating,
        comment=fb.comment,
        internal_note=fb.internal_note,
        status=fb.status,
        recorded_by=fb.recorded_by,
        created_at=fb.created_at,
        updated_at=fb.updated_at,
    )


@router.get("", response=List[FeedbackOut])
@require_permission("feedback", "list")
def list_feedback(
    request,
    status: str = None,
    feedback_type: str = None,
    rating_min: int = None,
    search: str = None,
):
    """List all feedback with optional filtering."""
    feedbacks = ClientFeedback.objects.select_related(
        'order', 'recorded_by',
    ).all()

    if status:
        feedbacks = feedbacks.filter(status=status)
    if feedback_type:
        feedbacks = feedbacks.filter(feedback_type=feedback_type)
    if rating_min:
        feedbacks = feedbacks.filter(rating__gte=rating_min)
    if search:
        feedbacks = feedbacks.filter(
            Q(client_name__icontains=search) |
            Q(service_name__icontains=search) |
            Q(comment__icontains=search)
        )

    return [_feedback_out(fb) for fb in feedbacks]


@router.post("", response={201: FeedbackOut, 400: MessageSchema})
@require_permission("feedback", "create")
def create_feedback(request, payload: FeedbackIn):
    """Create a new feedback record."""
    from services.models.service import ServiceOrder

    try:
        order = ServiceOrder.objects.select_related('client', 'service').get(
            id=payload.order_id,
        )
    except ServiceOrder.DoesNotExist:
        return 400, {"detail": "Order not found"}

    try:
        client_name = order.client.company_name or order.client.user.get_full_name() or str(order.client)
    except Exception:
        client_name = str(order.client)

    service_name = order.service.name if order.service else ""

    fb = ClientFeedback.objects.create(
        order=order,
        recorded_by=request.user,
        client_name=client_name,
        service_name=service_name,
        feedback_type=payload.feedback_type,
        rating=payload.rating,
        comment=payload.comment,
        internal_note=payload.internal_note,
        status=payload.status,
    )

    return 201, _feedback_out(fb)


@router.get("/stats", response={200: FeedbackStatsSchema})
@require_permission("feedback", "list")
def feedback_stats(request):
    """Get feedback statistics: average rating, satisfaction, rework rate, repeat clients."""
    qs = ClientFeedback.objects.all()
    total = qs.count()

    if total == 0:
        return 200, FeedbackStatsSchema(
            total=0,
            average_rating=Decimal("0.00"),
            client_satisfaction=Decimal("0.00"),
            rework_rate=Decimal("0.00"),
            repeat_clients=Decimal("0.00"),
        )

    avg_rating = qs.aggregate(avg=Coalesce(Avg('rating'), Decimal('0'), output_field=DecimalField()))['avg']
    if isinstance(avg_rating, float):
        avg_rating = Decimal(str(avg_rating)).quantize(Decimal('0.01'))

    # Client satisfaction = % with rating >= 4
    satisfied = qs.filter(rating__gte=4).count()
    satisfaction = (Decimal(satisfied) / Decimal(total) * 100).quantize(Decimal('0.01'))

    # Rework rate = % with type defect_rework
    rework_count = qs.filter(feedback_type='defect_rework').count()
    rework = (Decimal(rework_count) / Decimal(total) * 100).quantize(Decimal('0.01'))

    # Repeat clients = % of distinct clients with >1 feedback
    repeat = (
        qs.values('client_name')
        .annotate(cnt=Count('id'))
        .filter(cnt__gt=1)
        .count()
    )
    distinct_clients = qs.values('client_name').distinct().count()
    repeat_pct = (Decimal(repeat) / Decimal(distinct_clients) * 100).quantize(Decimal('0.01')) if distinct_clients else Decimal('0.00')

    return 200, FeedbackStatsSchema(
        total=total,
        average_rating=avg_rating,
        client_satisfaction=satisfaction,
        rework_rate=rework,
        repeat_clients=repeat_pct,
    )


@router.get("/{feedback_id}", response=FeedbackOut)
@require_permission("feedback", "view")
def get_feedback(request, feedback_id: int):
    """Get a specific feedback record."""
    fb = get_object_or_404(
        ClientFeedback.objects.select_related('order', 'recorded_by'),
        id=feedback_id,
    )
    return _feedback_out(fb)


@router.put("/{feedback_id}", response={200: FeedbackOut, 400: MessageSchema, 404: MessageSchema})
@require_permission("feedback", "update")
def update_feedback(request, feedback_id: int, payload: FeedbackUpdate):
    """Update a feedback record."""
    try:
        fb = get_object_or_404(ClientFeedback, id=feedback_id)
        for attr, value in payload.dict(exclude_unset=True).items():
            setattr(fb, attr, value)
        fb.save()
        fb = ClientFeedback.objects.select_related('order', 'recorded_by').get(id=fb.id)
        return 200, _feedback_out(fb)
    except Exception as e:
        return 400, {"detail": str(e)}


@router.delete("/{feedback_id}", response={200: MessageSchema, 404: MessageSchema})
@require_permission("feedback", "delete")
def delete_feedback(request, feedback_id: int):
    """Delete a feedback record."""
    fb = get_object_or_404(ClientFeedback, id=feedback_id)
    fb.delete()
    return 200, {"detail": "Feedback deleted successfully"}
