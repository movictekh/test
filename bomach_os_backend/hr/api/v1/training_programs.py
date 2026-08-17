from typing import List, Optional

from django.core.exceptions import ValidationError
from django.db.models import Q
from django.shortcuts import get_object_or_404
from ninja import Query, Router
from ninja.pagination import LimitOffsetPagination, paginate

from hr.api.schemas import (
    MessageSchema,
    TrainingProgramCreateSchema,
    TrainingProgramFilterSchema,
    TrainingProgramListSchema,
    TrainingProgramResponseSchema,
    TrainingProgramUpdateSchema,
)
from hr.models import TrainingProgram
from user.utils.perm import require_permission

router = Router(tags=["Training Programs"])


@router.post("/", response={201: TrainingProgramResponseSchema, 400: MessageSchema})
@require_permission("training_programs", "create")
def create_training_program(request, payload: TrainingProgramCreateSchema):
    """Create a new training program"""
    try:
        program = TrainingProgram.objects.create(**payload.model_dump())
        return 201, program
    except ValidationError as e:
        return 400, {"detail": e.messages[0]}


@router.get("/", response=List[TrainingProgramListSchema])
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("training_programs", "list")
def list_training_programs(
    request,
    search: Optional[str] = Query(None, description="Search by program name"),
    filters: TrainingProgramFilterSchema = Query(...),
):
    """List all training programs with search and filters"""
    programs = TrainingProgram.objects.all()

    if search:
        programs = programs.filter(program_name__icontains=search)

    if filters.program_name:
        programs = programs.filter(program_name__icontains=filters.program_name)
    if filters.provider:
        programs = programs.filter(provider__icontains=filters.provider)
    if filters.status:
        programs = programs.filter(status=filters.status)
    if filters.target_audience:
        programs = programs.filter(target_audience=filters.target_audience)
    if filters.start_date_from:
        programs = programs.filter(start_date__gte=filters.start_date_from)
    if filters.start_date_to:
        programs = programs.filter(start_date__lte=filters.start_date_to)
    if filters.end_date_from:
        programs = programs.filter(end_date__gte=filters.end_date_from)
    if filters.end_date_to:
        programs = programs.filter(end_date__lte=filters.end_date_to)
    if filters.min_cost:
        programs = programs.filter(cost__gte=filters.min_cost)
    if filters.max_cost:
        programs = programs.filter(cost__lte=filters.max_cost)

    return programs


@router.get("/{program_id}", response=TrainingProgramResponseSchema)
@require_permission("training_programs", "view")
def get_training_program(request, program_id: int):
    """Get a single training program by ID"""
    program = get_object_or_404(TrainingProgram, id=program_id)
    return program


@router.put(
    "/{program_id}", response={200: TrainingProgramResponseSchema, 400: MessageSchema}
)
@require_permission("training_programs", "update")
def update_training_program(
    request, program_id: int, payload: TrainingProgramUpdateSchema
):
    """Update a training program"""
    try:
        program = get_object_or_404(TrainingProgram, id=program_id)

        update_data = payload.model_dump(exclude_unset=True)

        # Validate date logic if both dates are being updated
        if "start_date" in update_data and "end_date" in update_data:
            if update_data["end_date"] < update_data["start_date"]:
                raise ValueError("End date must be after start date")
        elif (
            "start_date" in update_data and update_data["start_date"] > program.end_date
        ):
            raise ValueError("Start date cannot be after current end date")
        elif "end_date" in update_data and update_data["end_date"] < program.start_date:
            raise ValueError("End date cannot be before current start date")

        for attr, value in update_data.items():
            setattr(program, attr, value)

        program.save()
        return 200, program
    except ValidationError as e:
        return 400, {"detail": e.messages[0]}


@router.patch(
    "/{program_id}/status",
    response={200: TrainingProgramResponseSchema, 400: MessageSchema},
)
@require_permission("training_programs", "update")
def update_training_program_status(request, program_id: int, status: str = Query(...)):
    """Update only the status of a training program"""
    try:
        program = get_object_or_404(TrainingProgram, id=program_id)

        valid_statuses = ["pending", "in_progress", "completed", "cancelled"]
        if status not in valid_statuses:
            raise ValueError(f'Status must be one of: {", ".join(valid_statuses)}')

        program.status = status
        program.save()
        return 200, program
    except ValidationError as e:
        return 400, {"detail": e.messages[0]}


@router.delete("/{program_id}", response={204: None, 400: MessageSchema})
@require_permission("training_programs", "delete")
def delete_training_program(request, program_id: int):
    """Delete a training program"""
    try:
        program = get_object_or_404(TrainingProgram, id=program_id)
        program.delete()
        return 204, None
    except ValidationError as e:
        return 400, {"detail": e.messages[0]}
