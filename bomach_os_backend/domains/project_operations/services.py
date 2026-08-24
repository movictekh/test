"""State-changing use cases for Project Operations."""

from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404

from domains.project_operations.email import (
    send_associate_task_assignment_email,
    send_task_assignment_email,
)

from .models import Milestone, Project, Task

VALID_TASK_STATUSES = {status for status, _label in Task.STATUS_CHOICES}


def create_project(*, data):
    data = dict(data)
    employee_ids = data.pop("employee_ids", [])
    project = Project.objects.create(**data)

    if employee_ids:
        project.employees.set(employee_ids)

    return project


def update_project(*, project, data):
    data = dict(data)
    employee_ids = data.pop("employee_ids", None)

    for attr, value in data.items():
        setattr(project, attr, value)

    project.save()

    if employee_ids is not None:
        project.employees.set(employee_ids)

    return project


def create_task(*, data, assigned_by_user):
    data = dict(data)
    assigned_to_ids = data.pop("assigned_to", [])

    milestone_id = data.pop("milestone_id", None)
    milestone = (
        get_object_or_404(Milestone, id=milestone_id)
        if milestone_id is not None
        else None
    )

    with transaction.atomic():
        task = Task.objects.create(milestone=milestone, **data)

        if assigned_to_ids:
            task.assigned_to.set(assigned_to_ids)

        transaction.on_commit(
            lambda: _send_task_assignment_notifications(
                task=task,
                assigned_by_user=assigned_by_user,
            )
        )

    return task


def update_task(*, task, data):
    data = dict(data)
    assigned_to_ids = data.pop("assigned_to", None)

    if "milestone_id" in data:
        milestone_id = data.pop("milestone_id")
        task.milestone = (
            get_object_or_404(Milestone, id=milestone_id)
            if milestone_id is not None
            else None
        )

    for attr, value in data.items():
        setattr(task, attr, value)

    task.save()

    if assigned_to_ids is not None:
        task.assigned_to.set(assigned_to_ids)

    return task


def update_owned_task_status(*, task, status):
    if status not in VALID_TASK_STATUSES:
        valid = ", ".join(VALID_TASK_STATUSES)
        raise ValueError(f"Invalid status. Must be one of: {valid}")

    task.status = status
    task.save()
    return task


def _send_task_assignment_notifications(*, task, assigned_by_user):
    domain = settings.DOMAIN
    project_name = (
        task.milestone.project.name
        if task.milestone and task.milestone.project
        else "N/A"
    )
    assigned_by_name = assigned_by_user.get_full_name() or assigned_by_user.email

    for employee in task.assigned_to.select_related("user").all():
        due_date = (
            task.due_date.strftime("%B %d, %Y") if task.due_date else "No due date"
        )

        if employee.is_associate():
            response = send_associate_task_assignment_email(
                recipient=employee.user.email,
                associate_name=employee.user.first_name,
                task_title=task.name,
                project_name=project_name,
                assigned_by=assigned_by_name,
                due_date=due_date,
                task_link=f"{domain}/api/v1/my-tasks/{task.id}",
            )
        else:
            response = send_task_assignment_email(
                recipient=employee.user.email,
                assignee_name=employee.user.first_name,
                task_title=task.name,
                task_description=task.description,
                due_date=due_date,
                task_url=f"{domain}/api/v1/my-tasks/{task.id}",
            )

        if response.status_code not in (200, 201):
            print(
                "Warning: Task email could not be sent to "
                f"{employee.user.email}. Response: "
                f"{response.status_code} - {response.text}"
            )
