from typing import List
from ninja import Router
from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError
from django.utils import timezone
from ninja.pagination import LimitOffsetPagination, paginate

from hr.models import Applicant, OfferLetter
from hr.api.schemas import (
    OfferLetterCreateSchema,
    OfferLetterUpdateSchema,
    OfferLetterResponseSchema,
    OfferLetterListItemSchema,
    MessageSchema,
)
from user.utils.perm import require_permission, scope_queryset, check_obj_permission


router = Router(tags=['Offer Letters'])


@router.post('/{applicant_id}/offer-letters/', response={201: OfferLetterResponseSchema, 400: MessageSchema})
@require_permission("offer_letters", "create")
def create_offer_letter(request, applicant_id: int, payload: OfferLetterCreateSchema):
    try:
        applicant = get_object_or_404(
            Applicant.objects.select_related('job_posting'),
            id=applicant_id
        )

        applicant.status = 'offered'
        applicant.save(update_fields=['status', 'updated_at'])

        offer = OfferLetter.objects.create(
            applicant=applicant,
            template=payload.template,
            annual_salary=payload.annual_salary,
            start_date=payload.start_date,
            letter_content=payload.letter_content,
            status='sent',
            sent_at = timezone.now()
        )

        return 201, offer
    except ValidationError as e:
        return 400, {'detail': e.messages[0]}


@router.get('/{applicant_id}/offer-letters/', response=List[OfferLetterListItemSchema])
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("offer_letters", "list")
def list_offer_letters(request, applicant_id: int):
    applicant = get_object_or_404(Applicant, id=applicant_id)
    return OfferLetter.objects.filter(applicant=applicant)


@router.get('/{applicant_id}/offer-letters/{offer_id}', response=OfferLetterResponseSchema)
@require_permission("offer_letters", "view")
def get_offer_letter(request, applicant_id: int, offer_id: int):
    offer = get_object_or_404(
        OfferLetter, id=offer_id, applicant_id=applicant_id
    )
    return offer


@router.patch('/{applicant_id}/offer-letters/{offer_id}', response={200: OfferLetterResponseSchema, 400: MessageSchema})
@require_permission("offer_letters", "update")
def update_offer_letter(request, applicant_id: int, offer_id: int, payload: OfferLetterUpdateSchema):
    try:
        offer = get_object_or_404(
            OfferLetter, id=offer_id, applicant_id=applicant_id
        )

        update_data = payload.model_dump(exclude_unset=True)

        # If template/salary/start_date changed and no explicit letter_content, regenerate
        if any(k in update_data for k in ('template', 'annual_salary', 'start_date')) and 'letter_content' not in update_data:
            applicant = Applicant.objects.select_related('job_posting').get(id=applicant_id)
            update_data['letter_content'] = generate_offer_content(
                applicant=applicant,
                template=update_data.get('template', offer.template),
                annual_salary=update_data.get('annual_salary', offer.annual_salary),
                start_date=update_data.get('start_date', offer.start_date),
            )

        for attr, value in update_data.items():
            setattr(offer, attr, value)

        offer.save()
        return 200, offer
    except ValidationError as e:
        return 400, {'detail': e.messages[0]}
