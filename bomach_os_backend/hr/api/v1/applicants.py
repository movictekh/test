from typing import List, Optional

from django.core.exceptions import ValidationError
from django.db.models import Q
from django.shortcuts import get_object_or_404
from ninja import Router
from ninja.pagination import LimitOffsetPagination, paginate

from hr.api.schemas import (
    ApplicantCreateSchema,
    ApplicantListItemSchema,
    ApplicantResponseSchema,
    ApplicantStatusUpdateSchema,
    ApplicantUpdateSchema,
    MessageSchema,
)
from hr.models import Applicant, JobPosting
from system.authorization import check_obj_permission, require_permission, scope_queryset

router = Router(tags=["Applicants"])


@router.get("/", response=List[ApplicantListItemSchema])
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("applicants", "list")
def list_applicants(
    request,
    search: Optional[str] = None,
    job_posting_id: Optional[int] = None,
    status: Optional[str] = None,
):
    queryset = Applicant.objects.select_related("job_posting").all()

    if search:
        queryset = queryset.filter(
            Q(first_name__icontains=search)
            | Q(last_name__icontains=search)
            | Q(email__icontains=search)
            | Q(phone__icontains=search)
            | Q(job_posting__job_title__icontains=search)
        )

    if job_posting_id:
        queryset = queryset.filter(job_posting_id=job_posting_id)

    if status:
        queryset = queryset.filter(status=status)

    return queryset


@router.get("/{applicant_id}", response=ApplicantResponseSchema)
@require_permission("applicants", "view")
def get_applicant(request, applicant_id: int):
    """
    Get a single applicant by ID.
    """
    applicant = get_object_or_404(
        Applicant.objects.select_related("job_posting", "job_posting__department"),
        id=applicant_id,
    )
    return applicant


@router.post("/", response={201: ApplicantResponseSchema, 400: MessageSchema})
@require_permission("applicants", "create")
def create_applicant(request, payload: ApplicantCreateSchema):
    """
    Create a new applicant.
    """
    try:
        data = payload.model_dump(exclude={"job_posting_id"})

        # Get the job posting
        job_posting = get_object_or_404(JobPosting, id=payload.job_posting_id)
        data["job_posting"] = job_posting

        applicant = Applicant.objects.create(**data)

        return 201, applicant
    except ValidationError as e:
        return 400, {"detail": e.messages[0]}


@router.put(
    "/{applicant_id}", response={200: ApplicantResponseSchema, 400: MessageSchema}
)
@require_permission("applicants", "update")
def update_applicant(request, applicant_id: int, payload: ApplicantUpdateSchema):
    """
    Update an applicant (full update).
    """
    try:
        applicant = get_object_or_404(Applicant, id=applicant_id)

        update_data = payload.model_dump(exclude_unset=True)

        for attr, value in update_data.items():
            setattr(applicant, attr, value)

        applicant.save()
        return 200, applicant
    except ValidationError as e:
        return 400, {"detail": e.messages[0]}


@router.patch(
    "/{applicant_id}/status",
    response={200: ApplicantResponseSchema, 400: MessageSchema},
)
@require_permission("applicants", "update_status")
def update_applicant_status(
    request, applicant_id: int, payload: ApplicantStatusUpdateSchema
):
    """
    Update only the status of an applicant.
    """
    try:
        applicant = get_object_or_404(Applicant, id=applicant_id)
        applicant.status = payload.status
        applicant.save(update_fields=["status", "updated_at"])
        return 200, applicant
    except ValidationError as e:
        return 400, {"detail": e.messages[0]}


@router.delete(
    "/{applicant_id}", response={200: MessageSchema, 204: None, 400: MessageSchema}
)
@require_permission("applicants", "delete")
def delete_applicant(request, applicant_id: int):
    """
    Delete an applicant.
    """
    try:
        applicant = get_object_or_404(Applicant, id=applicant_id)
        job_posting = applicant.job_posting
        applicant_name = applicant.full_name

        applicant.delete()

        # Decrement job posting applicants count
        job_posting.decrement_applicants()

        return 200, {"detail": f'Applicant "{applicant_name}" deleted successfully'}
    except ValidationError as e:
        return 400, {"detail": e.messages[0]}
