from typing import List

from django.shortcuts import get_object_or_404
from ninja import Router
from ninja.errors import HttpError
from ninja.pagination import LimitOffsetPagination, paginate

from domains.project_operations import selectors, services
from domains.project_operations.models import Task
from user.utils.perm import require_permission

from ..schemas.schemas import MessageSchema, TaskOutSchema, TaskStatusUpdateSchema

router = Router(tags=["My Tasks"])


@router.get("", response=List[TaskOutSchema], operation_id="operations_api_v1_my_tasks_list_my_tasks")
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("tasks", "list", owner_lookup="assigned_to")
def list_my_tasks(request, status: str = None):
    return list(
        selectors.list_employee_tasks(
            employee=request._perm_employee,
            status=status,
        )
    )


@router.get("/{task_id}", response=TaskOutSchema, operation_id="operations_api_v1_my_tasks_get_my_task")
@require_permission("tasks", "view", owner_lookup="assigned_to")
def get_my_task(request, task_id: int):
    employee = request._perm_employee
    task = get_object_or_404(Task, id=task_id)

    if not selectors.employee_owns_task(task=task, employee=employee):
        raise HttpError(403, "You do not have permission to access this task.")

    return task


@router.patch("/{task_id}/status", response={200: TaskOutSchema, 400: MessageSchema}, operation_id="operations_api_v1_my_tasks_update_my_task_status")
@require_permission("tasks", "update", owner_lookup="assigned_to")
def update_my_task_status(request, task_id: int, payload: TaskStatusUpdateSchema):
    employee = request._perm_employee
    task = get_object_or_404(Task, id=task_id)

    if not selectors.employee_owns_task(task=task, employee=employee):
        raise HttpError(403, "You do not have permission to update this task.")

    try:
        return services.update_owned_task_status(task=task, status=payload.status)
    except ValueError as exc:
        return 400, {"detail": str(exc)}
