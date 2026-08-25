"""Project execution HTTP endpoints: tasks, employee tasks, worksites and equipment."""

# --------------------------------------------------------------------------
# Task administration
# --------------------------------------------------------------------------

from typing import List

from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from ninja import Router
from ninja.pagination import LimitOffsetPagination, paginate

from domains.project_operations import selectors, services
from domains.project_operations.models import Task
from system.authorization import require_permission

from ..schemas.schemas import (
    MessageSchema,
    TaskCreateSchema,
    TaskOutSchema,
    TaskUpdateSchema,
)

tasks_router = Router(tags=["Tasks"])


@tasks_router.get(
    "", response=List[TaskOutSchema], operation_id="operations_api_v1_tasks_list_tasks"
)
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
    return list(
        selectors.list_tasks(
            project_id=project_id,
            milestone_id=milestone_id,
            status=status,
            priority=priority,
            search=search,
        )
    )


@tasks_router.get(
    "/{task_id}",
    response=TaskOutSchema,
    operation_id="operations_api_v1_tasks_get_task",
)
@require_permission("tasks", "view")
def get_task(request, task_id: int):
    return get_object_or_404(Task, id=task_id)


@tasks_router.post(
    "",
    response={201: TaskOutSchema, 400: MessageSchema},
    operation_id="operations_api_v1_tasks_create_task",
)
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


@tasks_router.put(
    "/{task_id}",
    response={200: TaskOutSchema, 400: MessageSchema},
    operation_id="operations_api_v1_tasks_update_task",
)
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


@tasks_router.delete("/{task_id}", operation_id="operations_api_v1_tasks_delete_task")
@require_permission("tasks", "delete")
def delete_task(request, task_id: int):
    task = get_object_or_404(Task, id=task_id)
    task.delete()
    return {"detail": "Task deleted successfully"}


# --------------------------------------------------------------------------
# Employee-owned task view
# --------------------------------------------------------------------------

from typing import List

from django.shortcuts import get_object_or_404
from ninja import Router
from ninja.errors import HttpError
from ninja.pagination import LimitOffsetPagination, paginate

from domains.project_operations import selectors, services
from domains.project_operations.models import Task
from system.authorization import require_permission

from ..schemas.schemas import MessageSchema, TaskOutSchema, TaskStatusUpdateSchema

my_tasks_router = Router(tags=["My Tasks"])


@my_tasks_router.get(
    "",
    response=List[TaskOutSchema],
    operation_id="operations_api_v1_my_tasks_list_my_tasks",
)
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("tasks", "list", owner_lookup="assigned_to")
def list_my_tasks(request, status: str = None):
    return list(
        selectors.list_employee_tasks(
            employee=request._perm_employee,
            status=status,
        )
    )


@my_tasks_router.get(
    "/{task_id}",
    response=TaskOutSchema,
    operation_id="operations_api_v1_my_tasks_get_my_task",
)
@require_permission("tasks", "view", owner_lookup="assigned_to")
def get_my_task(request, task_id: int):
    employee = request._perm_employee
    task = get_object_or_404(Task, id=task_id)

    if not selectors.employee_owns_task(task=task, employee=employee):
        raise HttpError(403, "You do not have permission to access this task.")

    return task


@my_tasks_router.patch(
    "/{task_id}/status",
    response={200: TaskOutSchema, 400: MessageSchema},
    operation_id="operations_api_v1_my_tasks_update_my_task_status",
)
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


# --------------------------------------------------------------------------
# Worksites
# --------------------------------------------------------------------------

from typing import List

from django.core.exceptions import ValidationError
from django.db.models import Q
from django.shortcuts import get_object_or_404
from ninja import Router
from ninja.pagination import LimitOffsetPagination, paginate

from domains.project_operations.models import Project, Worksite
from system.authorization import require_permission

from ..schemas.schemas import (
    MessageSchema,
    WorksiteCreateSchema,
    WorksiteOutSchema,
    WorksiteUpdateSchema,
)

worksites_router = Router(tags=["Worksites"])


@worksites_router.get(
    "",
    response=List[WorksiteOutSchema],
    operation_id="operations_api_v1_worksites_list_worksites",
)
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("worksites", "list")
def list_worksites(
    request,
    project_id: int = None,
    status: str = None,
    search: str = None,
):
    """List all worksites with optional filters"""
    worksites = Worksite.objects.all()

    if project_id:
        worksites = worksites.filter(project_id=project_id)
    if status:
        worksites = worksites.filter(status=status)
    if search:
        worksites = worksites.filter(
            Q(name__icontains=search) | Q(location__icontains=search)
        )

    return list(worksites)


@worksites_router.get(
    "/{worksite_id}",
    response=WorksiteOutSchema,
    operation_id="operations_api_v1_worksites_get_worksite",
)
@require_permission("worksites", "view")
def get_worksite(request, worksite_id: int):
    """Get a specific worksite by ID"""
    worksite = get_object_or_404(Worksite, id=worksite_id)
    return worksite


