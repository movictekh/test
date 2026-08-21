from typing import List, Optional

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db.models import Q
from django.shortcuts import get_object_or_404
from ninja import Query, Router
from ninja.errors import HttpError
from ninja.pagination import LimitOffsetPagination, paginate

from domains.service_operations.models import (
    ServiceDeliverable,
    ServiceExecutionTask,
    ServiceOrder,
)
from domains.service_operations.services import orders as order_services
from shared.api.schema.others import MessageSchema
from user.utils.perm import require_permission, scope_queryset

from ..schemas.lifecycle import (
    ServiceDeliverableActionIn,
    ServiceDeliverableIn,
    ServiceDeliverableOut,
    ServiceDeliverableUpdate,
    ServiceExecutionTaskIn,
    ServiceExecutionTaskOut,
    ServiceExecutionTaskUpdate,
    ServiceOrderActivityIn,
    ServiceOrderActivityOut,
    ServiceOrderIn,
    ServiceOrderMilestoneIn,
    ServiceOrderMilestoneOut,
    ServiceOrderOut,
    ServiceOrderUpdate,
)

router = Router(tags=["Service Orders"])


def _validation_detail(exc):
    if hasattr(exc, "message_dict"):
        return "; ".join(
            f"{field}: {', '.join(messages)}"
            for field, messages in exc.message_dict.items()
        )
    return exc.messages[0] if getattr(exc, "messages", None) else str(exc)


def _order_queryset():
    return ServiceOrder.objects.select_related(
        "client",
        "client__user",
        "service",
        "service__category",
        "quote",
        "service_request",
        "service_request__branch",
        "invoice",
        "created_by",
        "assigned_to",
        "assigned_to__user",
    ).prefetch_related(
        "milestones",
        "activities",
        "tasks",
        "deliverables",
    )


def _staff_order_or_404(request, order_id):
    order = get_object_or_404(_order_queryset(), id=order_id)
    branch_ids = getattr(request, "_perm_branch_ids", [])
    if branch_ids:
        branch_id = (
            order.service_request.branch_id if order.service_request_id else None
        )
        if branch_id not in branch_ids:
            raise HttpError(
                403, "You do not have permission to access this service order."
            )
    return order


def _task_queryset():
    return ServiceExecutionTask.objects.select_related(
        "order",
        "order__service_request",
        "order__service_request__branch",
        "milestone",
        "owner",
        "owner__user",
        "created_by",
    ).prefetch_related("assignees")


def _deliverable_queryset():
    return ServiceDeliverable.objects.select_related(
        "order",
        "order__service_request",
        "order__service_request__branch",
        "milestone",
        "task",
        "owner",
        "owner__user",
        "approved_by",
        "rejected_by",
        "created_by",
    )


def _staff_task_or_404(request, order, task_id):
    return get_object_or_404(_task_queryset(), id=task_id, order=order)


def _staff_deliverable_or_404(request, order, deliverable_id):
    return get_object_or_404(_deliverable_queryset(), id=deliverable_id, order=order)


@router.get("", response=List[ServiceOrderOut])
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("orders", "list")
def list_orders(
    request,
    order_status: Optional[str] = Query(None),
    payment_status: Optional[str] = Query(None),
    client_id: Optional[int] = Query(None),
    service_request_id: Optional[int] = Query(None),
    invoice_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
):
    """List service orders with optional filtering."""
    orders = scope_queryset(
        request, _order_queryset(), branch_field="service_request__branch_id"
    )

    if order_status:
        orders = orders.filter(order_status=order_status)
    if payment_status:
        orders = orders.filter(payment_status=payment_status)
    if client_id:
        orders = orders.filter(client_id=client_id)
    if service_request_id:
        orders = orders.filter(service_request_id=service_request_id)
    if invoice_id:
        orders = orders.filter(invoice_id=invoice_id)
    if search:
        orders = orders.filter(
            Q(order_number__icontains=search)
            | Q(client__company_name__icontains=search)
            | Q(client__user__first_name__icontains=search)
            | Q(client__user__last_name__icontains=search)
            | Q(client__user__email__icontains=search)
            | Q(service__name__icontains=search)
        )

    return orders.order_by("-created_at")


