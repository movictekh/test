from typing import Any, Dict, List

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja import Router
from ninja.pagination import LimitOffsetPagination, paginate
from domains.service_operations import selectors as domain_selectors, services as domain_services

from services.api.schema.others import MessageSchema
from ..schemas.catalogue import (
    BranchActivationBulkUpsert,
    FieldTypeOut,
    PricingConfigIn,
    PricingConfigUpdate,
    RequestFormIn,
    RequestFormUpdate,
    ServiceCoreOut,
    ServiceCreateSchema,
    ServicePublishIn,
    ServiceSubServiceBulkReplace,
    ServiceSubServiceIn,
    ServiceSubServiceUpdate,
    ServiceUpdateSchema,
    WorkflowIn,
    WorkflowSeedIn,
    WorkflowStageBulkReplace,
    WorkflowStageIn,
    WorkflowStageUpdate,
    WorkflowUpdate,
)
from domains.service_operations.models import (
    Service,
    ServiceBranchActivation,
    ServiceCategory,
    ServiceFieldType,
    ServicePricingConfig,
    ServicePricingField,
    ServiceRequestField,
    ServiceRequestForm,
    ServiceSubService,
    ServiceWorkflow,
    ServiceWorkflowStage,
)
from user.models.branch import Branch
from user.models.role import Role
from user.utils.perm import require_permission


router = Router(tags=["Services"])


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
        row["fields"] = [_serialize_pricing_field(field) for field in config.fields.all()]
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
        row["stages"] = [_serialize_workflow_stage(stage) for stage in workflow.stages.all()]
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
    row.update({
        "active_request_form": (
            _serialize_request_form(service.active_request_form, include_fields=False)
            if service.active_request_form else None
        ),
        "active_pricing_config": (
            _serialize_pricing_config(service.active_pricing_config, include_fields=False)
            if service.active_pricing_config else None
        ),
        "active_workflow": (
            _serialize_workflow(service.active_workflow, include_stages=False)
            if service.active_workflow else None
        ),
        "active_branches": [
            _serialize_branch_activation(activation)
            for activation in service.branch_activations.all()
            if activation.status == "active"
        ],
    })
    return row


def _serialize_catalogue_detail(service):
    row = _serialize_catalogue_card(service)
    row.update({
        "subservices": [_serialize_subservice(item) for item in service.subservices.all()],
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
    })
    return row


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


@router.get("/catalogue", response=List[Dict[str, Any]], operation_id="services_api_v1_services_list_service_catalogue")
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("services", "list")
def list_service_catalogue(
    request,
    status: str = None,
    category_id: int = None,
    division: str = None,
    branch_id: int = None,
    client_visibility: str = None,
    search: str = None,
):
    services = domain_selectors.filter_services(
        domain_selectors.service_queryset(),
        status=status,
        category_id=category_id,
        division=division,
        branch_id=branch_id,
        client_visibility=client_visibility,
        search=search,
    )
    return [_serialize_catalogue_card(service) for service in services]


@router.get("/catalogue/{service_id}", response=Dict[str, Any], operation_id="services_api_v1_services_get_service_catalogue_detail")
@require_permission("services", "view")
def get_service_catalogue_detail(request, service_id: int):
    service = get_object_or_404(domain_selectors.service_queryset(), id=service_id)
    return _serialize_catalogue_detail(service)


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


@router.get("/branch-activation-matrix", response=List[Dict[str, Any]], operation_id="services_api_v1_services_get_branch_activation_matrix")
@require_permission("service_branch_activations", "list")
def get_branch_activation_matrix(request, division: str = None, status: str = None, branch_id: int = None, search: str = None):
    services = domain_selectors.filter_services(domain_selectors.service_queryset(), division=division, branch_id=branch_id, search=search)
    if status:
        services = services.filter(branch_activations__status=status).distinct()
    return [_serialize_catalogue_card(service) for service in services]


@router.get("", response=List[ServiceCoreOut], operation_id="services_api_v1_services_list_services")
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("services", "list")
def list_services(
    request,
    status: str = None,
    category_id: int = None,
    division: str = None,
    owner_role_id: int = None,
    client_visibility: str = None,
    branch_id: int = None,
    search: str = None,
):
    services = domain_selectors.filter_services(
        domain_selectors.service_queryset(),
        status=status,
        category_id=category_id,
        division=division,
        owner_role_id=owner_role_id,
        client_visibility=client_visibility,
        branch_id=branch_id,
        search=search,
    )
    return [_serialize_service_core(service) for service in services]


