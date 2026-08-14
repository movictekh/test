from ninja import Router
from typing import List
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.core.exceptions import ValidationError
from ninja.errors import HttpError
from django.db import transaction
from domains.project_operations.models import Milestone, Task, Project
from ..schemas.schemas import TaskCreateSchema, TaskUpdateSchema, TaskOutSchema, MessageSchema
from ninja.pagination import paginate, LimitOffsetPagination
from user.utils.perm import require_permission
from user.utils.send_email import send_task_assignment_email, send_associate_task_assignment_email
from django.conf import settings

router = Router(tags=["Tasks"])

DOMAIN = settings.DOMAIN

@router.get("", response=List[TaskOutSchema], operation_id="operations_api_v1_tasks_list_tasks")
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("tasks", "list")
def list_tasks(
    request,
    project_id: int = None,
    milestone_id: int = None,
    status: str = None,
    priority: str = None,
    search: str = None,
):
    """List all tasks with optional filters"""
    tasks = Task.objects.all()

    if project_id:
        tasks = tasks.filter(milestone__project_id=project_id)
    if milestone_id:
        tasks = tasks.filter(milestone_id=milestone_id)
    if status:
        tasks = tasks.filter(status=status)
    if priority:
        tasks = tasks.filter(priority=priority)
    if search:
        tasks = tasks.filter(
            Q(name__icontains=search) |
            Q(description__icontains=search)
        )

    return list(tasks)


@router.get("/{task_id}", response=TaskOutSchema, operation_id="operations_api_v1_tasks_get_task")
@require_permission("tasks", "view")
def get_task(request, task_id: int):
    """Get a specific task by ID"""
    task = get_object_or_404(Task, id=task_id)
    return task


@router.post("", response={201: TaskOutSchema, 400: MessageSchema}, operation_id="operations_api_v1_tasks_create_task")
@require_permission("tasks", "create")
def create_task(request, payload: TaskCreateSchema):
    """Create a new task"""
    try:
        with transaction.atomic():
            task_data = payload.dict()
            assigned_to_ids = task_data.pop('assigned_to', [])
            if 'milestone_id' in task_data and task_data['milestone_id'] is not None:
                milestone = get_object_or_404(Milestone, id=task_data.pop('milestone_id'))
            else:
                task_data.pop('milestone_id', None)
                milestone = None
            task = Task.objects.create(milestone=milestone, **task_data)
            if assigned_to_ids:
                task.assigned_to.set(assigned_to_ids)

            def send_email():
                project_name = task.milestone.project.name if task.milestone and task.milestone.project else "N/A"
                assigned_by_name = request.user.get_full_name() or request.user.email

                for employee in task.assigned_to.select_related('user').all():
                    due_date_str = task.due_date.strftime("%B %d, %Y") if task.due_date else "No due date"

                    if employee.is_associate():
                        res = send_associate_task_assignment_email(
                            recipient=employee.user.email,
                            associate_name=employee.user.first_name,
                            task_title=task.name,
                            project_name=project_name,
                            assigned_by=assigned_by_name,
                            due_date=due_date_str,
                            task_link=f"{DOMAIN}/api/v1/my-tasks/{task.id}",
                        )
                    else:
                        res = send_task_assignment_email(
                            recipient=employee.user.email,
                            assignee_name=employee.user.first_name,
                            task_title=task.name,
                            task_description=task.description,
                            due_date=due_date_str,
                            task_url=f"{DOMAIN}/api/v1/my-tasks/{task.id}",
                        )

                    if res.status_code not in [200, 201]:
                        print(f"Warning: Task email could not be sent to {employee.user.email}. Response: {res.status_code} - {res.text}")
            transaction.on_commit(send_email)
            return 201, task
    except ValidationError as e:
        return 400, {'detail': e.messages[0]}


@router.put("/{task_id}", response={200: TaskOutSchema, 400: MessageSchema}, operation_id="operations_api_v1_tasks_update_task")
@require_permission("tasks", "update")
def update_task(request, task_id: int, payload: TaskUpdateSchema):
    """Update an existing task"""
    try:
        task = get_object_or_404(Task, id=task_id)

        update_data = payload.dict(exclude_unset=True)
        assigned_to_ids = update_data.pop('assigned_to', None)

        if 'milestone_id' in update_data:
            milestone = get_object_or_404(Milestone, id=update_data.pop('milestone_id'))
            task.milestone = milestone

        for attr, value in update_data.items():
            setattr(task, attr, value)

        task.save()

        if assigned_to_ids is not None:
            task.assigned_to.set(assigned_to_ids)

        return task
    except ValidationError as e:
        return 400, {'detail': e.messages[0]}


@router.delete("/{task_id}", operation_id="operations_api_v1_tasks_delete_task")
@require_permission("tasks", "delete")
def delete_task(request, task_id: int):
    """Delete a task"""
    task = get_object_or_404(Task, id=task_id)
    task.delete()
    return {"detail": "Task deleted successfully"}
