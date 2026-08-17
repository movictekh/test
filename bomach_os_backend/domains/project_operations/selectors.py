"""Reusable read/query logic for Project Operations."""

from decimal import Decimal

from django.db.models import Q, Sum

from .models import Contract, Project, Task, Timeline, Worksite


def list_projects(*, status=None, priority=None, client_id=None, search=None):
    projects = Project.objects.all()

    if status:
        projects = projects.filter(status=status)
    if priority:
        projects = projects.filter(priority=priority)
    if client_id:
        projects = projects.filter(client_id=client_id)
    if search:
        projects = projects.filter(
            Q(name__icontains=search)
            | Q(short_code__icontains=search)
            | Q(category__icontains=search)
        )

    return projects


def list_tasks(
    *, project_id=None, milestone_id=None, status=None, priority=None, search=None
):
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
            Q(name__icontains=search) | Q(description__icontains=search)
        )

    return tasks


def list_employee_tasks(*, employee, status=None):
    tasks = Task.objects.filter(assigned_to=employee)

    if status:
        tasks = tasks.filter(status=status).order_by("due_date", "-priority")

    return tasks


def employee_owns_task(*, task, employee) -> bool:
    return task.assigned_to.filter(id=employee.id).exists()


def get_dashboard_stats():
    total_projects = Project.objects.count()
    total_worksites = Worksite.objects.count()
    total_contracts = Contract.objects.count()
    total_timelines = Timeline.objects.count()

    total_budget = Project.objects.aggregate(total=Sum("budget"))["total"] or Decimal(
        "0.00"
    )
    budget_utilization = Project.objects.filter(status="completed").aggregate(
        total=Sum("budget")
    )["total"] or Decimal("0.00")

    return {
        "total_projects": total_projects,
        "total_budget": total_budget,
        "budget_utilization": budget_utilization,
        "total_worksites": total_worksites,
        "total_contracts": total_contracts,
        "total_timelines": total_timelines,
    }
