"""Service request-form, pricing and workflow configuration endpoints."""

from typing import Any, Dict, List
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db.models import Q
from django.shortcuts import get_object_or_404
from ninja import Router
from ninja.pagination import LimitOffsetPagination, paginate
from domains.service_operations.services import catalogue as domain_services
from services.api.schema.others import MessageSchema
from ..schemas.catalogue import FieldTypeOut, PricingConfigIn, PricingConfigUpdate, RequestFormIn, RequestFormUpdate, WorkflowIn, WorkflowSeedIn, WorkflowStageBulkReplace, WorkflowStageIn, WorkflowStageUpdate, WorkflowUpdate
from domains.service_operations.models import Service, ServiceFieldType, ServicePricingConfig, ServiceRequestForm, ServiceWorkflow, ServiceWorkflowStage
from user.models.role import Role
from user.utils.perm import require_permission
from ._catalogue_support import (
    _current_user_id,
    _serialize_pricing_config,
    _serialize_request_form,
    _serialize_workflow,
    _serialize_workflow_stage,
    _validation_detail,
    _workflow_queryset,
)


router = Router(tags=["Services"])


@router.get("/request-field-types", response=List[FieldTypeOut], operation_id="services_api_v1_services_list_request_field_types")
@require_permission("service_request_forms", "list")
def list_request_field_types(request):
    option_types = {"select", "multiselect", "checkbox"}
    return [
        {
            "value": value,
            "label": label,
            "supports_options": value in option_types,
            "supports_validation": value not in {"checkbox"},
        }
        for value, label in ServiceFieldType.choices
    ]


@router.get("/pricing-configs", response=List[Dict[str, Any]], operation_id="services_api_v1_services_list_pricing_configs")
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("service_pricing_configs", "list")
def list_pricing_configs(request, service_id: int = None, status: str = None, pricing_type: str = None, search: str = None):
    configs = ServicePricingConfig.objects.select_related("service", "created_by").prefetch_related("fields").all()
    if service_id:
        configs = configs.filter(service_id=service_id)
    if status:
        configs = configs.filter(status=status)
    if pricing_type:
        configs = configs.filter(pricing_type=pricing_type)
    if search:
        configs = configs.filter(
            Q(name__icontains=search)
            | Q(formula__icontains=search)
            | Q(service__name__icontains=search)
        )
    return [_serialize_pricing_config(config, include_fields=False) for config in configs]


@router.get("/{service_id}/request-forms", response=List[Dict[str, Any]], operation_id="services_api_v1_services_list_request_forms")
@require_permission("service_request_forms", "list")
def list_request_forms(request, service_id: int):
    get_object_or_404(Service, id=service_id)
    forms = ServiceRequestForm.objects.filter(service_id=service_id).prefetch_related("fields")
    return [_serialize_request_form(form) for form in forms]


@router.post("/{service_id}/request-forms", response={201: Dict[str, Any], 400: MessageSchema}, operation_id="services_api_v1_services_create_request_form")
@require_permission("service_request_forms", "create")
def create_request_form(request, service_id: int, payload: RequestFormIn):
    try:
        service = get_object_or_404(Service, id=service_id)
        form = domain_services.create_request_form(service, payload, created_by_id=_current_user_id(request, payload.created_by_id))
        return 201, _serialize_request_form(form)
    except (ValidationError, IntegrityError) as e:
        return 400, {"detail": _validation_detail(e)}


@router.get("/{service_id}/request-forms/{form_id}", response=Dict[str, Any], operation_id="services_api_v1_services_get_request_form")
@require_permission("service_request_forms", "view")
def get_request_form(request, service_id: int, form_id: int):
    form = get_object_or_404(ServiceRequestForm.objects.prefetch_related("fields"), id=form_id, service_id=service_id)
    return _serialize_request_form(form)


@router.put("/{service_id}/request-forms/{form_id}", response={200: Dict[str, Any], 400: MessageSchema, 404: MessageSchema}, operation_id="services_api_v1_services_update_request_form")
@require_permission("service_request_forms", "update")
def update_request_form(request, service_id: int, form_id: int, payload: RequestFormUpdate):
    try:
        form = get_object_or_404(ServiceRequestForm, id=form_id, service_id=service_id)
        return 200, _serialize_request_form(domain_services.update_request_form(form, payload))
    except (ValidationError, IntegrityError) as e:
        return 400, {"detail": _validation_detail(e)}


