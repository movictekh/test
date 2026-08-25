"""Service Operations catalogue application services."""

from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404

from domains.service_operations.models import (
    ServiceFieldType,
    ServicePricingConfig,
    ServicePricingField,
    ServiceRequestField,
    ServiceRequestForm,
    ServiceWorkflow,
    ServiceWorkflowStage,
)
from domains.organization.models.role import Role


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
        rows.append(
            ServiceRequestField(
                form=form,
                key=item_value(item, "key"),
                label=item_value(item, "label"),
                field_type=field_type,
                required=item_value(item, "required", False),
                options=item_value(item, "options", []),
                validation=item_value(item, "validation", {}),
                help_text=item_value(item, "help_text", "") or "",
                placeholder=item_value(item, "placeholder", "") or "",
                sort_order=item_value(item, "sort_order", index),
            )
        )
    ServiceRequestField.objects.bulk_create(rows)


def create_pricing_fields(config, fields):
    ensure_unique_keys(fields, "pricing field")
    rows = []
    valid_types = choice_values(ServiceFieldType.choices)
    for index, item in enumerate(fields):
        field_type = item_value(item, "field_type")
        if field_type not in valid_types:
            raise ValidationError({"field_type": f"Invalid field type: {field_type}."})
        rows.append(
            ServicePricingField(
                pricing_config=config,
                key=item_value(item, "key"),
                label=item_value(item, "label"),
                field_type=field_type,
                default_value=item_value(item, "default_value"),
                required=item_value(item, "required", False),
                options=item_value(item, "options", []),
                validation=item_value(item, "validation", {}),
                sort_order=item_value(item, "sort_order", index),
            )
        )
    ServicePricingField.objects.bulk_create(rows)


def create_workflow_stages(workflow, stages):
    rows = []
    for index, item in enumerate(stages):
        owner_role_id = item_value(item, "owner_role_id")
        if owner_role_id:
            get_object_or_404(Role, id=owner_role_id)
        rows.append(
            ServiceWorkflowStage(
                workflow=workflow,
                name=item_value(item, "name"),
                owner_role_id=owner_role_id,
                sla_days=item_value(item, "sla_days", 0),
                requires_approval=item_value(item, "requires_approval", False),
                requires_evidence=item_value(item, "requires_evidence", False),
                client_visible=item_value(item, "client_visible", False),
                sort_order=item_value(item, "sort_order", index),
            )
        )
    ServiceWorkflowStage.objects.bulk_create(rows)


def activate_request_form(service, form):
    with transaction.atomic():
        ServiceRequestForm.objects.filter(service=service, is_active=True).exclude(
            id=form.id
        ).update(is_active=False)
        form.status = "active"
        form.is_active = True
        form.save()
        service.active_request_form = form
        service.save(update_fields=["active_request_form", "updated_at"])


def activate_pricing_config(service, config):
    with transaction.atomic():
        ServicePricingConfig.objects.filter(service=service, is_active=True).exclude(
            id=config.id
        ).update(is_active=False)
        config.status = "active"
        config.is_active = True
        config.save()
        service.active_pricing_config = config
        service.save(update_fields=["active_pricing_config", "updated_at"])


def activate_workflow(service, workflow):
    with transaction.atomic():
        ServiceWorkflow.objects.filter(service=service, is_active=True).exclude(
            id=workflow.id
        ).update(is_active=False)
        workflow.status = "active"
        workflow.is_active = True
        workflow.save()
        service.active_workflow = workflow
        service.save(update_fields=["active_workflow", "updated_at"])


def create_workflow(service, payload, *, created_by_id):
    """Create a workflow, its stages, and optionally activate it atomically."""
    ensure_choice(payload.status, ServiceWorkflow.STATUS_CHOICES, "status")
    with transaction.atomic():
        workflow = ServiceWorkflow.objects.create(
            service=service,
            name=payload.name,
            version=payload.version,
            status=payload.status,
            is_active=False,
            created_by_id=created_by_id,
        )
        create_workflow_stages(workflow, payload.stages)
        if payload.is_active:
            activate_workflow(service, workflow)

    return (
        ServiceWorkflow.objects.select_related("service", "created_by")
        .prefetch_related("stages__owner_role")
        .get(id=workflow.id)
    )


def create_request_form(service, payload, *, created_by_id):
    ensure_choice(payload.status, ServiceRequestForm.STATUS_CHOICES, "status")
    with transaction.atomic():
        form = ServiceRequestForm.objects.create(
            service=service,
            name=payload.name,
            version=payload.version,
            status=payload.status,
            is_active=False,
            created_by_id=created_by_id,
        )
        create_request_fields(form, payload.fields)
        if payload.is_active:
            activate_request_form(service, form)
    return ServiceRequestForm.objects.prefetch_related("fields").get(id=form.id)


