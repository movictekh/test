"""Core Service catalogue, Service CRUD, publishing and subservice endpoints."""

from typing import Any, Dict, List
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja import Router
from ninja.pagination import LimitOffsetPagination, paginate
from domains.service_operations import selectors as domain_selectors
from domains.service_operations.services import catalogue as domain_services
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
from ._catalogue_support import (
    _current_user_id,
    _serialize_catalogue_card,
    _serialize_catalogue_detail,
    _serialize_service_core,
    _serialize_subservice,
    _validation_detail,
)


router = Router(tags=["Services"])


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