@router.delete("/{service_id}/request-forms/{form_id}", response={200: MessageSchema, 404: MessageSchema}, operation_id="services_api_v1_services_delete_request_form")
@require_permission("service_request_forms", "delete")
def delete_request_form(request, service_id: int, form_id: int):
    form = get_object_or_404(ServiceRequestForm, id=form_id, service_id=service_id)
    outcome = domain_services.delete_request_form(form)
    return 200, {"detail": "Request form deleted successfully" if outcome == "deleted" else "Request form archived successfully"}


@router.post("/{service_id}/request-forms/{form_id}/activate", response={200: Dict[str, Any], 404: MessageSchema}, operation_id="services_api_v1_services_activate_request_form")
@require_permission("service_request_forms", "update")
def activate_request_form(request, service_id: int, form_id: int):
    service = get_object_or_404(Service, id=service_id)
    form = get_object_or_404(ServiceRequestForm.objects.prefetch_related("fields"), id=form_id, service=service)
    domain_services.activate_request_form(service, form)
    form.refresh_from_db()
    return 200, _serialize_request_form(form)


@router.post("/{service_id}/pricing-configs", response={201: Dict[str, Any], 400: MessageSchema}, operation_id="services_api_v1_services_create_pricing_config")
@require_permission("service_pricing_configs", "create")
def create_pricing_config(request, service_id: int, payload: PricingConfigIn):
    try:
        service = get_object_or_404(Service, id=service_id)
        config = domain_services.create_pricing_config(service, payload, created_by_id=_current_user_id(request, payload.created_by_id))
        return 201, _serialize_pricing_config(config)
    except (ValidationError, IntegrityError) as e:
        return 400, {"detail": _validation_detail(e)}


@router.get("/{service_id}/pricing-configs/{config_id}", response=Dict[str, Any], operation_id="services_api_v1_services_get_pricing_config")
@require_permission("service_pricing_configs", "view")
def get_pricing_config(request, service_id: int, config_id: int):
    config = get_object_or_404(
        ServicePricingConfig.objects.select_related("service").prefetch_related("fields"),
        id=config_id,
        service_id=service_id,
    )
    return _serialize_pricing_config(config)


@router.put("/{service_id}/pricing-configs/{config_id}", response={200: Dict[str, Any], 400: MessageSchema, 404: MessageSchema}, operation_id="services_api_v1_services_update_pricing_config")
@require_permission("service_pricing_configs", "update")
def update_pricing_config(request, service_id: int, config_id: int, payload: PricingConfigUpdate):
    try:
        config = get_object_or_404(ServicePricingConfig, id=config_id, service_id=service_id)
        return 200, _serialize_pricing_config(domain_services.update_pricing_config(config, payload))
    except (ValidationError, IntegrityError) as e:
        return 400, {"detail": _validation_detail(e)}


@router.delete("/{service_id}/pricing-configs/{config_id}", response={200: MessageSchema, 404: MessageSchema}, operation_id="services_api_v1_services_delete_pricing_config")
@require_permission("service_pricing_configs", "delete")
def delete_pricing_config(request, service_id: int, config_id: int):
    config = get_object_or_404(ServicePricingConfig, id=config_id, service_id=service_id)
    outcome = domain_services.delete_pricing_config(config)
    return 200, {"detail": "Pricing config deleted successfully" if outcome == "deleted" else "Pricing config archived successfully"}


@router.post("/{service_id}/pricing-configs/{config_id}/activate", response={200: Dict[str, Any], 404: MessageSchema}, operation_id="services_api_v1_services_activate_pricing_config")
@require_permission("service_pricing_configs", "update")
def activate_pricing_config(request, service_id: int, config_id: int):
    service = get_object_or_404(Service, id=service_id)
    config = get_object_or_404(ServicePricingConfig.objects.select_related("service").prefetch_related("fields"), id=config_id, service=service)
    domain_services.activate_pricing_config(service, config)
    config.refresh_from_db()
    return 200, _serialize_pricing_config(config)