def update_request_form(form, payload):
    service = form.service
    data = payload.dict(exclude_unset=True)
    fields = data.pop("fields", None)
    if data.get("status"):
        ensure_choice(data["status"], ServiceRequestForm.STATUS_CHOICES, "status")
    with transaction.atomic():
        make_active = data.pop("is_active", None)
        for attr, value in data.items():
            setattr(form, attr, value)
        form.save()
        if fields is not None:
            form.fields.all().delete()
            create_request_fields(form, fields)
        if make_active is True:
            activate_request_form(service, form)
        elif make_active is False and form.is_active:
            form.is_active = False
            form.save(update_fields=["is_active", "updated_at"])
            if service.active_request_form_id == form.id:
                service.active_request_form = None
                service.save(update_fields=["active_request_form", "updated_at"])
    return ServiceRequestForm.objects.prefetch_related("fields").get(id=form.id)


def delete_request_form(form):
    service = form.service
    if form.status == "draft" and not form.is_active:
        form.delete()
        return "deleted"
    with transaction.atomic():
        form.status = "archived"
        form.is_active = False
        form.save(update_fields=["status", "is_active", "updated_at"])
        if service.active_request_form_id == form.id:
            service.active_request_form = None
            service.save(update_fields=["active_request_form", "updated_at"])
    return "archived"


def create_pricing_config(service, payload, *, created_by_id):
    ensure_choice(payload.status, ServicePricingConfig.STATUS_CHOICES, "status")
    ensure_choice(
        payload.pricing_type, ServicePricingConfig.PRICING_TYPE_CHOICES, "pricing_type"
    )
    with transaction.atomic():
        config = ServicePricingConfig.objects.create(
            service=service,
            name=payload.name,
            version=payload.version,
            pricing_type=payload.pricing_type,
            formula=payload.formula or "",
            tax_rate=payload.tax_rate,
            deposit_percent=payload.deposit_percent,
            discount_approval_threshold_percent=payload.discount_approval_threshold_percent,
            status=payload.status,
            is_active=False,
            created_by_id=created_by_id,
        )
        create_pricing_fields(config, payload.fields)
        if payload.is_active:
            activate_pricing_config(service, config)
    return (
        ServicePricingConfig.objects.select_related("service")
        .prefetch_related("fields")
        .get(id=config.id)
    )


def update_pricing_config(config, payload):
    service = config.service
    data = payload.dict(exclude_unset=True)
    fields = data.pop("fields", None)
    if data.get("status"):
        ensure_choice(data["status"], ServicePricingConfig.STATUS_CHOICES, "status")
    if data.get("pricing_type"):
        ensure_choice(
            data["pricing_type"],
            ServicePricingConfig.PRICING_TYPE_CHOICES,
            "pricing_type",
        )
    with transaction.atomic():
        make_active = data.pop("is_active", None)
        for attr, value in data.items():
            setattr(config, attr, value)
        config.save()
        if fields is not None:
            config.fields.all().delete()
            create_pricing_fields(config, fields)
        if make_active is True:
            activate_pricing_config(service, config)
        elif make_active is False and config.is_active:
            config.is_active = False
            config.save(update_fields=["is_active", "updated_at"])
            if service.active_pricing_config_id == config.id:
                service.active_pricing_config = None
                service.save(update_fields=["active_pricing_config", "updated_at"])
    return (
        ServicePricingConfig.objects.select_related("service")
        .prefetch_related("fields")
        .get(id=config.id)
    )


def delete_pricing_config(config):
    service = config.service
    if config.status == "draft" and not config.is_active:
        config.delete()
        return "deleted"
    with transaction.atomic():
        config.status = "archived"
        config.is_active = False
        config.save(update_fields=["status", "is_active", "updated_at"])
        if service.active_pricing_config_id == config.id:
            service.active_pricing_config = None
            service.save(update_fields=["active_pricing_config", "updated_at"])
    return "archived"


def update_workflow(workflow, payload):
    service = workflow.service
    data = payload.dict(exclude_unset=True)
    stages = data.pop("stages", None)
    if data.get("status"):
        ensure_choice(data["status"], ServiceWorkflow.STATUS_CHOICES, "status")
    with transaction.atomic():
        make_active = data.pop("is_active", None)
        for attr, value in data.items():
            setattr(workflow, attr, value)
        workflow.save()
        if stages is not None:
            workflow.stages.all().delete()
            create_workflow_stages(workflow, stages)
        if make_active is True:
            activate_workflow(service, workflow)
        elif make_active is False and workflow.is_active:
            workflow.is_active = False
            workflow.save(update_fields=["is_active", "updated_at"])
            if service.active_workflow_id == workflow.id:
                service.active_workflow = None
                service.save(update_fields=["active_workflow", "updated_at"])
    return (
        ServiceWorkflow.objects.select_related("service", "created_by")
        .prefetch_related("stages__owner_role")
        .get(id=workflow.id)
    )


def delete_workflow(workflow):
    service = workflow.service
    with transaction.atomic():
        if workflow.status == "draft" and not workflow.is_active:
            workflow.delete()
            return "deleted"
        workflow.status = "archived"
        workflow.is_active = False
        workflow.save(update_fields=["status", "is_active", "updated_at"])
        if service.active_workflow_id == workflow.id:
            service.active_workflow = None
            service.save(update_fields=["active_workflow", "updated_at"])
    return "archived"


def replace_workflow_stages(workflow, stages):
    with transaction.atomic():
        workflow.stages.all().delete()
        create_workflow_stages(workflow, stages)
    return ServiceWorkflowStage.objects.filter(workflow=workflow).select_related(
        "owner_role"
    )
