"""Service branch activation endpoints."""

from typing import Any, Dict, List
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja import Router
from domains.service_operations import selectors as domain_selectors
from domains.service_operations.services import catalogue as domain_services
from services.api.schema.others import MessageSchema
from ..schemas.catalogue import BranchActivationBulkUpsert
from domains.service_operations.models import Service, ServiceBranchActivation
from user.models.branch import Branch
from user.utils.perm import require_permission
from ._catalogue_support import (
    _serialize_branch_activation,
    _serialize_catalogue_card,
    _validation_detail,
)


router = Router(tags=["Services"])


@router.get("/branch-activation-matrix", response=List[Dict[str, Any]], operation_id="services_api_v1_services_get_branch_activation_matrix")
@require_permission("service_branch_activations", "list")
def get_branch_activation_matrix(request, division: str = None, status: str = None, branch_id: int = None, search: str = None):
    services = domain_selectors.filter_services(domain_selectors.service_queryset(), division=division, branch_id=branch_id, search=search)
    if status:
        services = services.filter(branch_activations__status=status).distinct()
    return [_serialize_catalogue_card(service) for service in services]


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