@router.post("", response={201: ServiceOrderOut, 400: MessageSchema})
@require_permission("orders", "create")
def create_order(request, payload: ServiceOrderIn):
    try:
        data = payload.dict(exclude_unset=True)
        if data.get("invoice_id"):
            return 400, {
                "detail": "Use the invoice service-order endpoint to create invoice-backed orders."
            }
        data["created_by_id"] = request.user.id
        order = order_services.create_manual_order(data, request.user)
        return 201, _order_queryset().get(id=order.id)
    except (ValidationError, IntegrityError) as e:
        return 400, {"detail": _validation_detail(e)}


@router.get("/{order_id}", response={200: ServiceOrderOut, 404: MessageSchema})
@require_permission("orders", "view")
def get_order(request, order_id: int):
    """Get a specific service order by ID."""
    return 200, _staff_order_or_404(request, order_id)


@router.patch(
    "/{order_id}",
    response={200: ServiceOrderOut, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("orders", "update")
def patch_order(request, order_id: int, payload: ServiceOrderUpdate):
    try:
        order = _staff_order_or_404(request, order_id)
        order_services.update_order(order, payload, user=request.user)
        return 200, _order_queryset().get(id=order.id)
    except (ValidationError, IntegrityError) as e:
        return 400, {"detail": _validation_detail(e)}


@router.put(
    "/{order_id}",
    response={200: ServiceOrderOut, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("orders", "update")
def update_order(request, order_id: int, payload: ServiceOrderUpdate):
    return patch_order(request, order_id, payload)


@router.post(
    "/{order_id}/activities",
    response={201: ServiceOrderActivityOut, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("orders", "update")
def create_order_activity(request, order_id: int, payload: ServiceOrderActivityIn):
    try:
        order = _staff_order_or_404(request, order_id)
        return 201, order_services.create_order_activity(
            order, payload, user=request.user
        )
    except (ValidationError, IntegrityError) as e:
        return 400, {"detail": _validation_detail(e)}


@router.post(
    "/{order_id}/milestones",
    response={201: ServiceOrderMilestoneOut, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("orders", "update")
def create_order_milestone(request, order_id: int, payload: ServiceOrderMilestoneIn):
    try:
        order = _staff_order_or_404(request, order_id)
        return 201, order_services.create_order_milestone(
            order, payload, user=request.user
        )
    except (ValidationError, IntegrityError) as e:
        return 400, {"detail": _validation_detail(e)}


@router.post(
    "/{order_id}/milestones/{milestone_id}/complete",
    response={200: ServiceOrderOut, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("orders", "update")
def complete_order_milestone(request, order_id: int, milestone_id: int):
    try:
        order = _staff_order_or_404(request, order_id)
        order_services.complete_order_milestone(order, milestone_id, user=request.user)
        return 200, _order_queryset().get(id=order.id)
    except (ValidationError, IntegrityError) as e:
        return 400, {"detail": _validation_detail(e)}


@router.post(
    "/{order_id}/milestones/{milestone_id}/reopen",
    response={200: ServiceOrderOut, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("orders", "update")
def reopen_order_milestone(request, order_id: int, milestone_id: int):
    try:
        order = _staff_order_or_404(request, order_id)
        order_services.reopen_order_milestone(order, milestone_id, user=request.user)
        return 200, _order_queryset().get(id=order.id)
    except (ValidationError, IntegrityError) as e:
        return 400, {"detail": _validation_detail(e)}


@router.get("/{order_id}/tasks", response=List[ServiceExecutionTaskOut])
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("orders", "view")
def list_order_tasks(
    request,
    order_id: int,
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    milestone_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
):
    order = _staff_order_or_404(request, order_id)
    tasks = _task_queryset().filter(order=order)
    if status:
        tasks = tasks.filter(status=status)
    if priority:
        tasks = tasks.filter(priority=priority)
    if milestone_id:
        tasks = tasks.filter(milestone_id=milestone_id)
    if search:
        tasks = tasks.filter(
            Q(task_number__icontains=search)
            | Q(title__icontains=search)
            | Q(description__icontains=search)
        )
    return tasks.order_by("due_date", "-created_at")


@router.post(
    "/{order_id}/tasks",
    response={201: ServiceExecutionTaskOut, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("orders", "update")
def create_order_task(request, order_id: int, payload: ServiceExecutionTaskIn):
    try:
        order = _staff_order_or_404(request, order_id)
        task = order_services.create_order_task(order, payload, user=request.user)
        return 201, _task_queryset().get(id=task.id)
    except (ValidationError, IntegrityError) as e:
        return 400, {"detail": _validation_detail(e)}


@router.get(
    "/{order_id}/tasks/{task_id}",
    response={200: ServiceExecutionTaskOut, 404: MessageSchema},
)
@require_permission("orders", "view")
def get_order_task(request, order_id: int, task_id: int):
    order = _staff_order_or_404(request, order_id)
    return 200, _staff_task_or_404(request, order, task_id)


@router.patch(
    "/{order_id}/tasks/{task_id}",
    response={200: ServiceExecutionTaskOut, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("orders", "update")
def patch_order_task(
    request, order_id: int, task_id: int, payload: ServiceExecutionTaskUpdate
):
    try:
        order = _staff_order_or_404(request, order_id)
        task = _staff_task_or_404(request, order, task_id)
        order_services.update_order_task(order, task, payload, user=request.user)
        return 200, _task_queryset().get(id=task.id)
    except (ValidationError, IntegrityError) as e:
        return 400, {"detail": _validation_detail(e)}


@router.put(
    "/{order_id}/tasks/{task_id}",
    response={200: ServiceExecutionTaskOut, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("orders", "update")
def update_order_task(
    request, order_id: int, task_id: int, payload: ServiceExecutionTaskUpdate
):
    return patch_order_task(request, order_id, task_id, payload)


@router.post(
    "/{order_id}/tasks/{task_id}/advance",
    response={200: ServiceExecutionTaskOut, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("orders", "update")
def advance_order_task(request, order_id: int, task_id: int):
    try:
        order = _staff_order_or_404(request, order_id)
        task = _staff_task_or_404(request, order, task_id)
        order_services.advance_order_task(order, task, user=request.user)
        return 200, _task_queryset().get(id=task.id)
    except (ValidationError, IntegrityError) as e:
        return 400, {"detail": _validation_detail(e)}


@router.delete(
    "/{order_id}/tasks/{task_id}",
    response={200: MessageSchema, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("orders", "update")
def delete_order_task(request, order_id: int, task_id: int):
    order = _staff_order_or_404(request, order_id)
    task = _staff_task_or_404(request, order, task_id)
    order_services.delete_order_task(order, task, user=request.user)
    return 200, {"detail": "Task deleted successfully"}


@router.get("/{order_id}/deliverables", response=List[ServiceDeliverableOut])
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("orders", "view")
def list_order_deliverables(
    request,
    order_id: int,
    status: Optional[str] = Query(None),
    deliverable_type: Optional[str] = Query(None),
    client_visible: Optional[bool] = Query(None),
    milestone_id: Optional[int] = Query(None),
    task_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
):
    order = _staff_order_or_404(request, order_id)
    deliverables = _deliverable_queryset().filter(order=order)
    if status:
        deliverables = deliverables.filter(status=status)
    if deliverable_type:
        deliverables = deliverables.filter(deliverable_type=deliverable_type)
    if client_visible is not None:
        deliverables = deliverables.filter(client_visible=client_visible)
    if milestone_id:
        deliverables = deliverables.filter(milestone_id=milestone_id)
    if task_id:
        deliverables = deliverables.filter(task_id=task_id)
    if search:
        deliverables = deliverables.filter(
            Q(deliverable_number__icontains=search)
            | Q(title__icontains=search)
            | Q(description__icontains=search)
        )
    return deliverables.order_by("-created_at")


@router.post(
    "/{order_id}/deliverables",
    response={201: ServiceDeliverableOut, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("orders", "update")
def create_order_deliverable(request, order_id: int, payload: ServiceDeliverableIn):
    try:
        order = _staff_order_or_404(request, order_id)
        obj = order_services.create_order_deliverable(order, payload, user=request.user)
        return 201, _deliverable_queryset().get(id=obj.id)
    except (ValidationError, IntegrityError) as e:
        return 400, {"detail": _validation_detail(e)}


@router.get(
    "/{order_id}/deliverables/{deliverable_id}",
    response={200: ServiceDeliverableOut, 404: MessageSchema},
)
@require_permission("orders", "view")
def get_order_deliverable(request, order_id: int, deliverable_id: int):
    order = _staff_order_or_404(request, order_id)
    return 200, _staff_deliverable_or_404(request, order, deliverable_id)


@router.patch(
    "/{order_id}/deliverables/{deliverable_id}",
    response={200: ServiceDeliverableOut, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("orders", "update")
def patch_order_deliverable(
    request, order_id: int, deliverable_id: int, payload: ServiceDeliverableUpdate
):
    try:
        order = _staff_order_or_404(request, order_id)
        obj = _staff_deliverable_or_404(request, order, deliverable_id)
        order_services.update_order_deliverable(order, obj, payload, user=request.user)
        return 200, _deliverable_queryset().get(id=obj.id)
    except (ValidationError, IntegrityError) as e:
        return 400, {"detail": _validation_detail(e)}


@router.put(
    "/{order_id}/deliverables/{deliverable_id}",
    response={200: ServiceDeliverableOut, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("orders", "update")
def update_order_deliverable(
    request, order_id: int, deliverable_id: int, payload: ServiceDeliverableUpdate
):
    return patch_order_deliverable(request, order_id, deliverable_id, payload)


@router.post(
    "/{order_id}/deliverables/{deliverable_id}/approve",
    response={200: ServiceDeliverableOut, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("orders", "update")
def approve_order_deliverable(request, order_id: int, deliverable_id: int):
    try:
        order = _staff_order_or_404(request, order_id)
        obj = _staff_deliverable_or_404(request, order, deliverable_id)
        order_services.approve_order_deliverable(order, obj, user=request.user)
        return 200, _deliverable_queryset().get(id=obj.id)
    except (ValidationError, IntegrityError) as e:
        return 400, {"detail": _validation_detail(e)}


@router.post(
    "/{order_id}/deliverables/{deliverable_id}/reject",
    response={200: ServiceDeliverableOut, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("orders", "update")
def reject_order_deliverable(
    request, order_id: int, deliverable_id: int, payload: ServiceDeliverableActionIn
):
    try:
        order = _staff_order_or_404(request, order_id)
        obj = _staff_deliverable_or_404(request, order, deliverable_id)
        order_services.reject_order_deliverable(
            order, obj, reason=payload.reason, user=request.user
        )
        return 200, _deliverable_queryset().get(id=obj.id)
    except (ValidationError, IntegrityError) as e:
        return 400, {"detail": _validation_detail(e)}


@router.delete(
    "/{order_id}/deliverables/{deliverable_id}",
    response={200: MessageSchema, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("orders", "update")
def delete_order_deliverable(request, order_id: int, deliverable_id: int):
    order = _staff_order_or_404(request, order_id)
    obj = _staff_deliverable_or_404(request, order, deliverable_id)
    try:
        order_services.delete_order_deliverable(order, obj, user=request.user)
        return 200, {"detail": "Deliverable deleted successfully"}
    except ValidationError as e:
        return 400, {"detail": _validation_detail(e)}


@router.delete(
    "/{order_id}", response={200: MessageSchema, 400: MessageSchema, 404: MessageSchema}
)
@require_permission("orders", "delete")
def delete_order(request, order_id: int):
    """Delete a service order."""
    try:
        order = _staff_order_or_404(request, order_id)
        order.delete()
        return 200, {"detail": "Order deleted successfully"}
    except (ValidationError, IntegrityError) as e:
        return 400, {"detail": _validation_detail(e)}
