"""
Django identity shell for Project Operations models.

The real model source is owned by ``domains.project_operations.models``.
These imports preserve the installed Django app's conventional ``operations.models`` loading
path and existing internal import compatibility while model labels remain ``operations.*``.
"""

from domains.project_operations.models import (
    Contract,
    Milestone,
    Project,
    SiteEquipment,
    Task,
    Timeline,
    Worksite,
)

__all__ = [
    "Project",
    "Milestone",
    "Task",
    "Worksite",
    "SiteEquipment",
    "Contract",
    "Timeline",
]