@router.get("/{service_id}/workflows", response=List[Dict[str, Any]], operation_id="services_api_v1_services_list_workflows")
@require_permission("service_workflows", "list")
def list_workflows(request, service_id: int):
    get_object_or_404(Service, id=service_id)
    workflows = _workflow_queryset().filter(service_id=service_id)
    return [_serialize_workflow(workflow) for workflow in workflows]


@router.post("/{service_id}/workflows", response={201: Dict[str, Any], 400: MessageSchema}, operation_id="services_api_v1_services_create_workflow")
@require_permission("service_workflows", "create")
def create_workflow(request, service_id: int, payload: WorkflowIn):
    try:
        service = get_object_or_404(Service, id=service_id)
        workflow = domain_services.create_workflow(service, payload, created_by_id=_current_user_id(request, payload.created_by_id))
        return 201, _serialize_workflow(workflow)
    except (ValidationError, IntegrityError) as e:
        return 400, {"detail": _validation_detail(e)}


@router.get("/{service_id}/workflows/{workflow_id}", response=Dict[str, Any], operation_id="services_api_v1_services_get_workflow")
@require_permission("service_workflows", "view")
def get_workflow(request, service_id: int, workflow_id: int):
    workflow = get_object_or_404(_workflow_queryset(), id=workflow_id, service_id=service_id)
    return _serialize_workflow(workflow)


@router.put("/{service_id}/workflows/{workflow_id}", response={200: Dict[str, Any], 400: MessageSchema, 404: MessageSchema}, operation_id="services_api_v1_services_update_workflow")
@require_permission("service_workflows", "update")
def update_workflow(request, service_id: int, workflow_id: int, payload: WorkflowUpdate):
    try:
        workflow = get_object_or_404(ServiceWorkflow, id=workflow_id, service_id=service_id)
        return 200, _serialize_workflow(domain_services.update_workflow(workflow, payload))
    except (ValidationError, IntegrityError) as e:
        return 400, {"detail": _validation_detail(e)}


@router.delete("/{service_id}/workflows/{workflow_id}", response={200: MessageSchema, 404: MessageSchema}, operation_id="services_api_v1_services_delete_workflow")
@require_permission("service_workflows", "delete")
def delete_workflow(request, service_id: int, workflow_id: int):
    workflow = get_object_or_404(ServiceWorkflow, id=workflow_id, service_id=service_id)
    outcome = domain_services.delete_workflow(workflow)
    return 200, {"detail": "Workflow deleted successfully" if outcome == "deleted" else "Workflow archived successfully"}


@router.get("/{service_id}/workflows/{workflow_id}/stages", response=List[Dict[str, Any]], operation_id="services_api_v1_services_list_workflow_stages")
@require_permission("service_workflows", "view")
def list_workflow_stages(request, service_id: int, workflow_id: int):
    get_object_or_404(ServiceWorkflow, id=workflow_id, service_id=service_id)
    stages = ServiceWorkflowStage.objects.filter(workflow_id=workflow_id).select_related("owner_role")
    return [_serialize_workflow_stage(stage) for stage in stages]


@router.put("/{service_id}/workflows/{workflow_id}/stages", response={200: List[Dict[str, Any]], 400: MessageSchema, 404: MessageSchema}, operation_id="services_api_v1_services_replace_workflow_stages")
@require_permission("service_workflows", "update")
def replace_workflow_stages(request, service_id: int, workflow_id: int, payload: WorkflowStageBulkReplace):
    try:
        workflow = get_object_or_404(ServiceWorkflow, id=workflow_id, service_id=service_id)
        return 200, [_serialize_workflow_stage(stage) for stage in domain_services.replace_workflow_stages(workflow, payload.stages)]
    except (ValidationError, IntegrityError) as e:
        return 400, {"detail": _validation_detail(e)}