@worksites_router.post(
    "",
    response={200: WorksiteOutSchema, 400: MessageSchema},
    operation_id="operations_api_v1_worksites_create_worksite",
)
@require_permission("worksites", "create")
def create_worksite(request, payload: WorksiteCreateSchema):
    """Create a new worksite"""
    try:
        worksite_data = payload.dict()
        project = get_object_or_404(Project, id=worksite_data.pop("project_id"))
        worksite = Worksite.objects.create(project=project, **worksite_data)
        return worksite
    except ValidationError as e:
        return 400, {"detail": e.messages[0]}


@worksites_router.put(
    "/{worksite_id}",
    response={200: WorksiteOutSchema, 400: MessageSchema},
    operation_id="operations_api_v1_worksites_update_worksite",
)
@require_permission("worksites", "update")
def update_worksite(request, worksite_id: int, payload: WorksiteUpdateSchema):
    """Update an existing worksite"""
    try:
        worksite = get_object_or_404(Worksite, id=worksite_id)

        update_data = payload.dict(exclude_unset=True)
        if "project_id" in update_data:
            project = get_object_or_404(Project, id=update_data.pop("project_id"))
            worksite.project = project

        for attr, value in update_data.items():
            setattr(worksite, attr, value)

        worksite.save()
        return worksite
    except ValidationError as e:
        return 400, {"detail": e.messages[0]}


@worksites_router.delete(
    "/{worksite_id}", operation_id="operations_api_v1_worksites_delete_worksite"
)
@require_permission("worksites", "delete")
def delete_worksite(request, worksite_id: int):
    """Delete a worksite"""
    worksite = get_object_or_404(Worksite, id=worksite_id)
    worksite.delete()
    return {"detail": "Worksite deleted successfully"}


# --------------------------------------------------------------------------
# Site equipment
# --------------------------------------------------------------------------

from typing import List

from django.core.exceptions import ValidationError
from django.db.models import Q
from django.shortcuts import get_object_or_404
from ninja import Router
from ninja.pagination import LimitOffsetPagination, paginate

from domains.project_operations.models import SiteEquipment, Worksite
from system.authorization import require_permission

from ..schemas.schemas import (
    MessageSchema,
    SiteEquipmentCreateSchema,
    SiteEquipmentOutSchema,
    SiteEquipmentUpdateSchema,
)

site_equipment_router = Router(tags=["Site Equipment"])


@site_equipment_router.get(
    "",
    response=List[SiteEquipmentOutSchema],
    operation_id="operations_api_v1_site_equipment_list_site_equipment",
)
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("site_equipment", "list")
def list_site_equipment(
    request,
    worksite_id: int = None,
    search: str = None,
):
    """List all site equipment with optional filters"""
    equipment = SiteEquipment.objects.all()

    if worksite_id:
        equipment = equipment.filter(worksite_id=worksite_id)
    if search:
        equipment = equipment.filter(
            Q(name__icontains=search) | Q(unit_value__icontains=search)
        )

    return list(equipment)


@site_equipment_router.get(
    "/{equipment_id}",
    response=SiteEquipmentOutSchema,
    operation_id="operations_api_v1_site_equipment_get_site_equipment",
)
@require_permission("site_equipment", "view")
def get_site_equipment(request, equipment_id: int):
    """Get a specific site equipment item by ID"""
    equipment = get_object_or_404(SiteEquipment, id=equipment_id)
    return equipment


@site_equipment_router.post(
    "",
    response={200: SiteEquipmentOutSchema, 400: MessageSchema},
    operation_id="operations_api_v1_site_equipment_create_site_equipment",
)
@require_permission("site_equipment", "create")
def create_site_equipment(request, payload: SiteEquipmentCreateSchema):
    """Create a new site equipment item"""
    try:
        equipment_data = payload.dict()
        worksite = get_object_or_404(Worksite, id=equipment_data.pop("worksite_id"))
        equipment = SiteEquipment.objects.create(worksite=worksite, **equipment_data)
        return equipment
    except ValidationError as e:
        return 400, {"detail": e.messages[0]}


@site_equipment_router.put(
    "/{equipment_id}",
    response={200: SiteEquipmentOutSchema, 400: MessageSchema},
    operation_id="operations_api_v1_site_equipment_update_site_equipment",
)
@require_permission("site_equipment", "update")
def update_site_equipment(
    request, equipment_id: int, payload: SiteEquipmentUpdateSchema
):
    """Update an existing site equipment item"""
    try:
        equipment = get_object_or_404(SiteEquipment, id=equipment_id)

        update_data = payload.dict(exclude_unset=True)
        if "worksite_id" in update_data:
            worksite = get_object_or_404(Worksite, id=update_data.pop("worksite_id"))
            equipment.worksite = worksite

        for attr, value in update_data.items():
            setattr(equipment, attr, value)

        equipment.save()
        return equipment
    except ValidationError as e:
        return 400, {"detail": e.messages[0]}


@site_equipment_router.delete(
    "/{equipment_id}",
    operation_id="operations_api_v1_site_equipment_delete_site_equipment",
)
@require_permission("site_equipment", "delete")
def delete_site_equipment(request, equipment_id: int):
    """Delete a site equipment item"""
    equipment = get_object_or_404(SiteEquipment, id=equipment_id)
    equipment.delete()
    return {"detail": "Site equipment deleted successfully"}
