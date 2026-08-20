from ninja import Router, Query
from ninja.pagination import paginate, LimitOffsetPagination

from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError
from django.db.models import Q
from typing import Optional, List

from user.api.schemas.others import MessageSchema
from user.api.schemas.partner import (
    PartnerSchema,
    PartnerCreateSchema,
    PartnerUpdateSchema,
    PartnerChoicesSchema,
    AgreementSchema,
    AgreementCreateSchema,
    AgreementUpdateSchema,
)
from user.models.partner import Partner, PartnerAgreement
from user.utils.perm import require_permission


partner_api = Router(tags=["Partners"])


# ============== Choices ==============

@partner_api.get("/choices/fields", response=PartnerChoicesSchema)
def get_partner_field_choices(request):
    """Get available choices for partner fields."""
    return {
        "category": [
            {"value": c[0], "label": c[1]}
            for c in Partner.CATEGORY_CHOICES
        ],
        "status": [
            {"value": c[0], "label": c[1]}
            for c in Partner.STATUS_CHOICES
        ],
    }


# ============== Partner CRUD ==============

@partner_api.get("/", response=List[PartnerSchema])
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("partners", "list")
def list_partners(
    request,
    category: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
):
    """List all partners with filtering and search."""
    partners = Partner.objects.all()

    if category:
        partners = partners.filter(category=category)
    if status:
        partners = partners.filter(status=status)
    if search:
        partners = partners.filter(
            Q(name__icontains=search) |
            Q(email__icontains=search) |
            Q(phone__icontains=search) |
            Q(address__icontains=search)
        )

    return partners.order_by('-created_at')


@partner_api.get("/{partner_id}", response={200: PartnerSchema, 404: MessageSchema})
@require_permission("partners", "view")
def get_partner(request, partner_id: int):
    """Get a specific partner by ID."""
    try:
        partner = Partner.objects.get(id=partner_id)
        return 200, partner
    except Partner.DoesNotExist:
        return 404, {"detail": "Partner not found"}


@partner_api.post("/", response={201: PartnerSchema, 400: MessageSchema})
@require_permission("partners", "create")
def create_partner(request, payload: PartnerCreateSchema):
    """Create a new partner."""
    try:
        data = payload.dict()
        data = {k: v for k, v in data.items() if v is not None}
        partner = Partner.objects.create(**data)
        return 201, partner

    except ValidationError as e:
        return 400, {'detail': e.messages[0] if hasattr(e, 'messages') else str(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


@partner_api.put("/{partner_id}", response={200: PartnerSchema, 400: MessageSchema, 404: MessageSchema})
@require_permission("partners", "update")
def update_partner(request, partner_id: int, payload: PartnerUpdateSchema):
    """Update an existing partner."""
    try:
        partner = get_object_or_404(Partner, id=partner_id)
        update_data = payload.dict(exclude_unset=True)

        for field, value in update_data.items():
            if value is not None:
                setattr(partner, field, value)

        partner.save()
        partner.refresh_from_db()
        return 200, partner

    except ValidationError as e:
        return 400, {'detail': e.messages[0] if hasattr(e, 'messages') else str(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


@partner_api.delete("/{partner_id}", response={200: MessageSchema, 404: MessageSchema})
@require_permission("partners", "delete")
def delete_partner(request, partner_id: int):
    """Delete a partner and all associated agreements."""
    try:
        partner = get_object_or_404(Partner, id=partner_id)
        partner.delete()
        return 200, {"detail": "Partner deleted successfully"}

    except ValidationError as e:
        return 400, {'detail': e.messages[0] if hasattr(e, 'messages') else str(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


# ============== Partner Agreements ==============

@partner_api.get("/{partner_id}/agreements", response=List[AgreementSchema])
@paginate(LimitOffsetPagination, page_size=11)
@require_permission("partner_agreements", "list")
def list_agreements(
    request,
    partner_id: int,
    search: Optional[str] = Query(None),
):
    """List all agreements for a partner."""
    get_object_or_404(Partner, id=partner_id)
    agreements = PartnerAgreement.objects.filter(partner_id=partner_id)

    if search:
        agreements = agreements.filter(title__icontains=search)

    return agreements.order_by('-date')


@partner_api.get("/{partner_id}/agreements/{agreement_id}", response={200: AgreementSchema, 404: MessageSchema})
@require_permission("partner_agreements", "view")
def get_agreement(request, partner_id: int, agreement_id: int):
    """Get a specific agreement."""
    try:
        agreement = PartnerAgreement.objects.get(id=agreement_id, partner_id=partner_id)
        return 200, agreement
    except PartnerAgreement.DoesNotExist:
        return 404, {"detail": "Agreement not found"}


@partner_api.post("/{partner_id}/agreements", response={201: AgreementSchema, 400: MessageSchema, 404: MessageSchema})
@require_permission("partner_agreements", "create")
def create_agreement(request, partner_id: int, payload: AgreementCreateSchema):
    """Create a new agreement for a partner."""
    try:
        partner = get_object_or_404(Partner, id=partner_id)

        # Handle document URL
        from urllib.parse import urlparse
        doc_path = payload.document
        if doc_path.startswith('http'):
            parsed = urlparse(doc_path)
            doc_path = parsed.path.lstrip('/')

        agreement = PartnerAgreement.objects.create(
            partner=partner,
            title=payload.title,
            document=doc_path,
            date=payload.date,
        )
        return 201, agreement

    except ValidationError as e:
        return 400, {'detail': e.messages[0] if hasattr(e, 'messages') else str(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


@partner_api.put(
    "/{partner_id}/agreements/{agreement_id}",
    response={200: AgreementSchema, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("partner_agreements", "update")
def update_agreement(request, partner_id: int, agreement_id: int, payload: AgreementUpdateSchema):
    """Update an existing agreement."""
    try:
        agreement = get_object_or_404(PartnerAgreement, id=agreement_id, partner_id=partner_id)
        update_data = payload.dict(exclude_unset=True)

        if 'document' in update_data and update_data['document']:
            from urllib.parse import urlparse
            doc_path = update_data['document']
            if doc_path.startswith('http'):
                parsed = urlparse(doc_path)
                doc_path = parsed.path.lstrip('/')
            if agreement.document:
                agreement.document.delete(save=False)
            update_data['document'] = doc_path

        for field, value in update_data.items():
            if value is not None:
                setattr(agreement, field, value)

        agreement.save()
        agreement.refresh_from_db()
        return 200, agreement

    except ValidationError as e:
        return 400, {'detail': e.messages[0] if hasattr(e, 'messages') else str(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


@partner_api.delete(
    "/{partner_id}/agreements/{agreement_id}",
    response={200: MessageSchema, 404: MessageSchema},
)
@require_permission("partner_agreements", "delete")
def delete_agreement(request, partner_id: int, agreement_id: int):
    """Delete an agreement."""
    try:
        agreement = get_object_or_404(PartnerAgreement, id=agreement_id, partner_id=partner_id)
        if agreement.document:
            agreement.document.delete(save=False)
        agreement.delete()
        return 200, {"detail": "Agreement deleted successfully"}

    except ValidationError as e:
        return 400, {'detail': e.messages[0] if hasattr(e, 'messages') else str(e)}
    except Exception as e:
        return 400, {"detail": str(e)}