@router.post("", response={201: ServiceCoreOut, 400: MessageSchema}, operation_id="services_api_v1_services_create_service")
@require_permission("services", "create")
def create_service(request, payload: ServiceCreateSchema):
    try:
        if payload.status:
            domain_services.ensure_choice(payload.status, Service.STATUS_CHOICES, "status")
        if payload.fulfillment_mode:
            domain_services.ensure_choice(payload.fulfillment_mode, Service.FULFILLMENT_MODE_CHOICES, "fulfillment_mode")
        domain_services.ensure_choice(payload.client_visibility, Service.CLIENT_VISIBILITY_CHOICES, "client_visibility")
        get_object_or_404(ServiceCategory, id=payload.category_id)
        if payload.owner_role_id:
            get_object_or_404(Role, id=payload.owner_role_id)

        service = Service.objects.create(
            name=payload.name,
            code=payload.code or None,
            category_id=payload.category_id,
            division=payload.division or "",
            description=payload.description,
            base_price=payload.base_price,
            delivery_time=payload.delivery_time or "",
            status=payload.status or "draft",
            owner_role_id=payload.owner_role_id,
            default_sla_days=payload.default_sla_days,
            fulfillment_mode=payload.fulfillment_mode or "",
            client_visibility=payload.client_visibility,
            created_by_id=_current_user_id(request, payload.created_by_id),
        )
        return 201, _serialize_service_core(Service.objects.select_related("category", "owner_role", "created_by").get(id=service.id))
    except (ValidationError, IntegrityError) as e:
        return 400, {"detail": _validation_detail(e)}


@router.get("/{service_id}", response=ServiceCoreOut, operation_id="services_api_v1_services_get_service")
@require_permission("services", "view")
def get_service(request, service_id: int):
    service = get_object_or_404(domain_selectors.service_queryset(), id=service_id)
    return _serialize_service_core(service)


@router.put("/{service_id}", response={200: ServiceCoreOut, 400: MessageSchema, 404: MessageSchema}, operation_id="services_api_v1_services_update_service")
@require_permission("services", "update")
def update_service(request, service_id: int, payload: ServiceUpdateSchema):
    try:
        service = get_object_or_404(Service, id=service_id)
        update_data = payload.dict(exclude_unset=True)
        for field_name in ["status", "fulfillment_mode", "client_visibility"]:
            if field_name in update_data and update_data[field_name]:
                choices = getattr(Service, f"{field_name.upper()}_CHOICES", None)
                if field_name == "status":
                    choices = Service.STATUS_CHOICES
                domain_services.ensure_choice(update_data[field_name], choices, field_name)
        if "category_id" in update_data and update_data["category_id"]:
            get_object_or_404(ServiceCategory, id=update_data["category_id"])
        if "owner_role_id" in update_data and update_data["owner_role_id"]:
            get_object_or_404(Role, id=update_data["owner_role_id"])

        for attr, value in update_data.items():
            setattr(service, attr, value)
        service.save()
        service = get_object_or_404(domain_selectors.service_queryset(), id=service_id)
        return 200, _serialize_service_core(service)
    except (ValidationError, IntegrityError) as e:
        return 400, {"detail": _validation_detail(e)}


@router.delete("/{service_id}", response={200: MessageSchema, 400: MessageSchema, 404: MessageSchema}, operation_id="services_api_v1_services_delete_service")
@require_permission("services", "delete")
def delete_service(request, service_id: int):
    try:
        service = get_object_or_404(Service, id=service_id)
        if service.status == "draft" and domain_selectors.service_dependents_count(service) == 0:
            service.delete()
            return 200, {"detail": "Service deleted successfully"}
        service.status = "inactive"
        service.save(update_fields=["status", "updated_at"])
        return 200, {"detail": "Service marked inactive successfully"}
    except ValidationError as e:
        return 400, {"detail": _validation_detail(e)}


