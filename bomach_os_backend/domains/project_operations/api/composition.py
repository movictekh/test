"""Project Operations HTTP API composition."""

from ninja import NinjaAPI

from .v1.routers import dashboard
from .v1.routers import projects
from .v1.routers import tasks
from .v1.routers import my_tasks
from .v1.routers import worksites
from .v1.routers import contracts
from .v1.routers import timelines
from .v1.routers import milestones
from .v1.routers import site_equipment


def register_project_operations_v1(api: NinjaAPI) -> None:
    """Register version 1 of the Project Operations HTTP contract."""

    api.add_router("/dashboard", dashboard.router)
    api.add_router("/projects", projects.router)
    api.add_router("/tasks", tasks.router)
    api.add_router("/my-tasks", my_tasks.router)
    api.add_router("/worksites", worksites.router)
    api.add_router("/contracts", contracts.router)
    api.add_router("/timelines", timelines.router)
    api.add_router("/milestones", milestones.router)
    api.add_router("/site-equipment", site_equipment.router)
