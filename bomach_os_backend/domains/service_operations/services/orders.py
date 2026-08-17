"""Service Operations orders application services."""

from django.core.exceptions import ValidationError
from django.db import transaction

from domains.service_operations.models import ServiceOrder, ServiceOrderActivity


def create_order_from_invoice(
    invoice,
    created_by,
    assigned_to_id=None,
    due_date=None,
    description="",
    stage="",
    next_action="Confirm team and mobilisation",
):
    if not invoice.activation_threshold_met_at:
        raise ValidationError(
            "Payment threshold must be met before creating a service order."
        )
    if ServiceOrder.objects.filter(invoice=invoice).exists() or invoice.order_id:
        raise ValidationError("This invoice already has a service order.")

    with transaction.atomic():
        invoice = invoice.__class__.objects.select_for_update().get(id=invoice.id)
        if not invoice.activation_threshold_met_at:
            raise ValidationError(
                "Payment threshold must be met before creating a service order."
            )
        if ServiceOrder.objects.filter(invoice=invoice).exists() or invoice.order_id:
            raise ValidationError("This invoice already has a service order.")

        order = ServiceOrder.objects.create(
            client=invoice.client,
            service=invoice.service,
            quote=invoice.quote,
            service_request=invoice.service_request,
            invoice=invoice,
            description=description or invoice.notes or invoice.service.name,
            amount=invoice.total_amount,
            order_status="pending_mobilisation",
            payment_status="paid" if invoice.status == "paid" else "partial",
            valid_until=due_date or invoice.due_date,
            due_date=due_date or invoice.due_date,
            stage=stage,
            next_action=next_action,
            created_by=created_by,
            assigned_to_id=assigned_to_id,
            branch=invoice.service_request.branch if invoice.service_request else None,
        )
        order.seed_milestones()
        ServiceOrderActivity.objects.create(
            order=order,
            activity_type="order_created",
            visibility="internal_client",
            note=f"Service order created from invoice {invoice.invoice_number}.",
            next_action=order.next_action,
            created_by=created_by,
        )
        invoice.order = order
        invoice.save(update_fields=["order", "updated_at"])

        if invoice.service_request:
            invoice.service_request.status = "converted"
            invoice.service_request.next_action = f"Track {order.order_number}"
            invoice.service_request.save(
                update_fields=["status", "next_action", "updated_at"]
            )

    return order


def create_manual_order(payload_data, created_by):
    with transaction.atomic():
        payload_data.setdefault("created_by_id", created_by.id)
        order = ServiceOrder.objects.create(**payload_data)
        order.seed_milestones()
        ServiceOrderActivity.objects.create(
            order=order,
            activity_type="order_created",
            visibility="internal",
            note="Manual service order created.",
            next_action=order.next_action,
            created_by=created_by,
        )
        return order


def _choice_values(choices):
    return {choice[0] for choice in choices}


def _ensure_choice(value, choices, field_name):
    if value and value not in _choice_values(choices):
        raise ValidationError({field_name: f"Invalid {field_name}: {value}."})