@router.post("/{service_id}/publish", response={200: Dict[str, Any], 400: MessageSchema, 404: MessageSchema}, operation_id="services_api_v1_services_publish_service")
@require_permission("services", "update")
def publish_service(request, service_id: int, payload: ServicePublishIn):
    try:
        with transaction.atomic():
            service = get_object_or_404(Service, id=service_id)
            domain_services.ensure_choice(payload.status, Service.STATUS_CHOICES, "status")
            if payload.client_visibility:
                domain_services.ensure_choice(payload.client_visibility, Service.CLIENT_VISIBILITY_CHOICES, "client_visibility")

            request_form = (
                get_object_or_404(ServiceRequestForm, id=payload.request_form_id, service=service)
                if payload.request_form_id else service.active_request_form
            )
            pricing_config = (
                get_object_or_404(ServicePricingConfig, id=payload.pricing_config_id, service=service)
                if payload.pricing_config_id else service.active_pricing_config
            )
            workflow = (
                get_object_or_404(ServiceWorkflow, id=payload.workflow_id, service=service)
                if payload.workflow_id else service.active_workflow
            )

            if payload.status == "active":
                if not request_form:
                    raise ValidationError({"request_form": "An active request form is required before publishing."})
                if not pricing_config:
                    raise ValidationError({"pricing_config": "An active pricing config is required before publishing."})
                if not ServiceBranchActivation.objects.filter(service=service, status="active").exists():
                    raise ValidationError({"branch_activations": "At least one active branch is required before publishing."})

            if request_form:
                domain_services.activate_request_form(service, request_form)
            if pricing_config:
                domain_services.activate_pricing_config(service, pricing_config)
            if workflow:
                domain_services.activate_workflow(service, workflow)

            service.status = payload.status
            if payload.client_visibility:
                service.client_visibility = payload.client_visibility
            service.save()
        service = get_object_or_404(domain_selectors.service_queryset(), id=service_id)
        return 200, _serialize_catalogue_detail(service)
    except (ValidationError, IntegrityError) as e:
        return 400, {"detail": _validation_detail(e)}


@router.get("/{service_id}/subservices", response=List[Dict[str, Any]], operation_id="services_api_v1_services_list_subservices")
@require_permission("service_subservices", "list")
def list_subservices(request, service_id: int):
    get_object_or_404(Service, id=service_id)
    return [_serialize_subservice(item) for item in ServiceSubService.objects.filter(service_id=service_id)]


@router.put("/{service_id}/subservices", response={200: List[Dict[str, Any]], 400: MessageSchema}, operation_id="services_api_v1_services_replace_subservices")
@require_permission("service_subservices", "update")
def replace_subservices(request, service_id: int, payload: ServiceSubServiceBulkReplace):
    try:
        service = get_object_or_404(Service, id=service_id)
        codes = [item.code or item.name.lower().replace(" ", "-") for item in payload.subservices]
        if len(codes) != len(set(codes)):
            raise ValidationError({"code": "Subservice codes must be unique within a service."})
        with transaction.atomic():
            ServiceSubService.objects.filter(service=service).delete()
            rows = []
            for index, item in enumerate(payload.subservices):
                rows.append(ServiceSubService(
                    service=service,
                    code=item.code or item.name.lower().replace(" ", "-"),
                    name=item.name,
                    description=item.description or "",
                    status=item.status,
                    default_sla_days=item.default_sla_days,
                    sort_order=item.sort_order if item.sort_order is not None else index,
                ))
            ServiceSubService.objects.bulk_create(rows)
        return 200, [_serialize_subservice(item) for item in ServiceSubService.objects.filter(service=service)]
    except (ValidationError, IntegrityError) as e:
        return 400, {"detail": _validation_detail(e)}


@router.post("/{service_id}/subservices", response={201: Dict[str, Any], 400: MessageSchema}, operation_id="services_api_v1_services_create_subservice")
@require_permission("service_subservices", "create")
def create_subservice(request, service_id: int, payload: ServiceSubServiceIn):
    try:
        service = get_object_or_404(Service, id=service_id)
        domain_services.ensure_choice(payload.status, ServiceSubService.STATUS_CHOICES, "status")
        subservice = ServiceSubService.objects.create(
            service=service,
            code=payload.code or payload.name.lower().replace(" ", "-"),
            name=payload.name,
            description=payload.description or "",
            status=payload.status,
            default_sla_days=payload.default_sla_days,
            sort_order=payload.sort_order,
        )
        return 201, _serialize_subservice(subservice)
    except (ValidationError, IntegrityError) as e:
        return 400, {"detail": _validation_detail(e)}


