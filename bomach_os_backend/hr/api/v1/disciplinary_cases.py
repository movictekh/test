from typing import List
from ninja import Router
from ninja.pagination import paginate, LimitOffsetPagination
from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError
from hr.models.disciplinary_case import DisciplinaryCase
from hr.api.schemas.disciplinary_case import (
    DisciplinaryCaseSchema,
    DisciplinaryCaseCreateSchema,
    DisciplinaryCaseUpdateSchema,
)
from hr.api.schemas import MessageSchema
from user.utils.perm import require_permission, scope_queryset, check_obj_permission

router = Router(tags=["Disciplinary Cases"])


@router.post("/", response={201: DisciplinaryCaseSchema, 400: MessageSchema})
@require_permission("disciplinary_cases", "create")
def create_disciplinary_case(request, payload: DisciplinaryCaseCreateSchema):
    try:
        data = payload.model_dump(exclude_unset=True)
        case = DisciplinaryCase.objects.create(**data)
        return 201, case
    except ValidationError as e:
        return 400, {'detail': e.messages[0]}
    except Exception as e:
        return 400, {'detail': str(e)}


@router.get("/", response=List[DisciplinaryCaseSchema])
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("disciplinary_cases", "list", owner_lookup="employee__user")
def list_disciplinary_cases(
    request,
    employee_id: int = None,
    action_type: str = None,
    violation_category: str = None,
):
    qs = DisciplinaryCase.objects.all()
    if employee_id:
        qs = qs.filter(employee_id=employee_id)
    if action_type:
        qs = qs.filter(action_type=action_type)
    if violation_category:
        qs = qs.filter(violation_category=violation_category)
    qs = scope_queryset(request, qs, owner_field="employee__user",
                        branch_field="employee__branch",
                        department_field="employee__department")
    return qs


@router.get("/{case_id}", response=DisciplinaryCaseSchema)
@require_permission("disciplinary_cases", "view", owner_lookup="employee__user")
def get_disciplinary_case(request, case_id: int):
    case = get_object_or_404(DisciplinaryCase, id=case_id)
    check_obj_permission(request, case, owner_field="employee.user")
    return case


@router.put("/{case_id}", response={200: DisciplinaryCaseSchema, 400: MessageSchema})
@require_permission("disciplinary_cases", "update")
def update_disciplinary_case(
    request, case_id: int, payload: DisciplinaryCaseUpdateSchema
):
    try:
        case = get_object_or_404(DisciplinaryCase, id=case_id)
        for attr, value in payload.model_dump(exclude_unset=True).items():
            setattr(case, attr, value)
        case.save()
        return 200, case
    except ValidationError as e:
        return 400, {'detail': e.messages[0]}


@router.delete("/{case_id}", response={200: MessageSchema, 400: MessageSchema})
@require_permission("disciplinary_cases", "delete")
def delete_disciplinary_case(request, case_id: int):
    try:
        case = get_object_or_404(DisciplinaryCase, id=case_id)
        case.delete()
        return 200, {"detail": "Deleted successfully"}
    except ValidationError as e:
        return 400, {'detail': e.messages[0]}
