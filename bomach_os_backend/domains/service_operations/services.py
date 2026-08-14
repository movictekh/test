"""State-changing catalogue/configuration operations for Service Operations."""
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from services.models.service import (
    ServiceFieldType, ServicePricingConfig, ServicePricingField,
    ServiceRequestField, ServiceRequestForm, ServiceWorkflow,
    ServiceWorkflowStage,
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
