"""Private shared support for Service Catalogue v1 routers.

Contains transport serialization/query helpers only; no HTTP endpoints.
"""

from domains.service_operations.models import ServiceWorkflow


def _validation_detail(exc):
    if hasattr(exc, "message_dict"):
        return "; ".join(
            f"{field}: {', '.join(messages)}"
            for field, messages in exc.message_dict.items()
        )
    return exc.messages[0] if getattr(exc, "messages", None) else str(exc)


def _current_user_id(request, explicit_user_id=None):
    return explicit_user_id or request.user.id


def _category_name(service):
    return service.category.get_name_display() if service.category_id else ""


def _role_name(role):
    return role.name if role else ""


def _serialize_subservice(subservice):
    return {
        "id": subservice.id,
        "service_id": subservice.service_id,
        "code": subservice.code,
        "name": subservice.name,
        "description": subservice.description,
        "status": subservice.status,
        "default_sla_days": subservice.default_sla_days,
        "sort_order": subservice.sort_order,
        "created_at": subservice.created_at,
        "updated_at": subservice.updated_at,
    }


def _serialize_request_field(field):
    return {
        "id": field.id,
        "form_id": field.form_id,
        "key": field.key,
        "label": field.label,
        "field_type": field.field_type,
        "required": field.required,
        "options": field.options,
        "validation": field.validation,
        "help_text": field.help_text,
        "placeholder": field.placeholder,
        "sort_order": field.sort_order,
    }


def _serialize_request_form(form, include_fields=True):
    row = {
        "id": form.id,
        "service_id": form.service_id,
        "name": form.name,
        "version": form.version,
        "status": form.status,
        "is_active": form.is_active,
        "field_count": form.fields.count(),
        "created_by_id": form.created_by_id,
        "created_at": form.created_at,
        "updated_at": form.updated_at,
    }
    if include_fields:
        row["fields"] = [_serialize_request_field(field) for field in form.fields.all()]
    return row


def _serialize_pricing_field(field):
    return {
        "id": field.id,
        "pricing_config_id": field.pricing_config_id,
        "key": field.key,
        "label": field.label,
        "field_type": field.field_type,
        "default_value": field.default_value,
        "required": field.required,
        "options": field.options,
        "validation": field.validation,
        "sort_order": field.sort_order,
    }


def _serialize_pricing_config(config, include_fields=True):
    row = {
        "id": config.id,
        "service_id": config.service_id,
        "service_name": config.service.name if getattr(config, "service", None) else "",
        "name": config.name,
        "version": config.version,
        "pricing_type": config.pricing_type,
        "formula": config.formula,
        "tax_rate": config.tax_rate,
        "deposit_percent": config.deposit_percent,
        "discount_approval_threshold_percent": config.discount_approval_threshold_percent,
        "status": config.status,
        "is_active": config.is_active,
        "field_count": config.fields.count(),
        "created_by_id": config.created_by_id,
        "created_at": config.created_at,
        "updated_at": config.updated_at,
    }
    if include_fields:
        row["fields"] = [
            _serialize_pricing_field(field) for field in config.fields.all()
        ]
    return row


def _serialize_workflow_stage(stage):
    return {
        "id": stage.id,
        "workflow_id": stage.workflow_id,
        "name": stage.name,
        "owner_role_id": stage.owner_role_id,
        "owner_role_name": _role_name(stage.owner_role),
        "sla_days": stage.sla_days,
        "requires_approval": stage.requires_approval,
        "requires_evidence": stage.requires_evidence,
        "client_visible": stage.client_visible,
        "sort_order": stage.sort_order,
    }


def _serialize_workflow(workflow, include_stages=True):
    row = {
        "id": workflow.id,
        "service_id": workflow.service_id,
        "name": workflow.name,
        "version": workflow.version,
        "status": workflow.status,
        "is_active": workflow.is_active,
        "stage_count": workflow.stages.count(),
        "created_by_id": workflow.created_by_id,
        "created_at": workflow.created_at,
        "updated_at": workflow.updated_at,
    }
    if include_stages:
        row["stages"] = [
            _serialize_workflow_stage(stage) for stage in workflow.stages.all()
        ]
    return row


def _serialize_branch_activation(activation):
    branch = activation.branch
    return {
        "id": activation.id,
        "service_id": activation.service_id,
        "branch_id": activation.branch_id,
        "branch_name": branch.branch_name if branch else "",
        "status": activation.status,
        "client_visible": activation.client_visible,
        "capacity": activation.capacity,
        "activated_at": activation.activated_at,
        "created_at": activation.created_at,
        "updated_at": activation.updated_at,
    }


def _serialize_service_core(service):
    return {
        "id": service.id,
        "code": service.code,
        "name": service.name,
        "category_id": service.category_id,
        "category_name": _category_name(service),
        "division": service.division,
        "description": service.description,
        "base_price": service.base_price,
        "delivery_time": service.delivery_time,
        "status": service.status,
        "owner_role_id": service.owner_role_id,
        "owner_role_name": _role_name(service.owner_role),
        "default_sla_days": service.default_sla_days,
        "fulfillment_mode": service.fulfillment_mode,
        "client_visibility": service.client_visibility,
        "active_request_form_id": service.active_request_form_id,
        "active_pricing_config_id": service.active_pricing_config_id,
        "active_workflow_id": service.active_workflow_id,
        "subservice_count": service.subservices.count(),
        "branch_activation_count": service.branch_activations.count(),
        "created_at": service.created_at,
        "updated_at": service.updated_at,
        "created_by_id": service.created_by_id,
    }


def _serialize_catalogue_card(service):
    row = _serialize_service_core(service)
    row.update(
        {
            "active_request_form": (
                _serialize_request_form(
                    service.active_request_form, include_fields=False
                )
                if service.active_request_form
                else None
            ),
            "active_pricing_config": (
                _serialize_pricing_config(
                    service.active_pricing_config, include_fields=False
                )
                if service.active_pricing_config
                else None
            ),
            "active_workflow": (
                _serialize_workflow(service.active_workflow, include_stages=False)
                if service.active_workflow
                else None
            ),
            "active_branches": [
                _serialize_branch_activation(activation)
                for activation in service.branch_activations.all()
                if activation.status == "active"
            ],
        }
    )
    return row


def _serialize_catalogue_detail(service):
    row = _serialize_catalogue_card(service)
    row.update(
        {
            "subservices": [
                _serialize_subservice(item) for item in service.subservices.all()
            ],
            "request_forms": [
                _serialize_request_form(form, include_fields=True)
                for form in service.request_forms.all()
            ],
            "pricing_configs": [
                _serialize_pricing_config(config, include_fields=True)
                for config in service.pricing_configs.all()
            ],
            "workflows": [
                _serialize_workflow(workflow, include_stages=True)
                for workflow in service.workflows.all()
            ],
            "branch_activations": [
                _serialize_branch_activation(activation)
                for activation in service.branch_activations.all()
            ],
        }
    )
    return row


def _workflow_queryset():
    return ServiceWorkflow.objects.select_related(
        "service", "created_by"
    ).prefetch_related("stages__owner_role")
