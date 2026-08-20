from django.core.exceptions import ValidationError
from django.db import transaction

from services.models.service import ServiceOrder, ServiceOrderActivity


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