def log_order_activity(
    order,
    activity_type,
    note,
    *,
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


def update_order(order, payload, *, user):
    data = payload.dict(exclude_unset=True)
    if "invoice_id" in data and data["invoice_id"] != order.invoice_id:
        raise ValidationError(
            "Invoice links cannot be changed from the order update endpoint."
        )
    _ensure_choice(
        data.get("order_status"), ServiceOrder.ORDER_STATUS_CHOICES, "order_status"
    )
    old_status = order.order_status
    with transaction.atomic():
        for attr, value in data.items():
            if attr != "invoice_id":
                setattr(order, attr, value)
        order.save()
        log_order_activity(
            order,
            "control_update",
            f"Service order updated. Status: {order.order_status}; progress: {order.progress}%.",
            progress=order.progress,
            next_action=order.next_action,
            created_by=user,
        )
        if old_status != order.order_status and order.service_request_id:
            order.service_request.next_action = (
                order.next_action or f"Track {order.order_number}"
            )
            order.service_request.save(update_fields=["next_action", "updated_at"])
    return order


def create_order_activity(order, payload, *, user):
    _ensure_choice(
        payload.activity_type,
        ServiceOrderActivity.ACTIVITY_TYPE_CHOICES,
        "activity_type",
    )
    _ensure_choice(
        payload.visibility, ServiceOrderActivity.VISIBILITY_CHOICES, "visibility"
    )
    data = payload.dict(exclude_unset=True)
    with transaction.atomic():
        if "progress" in data:
            order.progress = data["progress"]
        if "next_action" in data:
            order.next_action = data["next_action"] or ""
        order.save()
        return log_order_activity(
            order,
            payload.activity_type,
            payload.note,
            visibility=payload.visibility,
            progress=data.get("progress"),
            next_action=data.get("next_action") or "",
            created_by=user,
        )


def create_order_milestone(order, payload, *, user):
    from domains.service_operations.models import ServiceOrderMilestone

    _ensure_choice(payload.status, ServiceOrderMilestone.STATUS_CHOICES, "status")
    with transaction.atomic():
        milestone = ServiceOrderMilestone.objects.create(order=order, **payload.dict())
        log_order_activity(
            order,
            "milestone_added",
            f"Milestone added: {milestone.name}.",
            visibility="internal_client" if milestone.client_visible else "internal",
            created_by=user,
        )
    return milestone


def complete_order_milestone(order, milestone_id, *, user):
    from django.shortcuts import get_object_or_404
    from django.utils import timezone

    from domains.service_operations.models import ServiceOrderMilestone

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
                order.save(update_fields=["order_status", "started_at", "updated_at"])
        order.refresh_progress_from_milestones()
        log_order_activity(
            order,
            "stage_advanced",
            f"Milestone completed: {milestone.name}.",
            visibility="internal_client" if milestone.client_visible else "internal",
            progress=order.progress,
            next_action=order.next_action,
            created_by=user,
        )
    return order


def reopen_order_milestone(order, milestone_id, *, user):
    from django.shortcuts import get_object_or_404

    from domains.service_operations.models import ServiceOrderMilestone

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
        log_order_activity(
            order,
            "milestone_reopened",
            f"Milestone reopened: {milestone.name}.",
            visibility="internal_client" if milestone.client_visible else "internal",
            progress=order.progress,
            next_action=order.next_action,
            created_by=user,
        )
    return order


def create_order_task(order, payload, *, user):
    from domains.service_operations.models import ServiceExecutionTask

    data = payload.dict(exclude_unset=True)
    assignee_ids = data.pop("assignee_ids", [])
    _ensure_choice(data.get("status"), ServiceExecutionTask.STATUS_CHOICES, "status")
    _ensure_choice(
        data.get("priority"), ServiceExecutionTask.PRIORITY_CHOICES, "priority"
    )
    with transaction.atomic():
        task = ServiceExecutionTask.objects.create(order=order, created_by=user, **data)
        task.assignees.set(assignee_ids)
        log_order_activity(
            order,
            "task_created",
            f"Execution task {task.task_number} created: {task.title}.",
            created_by=user,
            next_action=order.next_action,
        )
    return task


def update_order_task(order, task, payload, *, user):
    from domains.service_operations.models import ServiceExecutionTask

    supplied = payload.dict(exclude_unset=True)
    data = dict(supplied)
    assignee_ids = data.pop("assignee_ids", [])
    _ensure_choice(data.get("status"), ServiceExecutionTask.STATUS_CHOICES, "status")
    _ensure_choice(
        data.get("priority"), ServiceExecutionTask.PRIORITY_CHOICES, "priority"
    )
    with transaction.atomic():
        for attr, value in data.items():
            setattr(task, attr, value)
        task.save()
        if "assignee_ids" in supplied:
            task.assignees.set(assignee_ids)
        log_order_activity(
            order,
            "task_updated",
            f"Execution task {task.task_number} updated. Status: {task.status}.",
            created_by=user,
            next_action=order.next_action,
        )
    return task


def advance_order_task(order, task, *, user):
    transitions = {"to_do": "in_progress", "in_progress": "review", "review": "done"}
    if task.status not in transitions:
        raise ValidationError("Task cannot be advanced from its current status.")
    with transaction.atomic():
        task.status = transitions[task.status]
        task.save()
        log_order_activity(
            order,
            "task_advanced",
            f"Execution task {task.task_number} advanced to {task.status}.",
            created_by=user,
            next_action=order.next_action,
        )
    return task


def delete_order_task(order, task, *, user):
    number = task.task_number
    with transaction.atomic():
        task.delete()
        log_order_activity(
            order,
            "task_updated",
            f"Execution task {number} deleted.",
            created_by=user,
            visibility="internal",
        )


def _deliverable_data(payload):
    data = payload.dict(exclude_unset=True)
    if "status" not in data or data["status"] is None:
        data["status"] = (
            "approved"
            if data.get("approval_mode", "none") == "none"
            else "under_review"
        )
    return data


def create_order_deliverable(order, payload, *, user):
    from domains.service_operations.models import ServiceDeliverable

    data = _deliverable_data(payload)
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
    with transaction.atomic():
        obj = ServiceDeliverable.objects.create(order=order, created_by=user, **data)
        log_order_activity(
            order,
            "deliverable_added",
            f"Deliverable {obj.deliverable_number} added: {obj.title}.",
            created_by=user,
            visibility="internal_client" if obj.client_visible else "internal",
            next_action=order.next_action,
        )
    return obj


def update_order_deliverable(order, obj, payload, *, user):
    from domains.service_operations.models import ServiceDeliverable

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
    with transaction.atomic():
        for attr, value in data.items():
            setattr(obj, attr, value)
        obj.save()
        log_order_activity(
            order,
            "deliverable_added",
            f"Deliverable {obj.deliverable_number} updated. Status: {obj.status}.",
            created_by=user,
            visibility="internal_client" if obj.client_visible else "internal",
            next_action=order.next_action,
        )
    return obj


def approve_order_deliverable(order, obj, *, user, client_mode=False):
    from django.utils import timezone

    if client_mode and obj.approval_mode != "client":
        raise ValidationError("This deliverable does not require client approval.")
    if client_mode and obj.status != "under_review":
        raise ValidationError("Only deliverables under review can be approved.")
    if not client_mode and obj.status == "approved":
        raise ValidationError("Deliverable is already approved.")
    if obj.status == "superseded":
        raise ValidationError("Superseded deliverables cannot be approved.")
    with transaction.atomic():
        obj.status = "approved"
        obj.approved_by = user
        obj.approved_at = timezone.now()
        obj.rejected_by = None
        obj.rejected_at = None
        obj.rejection_reason = ""
        obj.save()
        note = (
            f"Client approved deliverable {obj.deliverable_number}."
            if client_mode
            else f"Deliverable {obj.deliverable_number} approved."
        )
        log_order_activity(
            order,
            "deliverable_approved",
            note,
            created_by=user,
            visibility="internal_client" if obj.client_visible else "internal",
            next_action="" if client_mode else order.next_action,
        )
    return obj


def reject_order_deliverable(order, obj, *, reason, user, client_mode=False):
    from django.utils import timezone

    if client_mode and obj.approval_mode != "client":
        raise ValidationError("This deliverable does not require client approval.")
    if client_mode and obj.status != "under_review":
        raise ValidationError("Only deliverables under review can be rejected.")
    if not client_mode and obj.status == "rejected":
        raise ValidationError("Deliverable is already rejected.")
    if obj.status == "superseded":
        raise ValidationError("Superseded deliverables cannot be rejected.")
    with transaction.atomic():
        obj.status = "rejected"
        obj.rejected_by = user
        obj.rejected_at = timezone.now()
        obj.rejection_reason = reason or ""
        obj.save()
        note = (
            f"Client rejected deliverable {obj.deliverable_number}."
            if client_mode
            else f"Deliverable {obj.deliverable_number} rejected."
        )
        log_order_activity(
            order,
            "deliverable_rejected",
            note,
            created_by=user,
            visibility="internal_client" if obj.client_visible else "internal",
            next_action="" if client_mode else order.next_action,
        )
    return obj


def delete_order_deliverable(order, obj, *, user):
    if obj.status in {"approved", "rejected"}:
        raise ValidationError("Approved or rejected deliverables cannot be deleted.")
    number = obj.deliverable_number
    with transaction.atomic():
        obj.delete()
        log_order_activity(
            order,
            "deliverable_added",
            f"Deliverable {number} deleted.",
            created_by=user,
            visibility="internal",
        )
