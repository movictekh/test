"""Version 1 of the Project Operations HTTP contract."""

from ninja import NinjaAPI

from .routers import contracts
from .routers import dashboard
from .routers import milestones
from .routers import my_tasks
from .routers import projects
from .routers import site_equipment
from .routers import tasks
from .routers import timelines
from .routers import worksites


def register_project_operations_v1(api: NinjaAPI) -> None:
    """Register version 1 of the Project Operations HTTP API."""

    api.add_router("/dashboard", dashboard.router)
    api.add_router("/projects", projects.router)
    api.add_router("/tasks", tasks.router)
    api.add_router("/my-tasks", my_tasks.router)
    api.add_router("/worksites", worksites.router)
    api.add_router("/contracts", contracts.router)
    api.add_router("/timelines", timelines.router)
    api.add_router("/milestones", milestones.router)
    api.add_router("/site-equipment", site_equipment.router)


__all__ = ["register_project_operations_v1"]
