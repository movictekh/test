from typing import List, Optional

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja import Query, Router
from ninja.errors import HttpError
from ninja.pagination import LimitOffsetPagination, paginate

from services.api.schema.others import MessageSchema
from services.api.schema.schemas import (
    ServiceOrderActivityIn,
    ServiceOrderActivityOut,
    ServiceDeliverableActionIn,
    ServiceDeliverableIn,
    ServiceDeliverableOut,
    ServiceDeliverableUpdate,
    ServiceExecutionTaskIn,
    ServiceExecutionTaskOut,
    ServiceExecutionTaskUpdate,
    ServiceOrderIn,
    ServiceOrderMilestoneIn,
    ServiceOrderMilestoneOut,
    ServiceOrderOut,
    ServiceOrderUpdate,
)
from services.models.service import (
    ServiceDeliverable,
    ServiceExecutionTask,
    ServiceOrder,
    ServiceOrderActivity,
    ServiceOrderMilestone,
)
from services.utils.service_orders import create_manual_order
from user.utils.perm import require_permission, scope_queryset

router = Router(tags=["Service Orders"])


def _validation_detail(exc):
    if hasattr(exc, "message_dict"):
        return "; ".join(
            f"{field}: {', '.join(messages)}"
            for field, messages in exc.message_dict.items()
        )
    return exc.messages[0] if getattr(exc, "messages", None) else str(exc)


def _choice_values(choices):
    return {choice[0] for choice in choices}


def _ensure_choice(value, choices, field_name):
    if value and value not in _choice_values(choices):
        raise ValidationError({field_name: f"Invalid {field_name}: {value}."})


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


def _log_order_activity(
    order,
    activity_type,
    note,
    created_by,
    visibility="internal_client",
    progress=None,
    next_action="",
):
    return ServiceOrderActivity.objects.create(
        order=order,
        activity_type=activity_type,
        visibility=visibility,
        note=note,
        progress=progress,
        next_action=next_action,
        created_by=created_by,
    )


def _task_payload_data(payload):
    data = payload.dict(exclude_unset=True)
    assignee_ids = data.pop("assignee_ids", [])
    return data, assignee_ids


def _set_task_assignees(task, assignee_ids):
    if assignee_ids is not None:
        task.assignees.set(assignee_ids)


