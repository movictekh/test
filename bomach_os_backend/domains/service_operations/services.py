"""State-changing catalogue/configuration operations for Service Operations."""
from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404
from services.models.service import (
    ServiceFieldType, ServicePricingConfig, ServicePricingField,
    ServiceRequestField, ServiceRequestForm, ServiceWorkflow,
    ServiceWorkflowStage,    ServiceOrder,
    ServiceOrderActivity,

)
from user.models.role import Role

def choice_values(choices):
    return {choice[0] for choice in choices}

def ensure_choice(value, choices, field_name):
    if value not in choice_values(choices):
        raise ValidationError({field_name: f"Invalid {field_name}: {value}."})

def item_value(item, key, default=None):
    if isinstance(item, dict):
        return item.get(key, default)
    return getattr(item, key, default)

def ensure_unique_keys(items, label):
    seen = set()
    for item in items:
        key = item_value(item, "key")
        if key in seen:
            raise ValidationError({"key": f"Duplicate {label} key: {key}."})
        seen.add(key)

def create_request_fields(form, fields):
    ensure_unique_keys(fields, "request field")
    rows = []
    valid_types = choice_values(ServiceFieldType.choices)
    for index, item in enumerate(fields):
        field_type = item_value(item, "field_type")
        if field_type not in valid_types:
            raise ValidationError({"field_type": f"Invalid field type: {field_type}."})
        rows.append(ServiceRequestField(
            form=form, key=item_value(item, "key"), label=item_value(item, "label"),
            field_type=field_type, required=item_value(item, "required", False),
            options=item_value(item, "options", []), validation=item_value(item, "validation", {}),
            help_text=item_value(item, "help_text", "") or "",
            placeholder=item_value(item, "placeholder", "") or "",
            sort_order=item_value(item, "sort_order", index),
        ))
    ServiceRequestField.objects.bulk_create(rows)

def create_pricing_fields(config, fields):
    ensure_unique_keys(fields, "pricing field")
    rows = []
    valid_types = choice_values(ServiceFieldType.choices)
    for index, item in enumerate(fields):
        field_type = item_value(item, "field_type")
        if field_type not in valid_types:
            raise ValidationError({"field_type": f"Invalid field type: {field_type}."})
        rows.append(ServicePricingField(
            pricing_config=config, key=item_value(item, "key"), label=item_value(item, "label"),
            field_type=field_type, default_value=item_value(item, "default_value"),
            required=item_value(item, "required", False), options=item_value(item, "options", []),
            validation=item_value(item, "validation", {}), sort_order=item_value(item, "sort_order", index),
        ))
    ServicePricingField.objects.bulk_create(rows)

def create_workflow_stages(workflow, stages):
    rows = []
    for index, item in enumerate(stages):
        owner_role_id = item_value(item, "owner_role_id")
        if owner_role_id:
            get_object_or_404(Role, id=owner_role_id)
        rows.append(ServiceWorkflowStage(
            workflow=workflow, name=item_value(item, "name"), owner_role_id=owner_role_id,
            sla_days=item_value(item, "sla_days", 0),
            requires_approval=item_value(item, "requires_approval", False),
            requires_evidence=item_value(item, "requires_evidence", False),
            client_visible=item_value(item, "client_visible", False),
            sort_order=item_value(item, "sort_order", index),
        ))
    ServiceWorkflowStage.objects.bulk_create(rows)

def activate_request_form(service, form):
    ServiceRequestForm.objects.filter(service=service, is_active=True).exclude(id=form.id).update(is_active=False)
    form.status = "active"
    form.is_active = True
    form.save()
    service.active_request_form = form
    service.save(update_fields=["active_request_form", "updated_at"])

def activate_pricing_config(service, config):
    ServicePricingConfig.objects.filter(service=service, is_active=True).exclude(id=config.id).update(is_active=False)
    config.status = "active"
    config.is_active = True
    config.save()
    service.active_pricing_config = config
    service.save(update_fields=["active_pricing_config", "updated_at"])

def activate_workflow(service, workflow):
    ServiceWorkflow.objects.filter(service=service, is_active=True).exclude(id=workflow.id).update(is_active=False)
    workflow.status = "active"
    workflow.is_active = True
    workflow.save()
    service.active_workflow = workflow
    service.save(update_fields=["active_workflow", "updated_at"])


def create_order_from_invoice(invoice, created_by, assigned_to_id=None, due_date=None, description="", stage="", next_action="Confirm team and mobilisation"):
    if not invoice.activation_threshold_met_at:
        raise ValidationError("Payment threshold must be met before creating a service order.")
    if ServiceOrder.objects.filter(invoice=invoice).exists() or invoice.order_id:
        raise ValidationError("This invoice already has a service order.")

    with transaction.atomic():
        invoice = invoice.__class__.objects.select_for_update().get(id=invoice.id)
        if not invoice.activation_threshold_met_at:
            raise ValidationError("Payment threshold must be met before creating a service order.")
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
            invoice.service_request.save(update_fields=["status", "next_action", "updated_at"])

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
