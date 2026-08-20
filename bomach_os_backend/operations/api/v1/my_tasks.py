from ninja import Router
from typing import List
from django.shortcuts import get_object_or_404
from ninja.errors import HttpError
from ninja.pagination import paginate, LimitOffsetPagination

from operations.models import Task
from ..schema.schemas import TaskOutSchema, TaskStatusUpdateSchema, MessageSchema
from user.utils.perm import require_permission

router = Router(tags=["My Tasks"])

VALID_STATUSES = {s[0] for s in Task.STATUS_CHOICES}


@router.get("", response=List[TaskOutSchema])
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("tasks", "list", owner_lookup="assigned_to")
def list_my_tasks(request, status: str = None, ):
    """List tasks assigned to the logged-in employee, with optional status filter."""
    employee = request._perm_employee
    tasks = Task.objects.filter(assigned_to=employee)

    if status:
        tasks = tasks.filter(status=status).order_by('due_date', '-priority')

    return list(tasks)


@router.get("/{task_id}", response=TaskOutSchema)
@require_permission("tasks", "view", owner_lookup="assigned_to")
def get_my_task(request, task_id: int):
    """Get a specific task assigned to the logged-in employee."""
    employee = request._perm_employee
    task = get_object_or_404(Task, id=task_id)

    if not task.assigned_to.filter(id=employee.id).exists():
        raise HttpError(403, "You do not have permission to access this task.")

    return task


@router.patch("/{task_id}/status", response={200: TaskOutSchema, 400: MessageSchema})
@require_permission("tasks", "update", owner_lookup="assigned_to")
def update_my_task_status(request, task_id: int, payload: TaskStatusUpdateSchema):
    """Update only the status of a task assigned to the logged-in employee."""
    employee = request._perm_employee
    task = get_object_or_404(Task, id=task_id)

    if not task.assigned_to.filter(id=employee.id).exists():
        raise HttpError(403, "You do not have permission to update this task.")

    if payload.status not in VALID_STATUSES:
        return 400, {"detail": f"Invalid status. Must be one of: {', '.join(VALID_STATUSES)}"}

    task.status = payload.status
    task.save()
    return task
