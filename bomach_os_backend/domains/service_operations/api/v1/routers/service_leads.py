from typing import List

from django.core.exceptions import ValidationError
from django.db.models import Q
from django.shortcuts import get_object_or_404
from ninja import Router
from ninja.pagination import LimitOffsetPagination, paginate

from services.api.schema.others import MessageSchema
from ..schemas.lifecycle import ServiceLeadIn, ServiceLeadOut, ServiceLeadUpdate
from services.models.service import ServiceLead
from user.utils.perm import require_permission


router = Router(tags=["Service Leads"])


@router.get("", response=List[ServiceLeadOut])
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("service_leads", "list")
def list_leads(request, status: str = None, client_id: int = None, search: str = None):
    """List all service leads with optional filtering."""
    leads = ServiceLead.objects.select_related('service', 'service__category').all()

    if status:
        leads = leads.filter(status=status)
    if client_id:
        leads = leads.filter(client_id=client_id)
    if search:
        leads = leads.filter(Q(notes__icontains=search))

    return leads


@router.post("", response={201: ServiceLeadOut, 400: MessageSchema})
@require_permission("service_leads", "create")
def create_lead(request, payload: ServiceLeadIn):
    """Create a new service lead."""
    try:
        lead = ServiceLead.objects.create(**payload.dict())
        return 201, lead
    except ValidationError as e:
        return 400, {'detail': e.messages[0]}
    except Exception as e:
        return 400, {'detail': str(e)}


@router.get("/{lead_id}", response=ServiceLeadOut)
@require_permission("service_leads", "view")
def get_lead(request, lead_id: int):
    """Get a specific service lead by ID."""
    return get_object_or_404(
        ServiceLead.objects.select_related('service', 'service__category'),
        id=lead_id,
    )


@router.put("/{lead_id}", response={200: ServiceLeadOut, 400: MessageSchema, 404: MessageSchema})
@require_permission("service_leads", "update")
def update_lead(request, lead_id: int, payload: ServiceLeadUpdate):
    """Update an existing service lead."""
    try:
        lead = get_object_or_404(ServiceLead, id=lead_id)
        for attr, value in payload.dict(exclude_unset=True).items():
            setattr(lead, attr, value)
        lead.save()
        return 200, lead
    except ValidationError as e:
        return 400, {'detail': e.messages[0]}
    except Exception as e:
        return 400, {'detail': str(e)}


@router.delete("/{lead_id}", response={200: MessageSchema, 400: MessageSchema, 404: MessageSchema})
@require_permission("service_leads", "delete")
def delete_lead(request, lead_id: int):
    """Delete a service lead."""
    try:
        lead = get_object_or_404(ServiceLead, id=lead_id)
        lead.delete()
        return 200, {"detail": "Lead deleted successfully"}
    except ValidationError as e:
        return 400, {'detail': e.messages[0]}
    except Exception as e:
        return 400, {'detail': str(e)}
