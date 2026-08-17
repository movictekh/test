from typing import List, Optional

from django.core.exceptions import ValidationError
from django.db.models import Q
from django.shortcuts import get_object_or_404
from ninja import Router
from ninja.pagination import LimitOffsetPagination, paginate

from hr.api.schemas import (
    JobPostingCreateSchema,
    JobPostingListItemSchema,
    JobPostingResponseSchema,
    JobPostingStatusUpdateSchema,
    JobPostingUpdateSchema,
    MessageSchema,
)
from hr.models import JobPosting
from user.utils.perm import check_obj_permission, require_permission, scope_queryset

router = Router(tags=["Job Postings"])


@router.get("/", response=List[JobPostingListItemSchema])
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("job_postings", "list")
def list_job_postings(
    request,
    search: Optional[str] = None,
    branch_id: Optional[int] = None,
    status: Optional[str] = None,
    job_type: Optional[str] = None,
    department_id: Optional[int] = None,
    is_active: Optional[bool] = None,
):
    queryset = JobPosting.objects.all()

    # Search functionality
    if search:
        queryset = queryset.filter(Q(job_title__icontains=search))

    # Filters
    if branch_id:
        queryset = queryset.filter(branch_id=branch_id)

    if status:
        queryset = queryset.filter(status=status)

    if job_type:
        queryset = queryset.filter(job_type=job_type)

    if department_id:
        queryset = queryset.filter(department_id=department_id)

    if is_active is not None:
        queryset = queryset.filter(is_active=is_active)

    return queryset


@router.get("/{job_posting_id}", response=JobPostingResponseSchema)
@require_permission("job_postings", "view")
def get_job_posting(request, job_posting_id: int):
    """
    Get a single job posting by ID.
    """
    job_posting = get_object_or_404(JobPosting, id=job_posting_id)
    return job_posting


@router.post("/", response={201: JobPostingResponseSchema, 400: MessageSchema})
@require_permission("job_postings", "create")
def create_job_posting(request, payload: JobPostingCreateSchema):
    """
    Create a new job posting.
    """
    try:
        data = payload.model_dump()
        job_posting = JobPosting.objects.create(**data)
        return 201, job_posting
    except ValidationError as e:
        return 400, {"detail": e.messages[0]}


@router.put(
    "/{job_posting_id}", response={200: JobPostingResponseSchema, 400: MessageSchema}
)
@require_permission("job_postings", "update")
def update_job_posting(request, job_posting_id: int, payload: JobPostingUpdateSchema):
    """
    Update a job posting (full update).
    """
    try:
        job_posting = get_object_or_404(JobPosting, id=job_posting_id)

        update_data = payload.model_dump(exclude_unset=True)

        for attr, value in update_data.items():
            setattr(job_posting, attr, value)

        job_posting.save()
        return 200, job_posting
    except ValidationError as e:
        return 400, {"detail": e.messages[0]}


@router.patch(
    "/{job_posting_id}/status",
    response={200: JobPostingResponseSchema, 400: MessageSchema},
)
@require_permission("job_postings", "update_status")
def update_job_posting_status(
    request, job_posting_id: int, payload: JobPostingStatusUpdateSchema
):
    """
    Update only the status of a job posting.
    """
    try:
        job_posting = get_object_or_404(JobPosting, id=job_posting_id)
        job_posting.status = payload.status
        job_posting.save(update_fields=["status", "updated_at"])
        return 200, job_posting
    except ValidationError as e:
        return 400, {"detail": e.messages[0]}


@router.delete(
    "/{job_posting_id}", response={200: MessageSchema, 204: None, 400: MessageSchema}
)
@require_permission("job_postings", "delete")
def delete_job_posting(request, job_posting_id: int):
    """
    Delete a job posting.
    """
    try:
        job_posting = get_object_or_404(JobPosting, id=job_posting_id)
        job_posting.delete()
        return 200, {
            "detail": f'Job posting "{job_posting.job_title}" deleted successfully'
        }
    except ValidationError as e:
        return 400, {"detail": e.messages[0]}


@router.get("/stats/summary", response=dict)
@require_permission("job_postings", "list")
def get_job_postings_summary(request):
    """
    Get summary statistics for job postings.
    """
    total = JobPosting.objects.count()
    active = JobPosting.objects.filter(status="active").count()
    pending = JobPosting.objects.filter(status="pending").count()
    closed = JobPosting.objects.filter(status="closed").count()
    draft = JobPosting.objects.filter(status="draft").count()

    return {
        "total": total,
        "active": active,
        "pending": pending,
        "closed": closed,
        "draft": draft,
    }