@router.put("/{service_id}/subservices/{subservice_id}", response={200: Dict[str, Any], 400: MessageSchema, 404: MessageSchema}, operation_id="services_api_v1_services_update_subservice")
@require_permission("service_subservices", "update")
def update_subservice(request, service_id: int, subservice_id: int, payload: ServiceSubServiceUpdate):
    try:
        subservice = get_object_or_404(ServiceSubService, id=subservice_id, service_id=service_id)
        update_data = payload.dict(exclude_unset=True)
        if update_data.get("status"):
            domain_services.ensure_choice(update_data["status"], ServiceSubService.STATUS_CHOICES, "status")
        for attr, value in update_data.items():
            setattr(subservice, attr, value)
        subservice.save()
        return 200, _serialize_subservice(subservice)
    except (ValidationError, IntegrityError) as e:
        return 400, {"detail": _validation_detail(e)}


@router.delete("/{service_id}/subservices/{subservice_id}", response={200: MessageSchema, 404: MessageSchema}, operation_id="services_api_v1_services_delete_subservice")
@require_permission("service_subservices", "delete")
def delete_subservice(request, service_id: int, subservice_id: int):
    subservice = get_object_or_404(ServiceSubService, id=subservice_id, service_id=service_id)
    if subservice.status == "draft":
        subservice.delete()
        return 200, {"detail": "Subservice deleted successfully"}
    subservice.status = "inactive"
    subservice.save(update_fields=["status", "updated_at"])
    return 200, {"detail": "Subservice marked inactive successfully"}


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
        domain_services.ensure_choice(payload.status, ServiceRequestForm.STATUS_CHOICES, "status")
        with transaction.atomic():
            form = ServiceRequestForm.objects.create(
                service=service,
                name=payload.name,
                version=payload.version,
                status=payload.status,
                is_active=False,
                created_by_id=_current_user_id(request, payload.created_by_id),
            )
            domain_services.create_request_fields(form, payload.fields)
            if payload.is_active:
                domain_services.activate_request_form(service, form)
        form = ServiceRequestForm.objects.prefetch_related("fields").get(id=form.id)
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
        service = form.service
        update_data = payload.dict(exclude_unset=True)
        fields = update_data.pop("fields", None)
        if update_data.get("status"):
            domain_services.ensure_choice(update_data["status"], ServiceRequestForm.STATUS_CHOICES, "status")
        with transaction.atomic():
            make_active = update_data.pop("is_active", None)
            for attr, value in update_data.items():
                setattr(form, attr, value)
            form.save()
            if fields is not None:
                form.fields.all().delete()
                domain_services.create_request_fields(form, fields)
            if make_active is True:
                domain_services.activate_request_form(service, form)
            elif make_active is False and form.is_active:
                form.is_active = False
                form.save(update_fields=["is_active", "updated_at"])
                if service.active_request_form_id == form.id:
                    service.active_request_form = None
                    service.save(update_fields=["active_request_form", "updated_at"])
        form = ServiceRequestForm.objects.prefetch_related("fields").get(id=form.id)
        return 200, _serialize_request_form(form)
    except (ValidationError, IntegrityError) as e:
        return 400, {"detail": _validation_detail(e)}


@router.delete("/{service_id}/request-forms/{form_id}", response={200: MessageSchema, 404: MessageSchema}, operation_id="services_api_v1_services_delete_request_form")
@require_permission("service_request_forms", "delete")
def delete_request_form(request, service_id: int, form_id: int):
    form = get_object_or_404(ServiceRequestForm, id=form_id, service_id=service_id)
    service = form.service
    if form.status == "draft" and not form.is_active:
        form.delete()
        return 200, {"detail": "Request form deleted successfully"}
    form.status = "archived"
    form.is_active = False
    form.save(update_fields=["status", "is_active", "updated_at"])
    if service.active_request_form_id == form.id:
        service.active_request_form = None
        service.save(update_fields=["active_request_form", "updated_at"])
    return 200, {"detail": "Request form archived successfully"}


@router.post("/{service_id}/request-forms/{form_id}/activate", response={200: Dict[str, Any], 404: MessageSchema}, operation_id="services_api_v1_services_activate_request_form")
@require_permission("service_request_forms", "update")
def activate_request_form(request, service_id: int, form_id: int):
    service = get_object_or_404(Service, id=service_id)
    form = get_object_or_404(ServiceRequestForm.objects.prefetch_related("fields"), id=form_id, service=service)
    with transaction.atomic():
        domain_services.activate_request_form(service, form)
    form.refresh_from_db()
    return 200, _serialize_request_form(form)


