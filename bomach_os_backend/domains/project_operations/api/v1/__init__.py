"""Version 1 of the Project Operations HTTP contract."""

from ninja import NinjaAPI

from .routers.contracts import router as contracts_router
from .routers.execution import (
    my_tasks_router,
    site_equipment_router,
    tasks_router,
    worksites_router,
)
from .routers.planning import milestone_router, timeline_router
from .routers.projects import dashboard_router
from .routers.projects import router as projects_router


def register_project_operations_v1(api: NinjaAPI) -> None:
    """Register version 1 of the Project Operations HTTP API."""

    api.add_router("/dashboard", dashboard_router)
    api.add_router("/projects", projects_router)
    api.add_router("/tasks", tasks_router)
    api.add_router("/my-tasks", my_tasks_router)
    api.add_router("/worksites", worksites_router)
    api.add_router("/contracts", contracts_router)
    api.add_router("/timelines", timeline_router)
    api.add_router("/milestones", milestone_router)
    api.add_router("/site-equipment", site_equipment_router)


__all__ = ["register_project_operations_v1"]