@router.post("/{service_id}/workflows/{workflow_id}/stages", response={201: Dict[str, Any], 400: MessageSchema, 404: MessageSchema}, operation_id="services_api_v1_services_create_workflow_stage")
@require_permission("service_workflows", "update")
def create_workflow_stage(request, service_id: int, workflow_id: int, payload: WorkflowStageIn):
    try:
        workflow = get_object_or_404(ServiceWorkflow, id=workflow_id, service_id=service_id)
        if payload.owner_role_id:
            get_object_or_404(Role, id=payload.owner_role_id)
        stage = ServiceWorkflowStage.objects.create(
            workflow=workflow,
            name=payload.name,
            owner_role_id=payload.owner_role_id,
            sla_days=payload.sla_days,
            requires_approval=payload.requires_approval,
            requires_evidence=payload.requires_evidence,
            client_visible=payload.client_visible,
            sort_order=payload.sort_order,
        )
        stage = ServiceWorkflowStage.objects.select_related("owner_role").get(id=stage.id)
        return 201, _serialize_workflow_stage(stage)
    except (ValidationError, IntegrityError) as e:
        return 400, {"detail": _validation_detail(e)}


@router.put("/{service_id}/workflows/{workflow_id}/stages/{stage_id}", response={200: Dict[str, Any], 400: MessageSchema, 404: MessageSchema}, operation_id="services_api_v1_services_update_workflow_stage")
@require_permission("service_workflows", "update")
def update_workflow_stage(request, service_id: int, workflow_id: int, stage_id: int, payload: WorkflowStageUpdate):
    try:
        stage = get_object_or_404(ServiceWorkflowStage, id=stage_id, workflow_id=workflow_id, workflow__service_id=service_id)
        update_data = payload.dict(exclude_unset=True)
        if update_data.get("owner_role_id"):
            get_object_or_404(Role, id=update_data["owner_role_id"])
        for attr, value in update_data.items():
            setattr(stage, attr, value)
        stage.save()
        stage = ServiceWorkflowStage.objects.select_related("owner_role").get(id=stage.id)
        return 200, _serialize_workflow_stage(stage)
    except (ValidationError, IntegrityError) as e:
        return 400, {"detail": _validation_detail(e)}


@router.delete("/{service_id}/workflows/{workflow_id}/stages/{stage_id}", response={200: MessageSchema, 404: MessageSchema}, operation_id="services_api_v1_services_delete_workflow_stage")
@require_permission("service_workflows", "update")
def delete_workflow_stage(request, service_id: int, workflow_id: int, stage_id: int):
    stage = get_object_or_404(ServiceWorkflowStage, id=stage_id, workflow_id=workflow_id, workflow__service_id=service_id)
    stage.delete()
    return 200, {"detail": "Workflow stage deleted successfully"}


@router.post("/{service_id}/workflow-seed", response={201: Dict[str, Any], 400: MessageSchema}, operation_id="services_api_v1_services_seed_workflow")
@require_permission("service_workflows", "create")
def seed_workflow(request, service_id: int, payload: WorkflowSeedIn):
    try:
        service = get_object_or_404(Service, id=service_id)
        workflow = domain_services.create_workflow(service, payload, created_by_id=_current_user_id(request, payload.created_by_id))
        return 201, _serialize_workflow(workflow)
    except (ValidationError, IntegrityError) as e:
        return 400, {"detail": _validation_detail(e)}


@router.get("/{service_id}/workflow-summary", response=List[Dict[str, Any]], operation_id="services_api_v1_services_get_workflow_summary")
@require_permission("service_workflows", "list")
def get_workflow_summary(request, service_id: int):
    get_object_or_404(Service, id=service_id)
    workflows = _workflow_queryset().filter(service_id=service_id)
    return [_serialize_workflow(workflow) for workflow in workflows]


@router.post("/{service_id}/workflows/{workflow_id}/activate", response={200: Dict[str, Any], 404: MessageSchema}, operation_id="services_api_v1_services_activate_workflow")
@require_permission("service_workflows", "update")
def activate_workflow(request, service_id: int, workflow_id: int):
    service = get_object_or_404(Service, id=service_id)
    workflow = get_object_or_404(_workflow_queryset(), id=workflow_id, service=service)
    domain_services.activate_workflow(service, workflow)
    workflow.refresh_from_db()
    return 200, _serialize_workflow(workflow)