@router.post("/{service_id}/pricing-configs", response={201: Dict[str, Any], 400: MessageSchema}, operation_id="services_api_v1_services_create_pricing_config")
@require_permission("service_pricing_configs", "create")
def create_pricing_config(request, service_id: int, payload: PricingConfigIn):
    try:
        service = get_object_or_404(Service, id=service_id)
        domain_services.ensure_choice(payload.status, ServicePricingConfig.STATUS_CHOICES, "status")
        domain_services.ensure_choice(payload.pricing_type, ServicePricingConfig.PRICING_TYPE_CHOICES, "pricing_type")
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
                created_by_id=_current_user_id(request, payload.created_by_id),
            )
            domain_services.create_pricing_fields(config, payload.fields)
            if payload.is_active:
                domain_services.activate_pricing_config(service, config)
        config = ServicePricingConfig.objects.select_related("service").prefetch_related("fields").get(id=config.id)
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
        service = config.service
        update_data = payload.dict(exclude_unset=True)
        fields = update_data.pop("fields", None)
        if update_data.get("status"):
            domain_services.ensure_choice(update_data["status"], ServicePricingConfig.STATUS_CHOICES, "status")
        if update_data.get("pricing_type"):
            domain_services.ensure_choice(update_data["pricing_type"], ServicePricingConfig.PRICING_TYPE_CHOICES, "pricing_type")
        with transaction.atomic():
            make_active = update_data.pop("is_active", None)
            for attr, value in update_data.items():
                setattr(config, attr, value)
            config.save()
            if fields is not None:
                config.fields.all().delete()
                domain_services.create_pricing_fields(config, fields)
            if make_active is True:
                domain_services.activate_pricing_config(service, config)
            elif make_active is False and config.is_active:
                config.is_active = False
                config.save(update_fields=["is_active", "updated_at"])
                if service.active_pricing_config_id == config.id:
                    service.active_pricing_config = None
                    service.save(update_fields=["active_pricing_config", "updated_at"])
        config = ServicePricingConfig.objects.select_related("service").prefetch_related("fields").get(id=config.id)
        return 200, _serialize_pricing_config(config)
    except (ValidationError, IntegrityError) as e:
        return 400, {"detail": _validation_detail(e)}


@router.delete("/{service_id}/pricing-configs/{config_id}", response={200: MessageSchema, 404: MessageSchema}, operation_id="services_api_v1_services_delete_pricing_config")
@require_permission("service_pricing_configs", "delete")
def delete_pricing_config(request, service_id: int, config_id: int):
    config = get_object_or_404(ServicePricingConfig, id=config_id, service_id=service_id)
    service = config.service
    if config.status == "draft" and not config.is_active:
        config.delete()
        return 200, {"detail": "Pricing config deleted successfully"}
    config.status = "archived"
    config.is_active = False
    config.save(update_fields=["status", "is_active", "updated_at"])
    if service.active_pricing_config_id == config.id:
        service.active_pricing_config = None
        service.save(update_fields=["active_pricing_config", "updated_at"])
    return 200, {"detail": "Pricing config archived successfully"}


@router.post("/{service_id}/pricing-configs/{config_id}/activate", response={200: Dict[str, Any], 404: MessageSchema}, operation_id="services_api_v1_services_activate_pricing_config")
@require_permission("service_pricing_configs", "update")
def activate_pricing_config(request, service_id: int, config_id: int):
    service = get_object_or_404(Service, id=service_id)
    config = get_object_or_404(ServicePricingConfig.objects.select_related("service").prefetch_related("fields"), id=config_id, service=service)
    with transaction.atomic():
        domain_services.activate_pricing_config(service, config)
    config.refresh_from_db()
    return 200, _serialize_pricing_config(config)


def _workflow_queryset():
    return ServiceWorkflow.objects.select_related("service", "created_by").prefetch_related("stages__owner_role")