def _deliverable_payload_data(payload):
    data = payload.dict(exclude_unset=True)
    if "status" not in data or data["status"] is None:
        data["status"] = (
            "approved"
            if data.get("approval_mode", "none") == "none"
            else "under_review"
        )
    return data


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
    """Create a manual/backfill service order."""
    try:
        data = payload.dict(exclude_unset=True)
        if data.get("invoice_id"):
            return 400, {
                "detail": "Use the invoice service-order endpoint to create invoice-backed orders."
            }
        data["created_by_id"] = request.user.id
        with transaction.atomic():
            order = create_manual_order(data, request.user)
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
    """Update an existing service order."""
    try:
        order = _staff_order_or_404(request, order_id)
        data = payload.dict(exclude_unset=True)
        if "invoice_id" in data and data["invoice_id"] != order.invoice_id:
            return 400, {
                "detail": "Invoice links cannot be changed from the order update endpoint."
            }

        _ensure_choice(
            data.get("order_status"), ServiceOrder.ORDER_STATUS_CHOICES, "order_status"
        )
        old_status = order.order_status
        for attr, value in data.items():
            if attr == "invoice_id":
                continue
            setattr(order, attr, value)
        order.save()
        ServiceOrderActivity.objects.create(
            order=order,
            activity_type="control_update",
            visibility="internal_client",
            note=f"Service order updated. Status: {order.order_status}; progress: {order.progress}%.",
            progress=order.progress,
            next_action=order.next_action,
            created_by=request.user,
        )
        if old_status != order.order_status and order.service_request_id:
            order.service_request.next_action = (
                order.next_action or f"Track {order.order_number}"
            )
            order.service_request.save(update_fields=["next_action", "updated_at"])
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
        _ensure_choice(
            payload.activity_type,
            ServiceOrderActivity.ACTIVITY_TYPE_CHOICES,
            "activity_type",
        )
        _ensure_choice(
            payload.visibility, ServiceOrderActivity.VISIBILITY_CHOICES, "visibility"
        )
        data = payload.dict(exclude_unset=True)
        if "progress" in data:
            order.progress = data["progress"]
        if "next_action" in data:
            order.next_action = data["next_action"] or ""
        order.save()
        activity = ServiceOrderActivity.objects.create(
            order=order,
            activity_type=payload.activity_type,
            visibility=payload.visibility,
            note=payload.note,
            progress=data.get("progress"),
            next_action=data.get("next_action") or "",
            created_by=request.user,
        )
        return 201, activity
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
        _ensure_choice(payload.status, ServiceOrderMilestone.STATUS_CHOICES, "status")
        milestone = ServiceOrderMilestone.objects.create(order=order, **payload.dict())
        ServiceOrderActivity.objects.create(
            order=order,
            activity_type="milestone_added",
            visibility="internal_client" if milestone.client_visible else "internal",
            note=f"Milestone added: {milestone.name}.",
            created_by=request.user,
        )
        return 201, milestone
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
        with transaction.atomic():
            milestone = get_object_or_404(
                ServiceOrderMilestone.objects.select_for_update(),
                id=milestone_id,
                order=order,
            )
            milestone.status = "done"
            milestone.completed_at = timezone.now()
            milestone.save(update_fields=["status", "completed_at", "updated_at"])

            next_milestone = (
                order.milestones.filter(
                    status="pending", sort_order__gte=milestone.sort_order
                )
                .order_by("sort_order", "id")
                .first()
            )
            if next_milestone:
                next_milestone.status = "active"
                next_milestone.save(update_fields=["status", "updated_at"])
                if order.order_status == "pending_mobilisation":
                    order.order_status = "active"
                    order.save(
                        update_fields=["order_status", "started_at", "updated_at"]
                    )

            order.refresh_progress_from_milestones()
            ServiceOrderActivity.objects.create(
                order=order,
                activity_type="stage_advanced",
                visibility=(
                    "internal_client" if milestone.client_visible else "internal"
                ),
                note=f"Milestone completed: {milestone.name}.",
                progress=order.progress,
                next_action=order.next_action,
                created_by=request.user,
            )
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
        with transaction.atomic():
            milestone = get_object_or_404(
                ServiceOrderMilestone.objects.select_for_update(),
                id=milestone_id,
                order=order,
            )
            milestone.status = "active"
            milestone.completed_at = None
            milestone.save(update_fields=["status", "completed_at", "updated_at"])
            if order.order_status == "completed":
                order.order_status = "active"
                order.completed_at = None
                order.save(update_fields=["order_status", "completed_at", "updated_at"])
            order.refresh_progress_from_milestones()
            ServiceOrderActivity.objects.create(
                order=order,
                activity_type="milestone_reopened",
                visibility=(
                    "internal_client" if milestone.client_visible else "internal"
                ),
                note=f"Milestone reopened: {milestone.name}.",
                progress=order.progress,
                next_action=order.next_action,
                created_by=request.user,
            )
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
        data, assignee_ids = _task_payload_data(payload)
        _ensure_choice(
            data.get("status"), ServiceExecutionTask.STATUS_CHOICES, "status"
        )
        _ensure_choice(
            data.get("priority"), ServiceExecutionTask.PRIORITY_CHOICES, "priority"
        )
        task = ServiceExecutionTask.objects.create(
            order=order, created_by=request.user, **data
        )
        _set_task_assignees(task, assignee_ids)
        _log_order_activity(
            order,
            "task_created",
            f"Execution task {task.task_number} created: {task.title}.",
            created_by=request.user,
            next_action=order.next_action,
        )
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
        data, assignee_ids = _task_payload_data(payload)
        _ensure_choice(
            data.get("status"), ServiceExecutionTask.STATUS_CHOICES, "status"
        )
        _ensure_choice(
            data.get("priority"), ServiceExecutionTask.PRIORITY_CHOICES, "priority"
        )
        for attr, value in data.items():
            setattr(task, attr, value)
        task.save()
        _set_task_assignees(
            task,
            (
                assignee_ids
                if "assignee_ids" in payload.dict(exclude_unset=True)
                else None
            ),
        )
        _log_order_activity(
            order,
            "task_updated",
            f"Execution task {task.task_number} updated. Status: {task.status}.",
            created_by=request.user,
            next_action=order.next_action,
        )
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
        transitions = {
            "to_do": "in_progress",
            "in_progress": "review",
            "review": "done",
        }
        if task.status not in transitions:
            return 400, {"detail": "Task cannot be advanced from its current status."}
        task.status = transitions[task.status]
        task.save()
        _log_order_activity(
            order,
            "task_advanced",
            f"Execution task {task.task_number} advanced to {task.status}.",
            created_by=request.user,
            next_action=order.next_action,
        )
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
    task.delete()
    _log_order_activity(
        order,
        "task_updated",
        f"Execution task {task.task_number} deleted.",
        created_by=request.user,
        visibility="internal",
    )
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
        data = _deliverable_payload_data(payload)
        _ensure_choice(
            data.get("deliverable_type"),
            ServiceDeliverable.DELIVERABLE_TYPE_CHOICES,
            "deliverable_type",
        )
        _ensure_choice(data.get("status"), ServiceDeliverable.STATUS_CHOICES, "status")
        _ensure_choice(
            data.get("approval_mode"),
            ServiceDeliverable.APPROVAL_MODE_CHOICES,
            "approval_mode",
        )
        deliverable = ServiceDeliverable.objects.create(
            order=order, created_by=request.user, **data
        )
        _log_order_activity(
            order,
            "deliverable_added",
            f"Deliverable {deliverable.deliverable_number} added: {deliverable.title}.",
            created_by=request.user,
            visibility="internal_client" if deliverable.client_visible else "internal",
            next_action=order.next_action,
        )
        return 201, _deliverable_queryset().get(id=deliverable.id)
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
        deliverable = _staff_deliverable_or_404(request, order, deliverable_id)
        data = payload.dict(exclude_unset=True)
        _ensure_choice(
            data.get("deliverable_type"),
            ServiceDeliverable.DELIVERABLE_TYPE_CHOICES,
            "deliverable_type",
        )
        _ensure_choice(data.get("status"), ServiceDeliverable.STATUS_CHOICES, "status")
        _ensure_choice(
            data.get("approval_mode"),
            ServiceDeliverable.APPROVAL_MODE_CHOICES,
            "approval_mode",
        )
        for attr, value in data.items():
            setattr(deliverable, attr, value)
        deliverable.save()
        _log_order_activity(
            order,
            "deliverable_added",
            f"Deliverable {deliverable.deliverable_number} updated. Status: {deliverable.status}.",
            created_by=request.user,
            visibility="internal_client" if deliverable.client_visible else "internal",
            next_action=order.next_action,
        )
        return 200, _deliverable_queryset().get(id=deliverable.id)
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
        deliverable = _staff_deliverable_or_404(request, order, deliverable_id)
        if deliverable.status == "approved":
            return 400, {"detail": "Deliverable is already approved."}
        if deliverable.status == "superseded":
            return 400, {"detail": "Superseded deliverables cannot be approved."}
        deliverable.status = "approved"
        deliverable.approved_by = request.user
        deliverable.approved_at = timezone.now()
        deliverable.rejected_by = None
        deliverable.rejected_at = None
        deliverable.rejection_reason = ""
        deliverable.save()
        _log_order_activity(
            order,
            "deliverable_approved",
            f"Deliverable {deliverable.deliverable_number} approved.",
            created_by=request.user,
            visibility="internal_client" if deliverable.client_visible else "internal",
            next_action=order.next_action,
        )
        return 200, _deliverable_queryset().get(id=deliverable.id)
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
        deliverable = _staff_deliverable_or_404(request, order, deliverable_id)
        if deliverable.status == "rejected":
            return 400, {"detail": "Deliverable is already rejected."}
        if deliverable.status == "superseded":
            return 400, {"detail": "Superseded deliverables cannot be rejected."}
        deliverable.status = "rejected"
        deliverable.rejected_by = request.user
        deliverable.rejected_at = timezone.now()
        deliverable.rejection_reason = payload.reason or ""
        deliverable.save()
        _log_order_activity(
            order,
            "deliverable_rejected",
            f"Deliverable {deliverable.deliverable_number} rejected.",
            created_by=request.user,
            visibility="internal_client" if deliverable.client_visible else "internal",
            next_action=order.next_action,
        )
        return 200, _deliverable_queryset().get(id=deliverable.id)
    except (ValidationError, IntegrityError) as e:
        return 400, {"detail": _validation_detail(e)}


@router.delete(
    "/{order_id}/deliverables/{deliverable_id}",
    response={200: MessageSchema, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("orders", "update")
def delete_order_deliverable(request, order_id: int, deliverable_id: int):
    order = _staff_order_or_404(request, order_id)
    deliverable = _staff_deliverable_or_404(request, order, deliverable_id)
    if deliverable.status in {"approved", "rejected"}:
        return 400, {"detail": "Approved or rejected deliverables cannot be deleted."}
    deliverable.delete()
    _log_order_activity(
        order,
        "deliverable_added",
        f"Deliverable {deliverable.deliverable_number} deleted.",
        created_by=request.user,
        visibility="internal",
    )
    return 200, {"detail": "Deliverable deleted successfully"}


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
