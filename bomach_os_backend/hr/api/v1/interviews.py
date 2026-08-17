from typing import List

from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from ninja import Router
from ninja.pagination import LimitOffsetPagination, paginate

from hr.api.schemas import (
    InterviewCreateSchema,
    InterviewFeedbackSchema,
    InterviewListItemSchema,
    InterviewResponseSchema,
    InterviewUpdateSchema,
    MessageSchema,
)
from hr.models import Applicant, Interview
from user.utils.perm import check_obj_permission, require_permission, scope_queryset

router = Router(tags=["Interviews"])


@router.post(
    "/{applicant_id}/interviews/",
    response={201: InterviewResponseSchema, 400: MessageSchema},
)
@require_permission("interviews", "create")
def create_interview(request, applicant_id: int, payload: InterviewCreateSchema):
    try:
        applicant = get_object_or_404(Applicant, id=applicant_id)

        interview = Interview.objects.create(
            applicant=applicant,
            interviewer_id=payload.interviewer_id,
            scheduled_at=payload.scheduled_at,
            meeting_link=payload.meeting_link,
        )

        # Update applicant status to interviewed
        if applicant.status in ("applied", "shortlisted"):
            applicant.status = "interviewed"
            applicant.save(update_fields=["status", "updated_at"])

        return 201, interview
    except ValidationError as e:
        return 400, {"detail": e.messages[0]}


@router.get("/{applicant_id}/interviews/", response=List[InterviewListItemSchema])
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("interviews", "list")
def list_interviews(request, applicant_id: int):
    applicant = get_object_or_404(Applicant, id=applicant_id)
    return Interview.objects.filter(applicant=applicant)


@router.get(
    "/{applicant_id}/interviews/{interview_id}", response=InterviewResponseSchema
)
@require_permission("interviews", "view")
def get_interview(request, applicant_id: int, interview_id: int):
    interview = get_object_or_404(Interview, id=interview_id, applicant_id=applicant_id)
    return interview


@router.patch(
    "/{applicant_id}/interviews/{interview_id}",
    response={200: InterviewResponseSchema, 400: MessageSchema},
)
@require_permission("interviews", "update")
def update_interview(
    request, applicant_id: int, interview_id: int, payload: InterviewUpdateSchema
):
    try:
        interview = get_object_or_404(
            Interview, id=interview_id, applicant_id=applicant_id
        )

        update_data = payload.model_dump(exclude_unset=True)

        for attr, value in update_data.items():
            setattr(interview, attr, value)

        interview.save()
        return 200, interview
    except ValidationError as e:
        return 400, {"detail": e.messages[0]}


@router.patch(
    "/{applicant_id}/interviews/{interview_id}/feedback",
    response={200: InterviewResponseSchema, 400: MessageSchema},
)
@require_permission("interviews", "update")
def submit_feedback(
    request, applicant_id: int, interview_id: int, payload: InterviewFeedbackSchema
):
    try:
        interview = get_object_or_404(
            Interview, id=interview_id, applicant_id=applicant_id
        )

        interview.feedback = payload.feedback
        if payload.status:
            interview.status = payload.status
        interview.save()
        return 200, interview
    except ValidationError as e:
        return 400, {"detail": e.messages[0]}


@router.delete(
    "/{applicant_id}/interviews/{interview_id}",
    response={200: MessageSchema, 400: MessageSchema},
)
@require_permission("interviews", "delete")
def delete_interview(request, applicant_id: int, interview_id: int):
    try:
        interview = get_object_or_404(
            Interview, id=interview_id, applicant_id=applicant_id
        )
        interview.delete()
        return 200, {"detail": "Interview deleted successfully"}
    except ValidationError as e:
        return 400, {"detail": e.messages[0]}