def _create_workflow(request, service, payload):
    domain_services.ensure_choice(payload.status, ServiceWorkflow.STATUS_CHOICES, "status")
    with transaction.atomic():
        workflow = ServiceWorkflow.objects.create(
            service=service,
            name=payload.name,
            version=payload.version,
            status=payload.status,
            is_active=False,
            created_by_id=_current_user_id(request, payload.created_by_id),
        )
        domain_services.create_workflow_stages(workflow, payload.stages)
        if payload.is_active:
            domain_services.activate_workflow(service, workflow)
    return _workflow_queryset().get(id=workflow.id)


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
        workflow = _create_workflow(request, service, payload)
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
        service = workflow.service
        update_data = payload.dict(exclude_unset=True)
        stages = update_data.pop("stages", None)
        if update_data.get("status"):
            domain_services.ensure_choice(update_data["status"], ServiceWorkflow.STATUS_CHOICES, "status")
        with transaction.atomic():
            make_active = update_data.pop("is_active", None)
            for attr, value in update_data.items():
                setattr(workflow, attr, value)
            workflow.save()
            if stages is not None:
                workflow.stages.all().delete()
                domain_services.create_workflow_stages(workflow, stages)
            if make_active is True:
                domain_services.activate_workflow(service, workflow)
            elif make_active is False and workflow.is_active:
                workflow.is_active = False
                workflow.save(update_fields=["is_active", "updated_at"])
                if service.active_workflow_id == workflow.id:
                    service.active_workflow = None
                    service.save(update_fields=["active_workflow", "updated_at"])
        workflow = _workflow_queryset().get(id=workflow.id)
        return 200, _serialize_workflow(workflow)
    except (ValidationError, IntegrityError) as e:
        return 400, {"detail": _validation_detail(e)}


@router.delete("/{service_id}/workflows/{workflow_id}", response={200: MessageSchema, 404: MessageSchema}, operation_id="services_api_v1_services_delete_workflow")
@require_permission("service_workflows", "delete")
def delete_workflow(request, service_id: int, workflow_id: int):
    workflow = get_object_or_404(ServiceWorkflow, id=workflow_id, service_id=service_id)
    service = workflow.service
    with transaction.atomic():
        if workflow.status == "draft" and not workflow.is_active:
            workflow.delete()
            return 200, {"detail": "Workflow deleted successfully"}
        workflow.status = "archived"
        workflow.is_active = False
        workflow.save(update_fields=["status", "is_active", "updated_at"])
        if service.active_workflow_id == workflow.id:
            service.active_workflow = None
            service.save(update_fields=["active_workflow", "updated_at"])
    return 200, {"detail": "Workflow archived successfully"}


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
        with transaction.atomic():
            workflow.stages.all().delete()
            domain_services.create_workflow_stages(workflow, payload.stages)
        stages = ServiceWorkflowStage.objects.filter(workflow=workflow).select_related("owner_role")
        return 200, [_serialize_workflow_stage(stage) for stage in stages]
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
        workflow = _create_workflow(request, service, payload)
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
    with transaction.atomic():
        domain_services.activate_workflow(service, workflow)
    workflow.refresh_from_db()
    return 200, _serialize_workflow(workflow)


@router.get("/{service_id}/branch-activations", response=List[Dict[str, Any]], operation_id="services_api_v1_services_list_branch_activations")
@require_permission("service_branch_activations", "list")
def list_branch_activations(request, service_id: int):
    get_object_or_404(Service, id=service_id)
    activations = ServiceBranchActivation.objects.filter(service_id=service_id).select_related("branch")
    return [_serialize_branch_activation(activation) for activation in activations]


@router.put("/{service_id}/branch-activations", response={200: List[Dict[str, Any]], 400: MessageSchema}, operation_id="services_api_v1_services_upsert_branch_activations")
@require_permission("service_branch_activations", "update")
def upsert_branch_activations(request, service_id: int, payload: BranchActivationBulkUpsert):
    try:
        service = get_object_or_404(Service, id=service_id)
        branch_ids = [item.branch_id for item in payload.branch_activations]
        if len(branch_ids) != len(set(branch_ids)):
            raise ValidationError({"branch_id": "Branch IDs must be unique in the payload."})
        for item in payload.branch_activations:
            domain_services.ensure_choice(item.status, ServiceBranchActivation.STATUS_CHOICES, "status")
            get_object_or_404(Branch, id=item.branch_id)
        with transaction.atomic():
            for item in payload.branch_activations:
                defaults = {
                    "status": item.status,
                    "client_visible": item.client_visible,
                    "capacity": item.capacity,
                    "activated_at": item.activated_at or (timezone.now() if item.status == "active" else None),
                }
                ServiceBranchActivation.objects.update_or_create(
                    service=service,
                    branch_id=item.branch_id,
                    defaults=defaults,
                )
        activations = ServiceBranchActivation.objects.filter(service=service).select_related("branch")
        return 200, [_serialize_branch_activation(activation) for activation in activations]
    except (ValidationError, IntegrityError) as e:
        return 400, {"detail": _validation_detail(e)}
