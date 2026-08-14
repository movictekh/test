from typing import List

from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from ninja import Router
from ninja.pagination import LimitOffsetPagination, paginate

from domains.project_operations import selectors, services
from domains.project_operations.models import Task
from user.utils.perm import require_permission

from ..schemas.schemas import MessageSchema, TaskCreateSchema, TaskOutSchema, TaskUpdateSchema

router = Router(tags=["Tasks"])


@router.get("", response=List[TaskOutSchema], operation_id="operations_api_v1_tasks_list_tasks")
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("tasks", "list")
def list_tasks(request, project_id: int = None, milestone_id: int = None, status: str = None, priority: str = None, search: str = None):
    return list(
        selectors.list_tasks(
            project_id=project_id,
            milestone_id=milestone_id,
            status=status,
            priority=priority,
            search=search,
        )
    )


@router.get("/{task_id}", response=TaskOutSchema, operation_id="operations_api_v1_tasks_get_task")
@require_permission("tasks", "view")
def get_task(request, task_id: int):
    return get_object_or_404(Task, id=task_id)


@router.post("", response={201: TaskOutSchema, 400: MessageSchema}, operation_id="operations_api_v1_tasks_create_task")
@require_permission("tasks", "create")
def create_task(request, payload: TaskCreateSchema):
    try:
        task = services.create_task(
            data=payload.dict(),
            assigned_by_user=request.user,
        )
        return 201, task
    except ValidationError as exc:
        return 400, {"detail": exc.messages[0]}


@router.put("/{task_id}", response={200: TaskOutSchema, 400: MessageSchema}, operation_id="operations_api_v1_tasks_update_task")
@require_permission("tasks", "update")
def update_task(request, task_id: int, payload: TaskUpdateSchema):
    try:
        task = get_object_or_404(Task, id=task_id)
        return services.update_task(
            task=task,
            data=payload.dict(exclude_unset=True),
        )
    except ValidationError as exc:
        return 400, {"detail": exc.messages[0]}


@router.delete("/{task_id}", operation_id="operations_api_v1_tasks_delete_task")
@require_permission("tasks", "delete")
def delete_task(request, task_id: int):
    task = get_object_or_404(Task, id=task_id)
    task.delete()
    return {"detail": "Task deleted successfully"}
