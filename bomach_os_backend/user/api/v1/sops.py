# your_app/api.py
from typing import Any, Dict, List

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from ninja import Router
from ninja.errors import HttpError

from user.api.schemas import (
    MessageOut,
    ResponsibilityIn,
    ResponsibilityOut,
    SOPIn,
    SOPOut,
)
from domains.organization.models.sop import SOP
from domains.people.models.responsibility import Responsibility
from domains.organization.models.roles import Department, Unit
from system.identity.models.user import User

# =============================================================================
#  BASE ROUTER (Shared functionality)
# =============================================================================


class BaseSOPRouter:
    """Base class for SOP routers with common CRUD operations."""

    def __init__(self, parent_field: str):
        self.parent_field = parent_field

    def get_queryset(self, request, parent_id: int):
        """Override in subclasses to provide filtered queryset."""
        raise NotImplementedError

    def create_sop(self, request, parent_id: int, payload: SOPIn):
        """Override in subclasses to handle creation logic."""
        raise NotImplementedError


# =============================================================================
#  DEPARTMENT SOPs
# =============================================================================

dept_router = Router(tags=["Department SOPs"])


@dept_router.get("/{dept_id}/sops", response={200: List[SOPOut], 404: MessageOut})
def list_department_sops(request, dept_id: int):
    """List all SOPs for a specific department."""
    department = get_object_or_404(Department, id=dept_id)
    return SOP.objects.filter(department=department).order_by("-updated_at")


@dept_router.post("/{dept_id}/sops", response={200: SOPOut, 400: MessageOut})
def create_department_sop(request, dept_id: int, payload: SOPIn):
    """Create a new SOP for a department."""
    department = get_object_or_404(Department, id=dept_id)

    sop = SOP.objects.create(
        department=department,
        **payload.dict(),
    )
    return sop


@dept_router.get("/{dept_id}/sops/{sop_id}", response={200: SOPOut, 404: MessageOut})
def get_department_sop(request, dept_id: int, sop_id: int):
    """Retrieve a specific department SOP."""
    department = get_object_or_404(Department, id=dept_id)
    return get_object_or_404(SOP, id=sop_id, department=department)


@dept_router.put("/{dept_id}/sops/{sop_id}", response={200: SOPOut, 404: MessageOut})
def update_department_sop(request, dept_id: int, sop_id: int, payload: SOPIn):
    """Update an existing department SOP."""
    department = get_object_or_404(Department, id=dept_id)
    sop = get_object_or_404(SOP, id=sop_id, department=department)

    for field, value in payload.dict(exclude_unset=True).items():
        setattr(sop, field, value)

    sop.updated_by = request.user
    sop.save()
    return sop


@dept_router.delete("/{dept_id}/sops/{sop_id}", response=MessageOut)
def delete_department_sop(request, dept_id: int, sop_id: int):
    """Delete a department SOP."""
    department = get_object_or_404(Department, id=dept_id)
    sop = get_object_or_404(SOP, id=sop_id, department=department)

    sop.delete()
    return {"message": "Department SOP deleted successfully", "success": True}


@dept_router.get(
    "/{dept_id}/sops/priority/{priority}", response={200: List[SOPOut], 404: MessageOut}
)
def filter_sops_by_priority(request, dept_id: int, priority: str):
    """Filter department SOPs by priority level."""
    department = get_object_or_404(Department, id=dept_id)
    return SOP.objects.filter(department=department, priority=priority)


# =============================================================================
#  UNIT SOPs
# =============================================================================

unit_router = Router(tags=["Unit SOPs"])


@unit_router.get("/{unit_id}/sops", response={200: List[SOPOut], 404: MessageOut})
def list_unit_sops(request, unit_id: int):
    """List all SOPs for a specific unit."""
    unit = get_object_or_404(Unit, id=unit_id)
    return SOP.objects.filter(unit=unit).order_by("-updated_at")


@unit_router.post("/{unit_id}/sops", response={200: SOPOut, 400: MessageOut})
def create_unit_sop(request, unit_id: int, payload: SOPIn):
    """Create a new SOP for a unit."""
    unit = get_object_or_404(Unit, id=unit_id)

    sop = SOP.objects.create(
        unit=unit,
        department=unit.department,  # Optional: inherit from unit
        **payload.dict(),
    )
    return sop


@unit_router.get("/{unit_id}/sops/{sop_id}", response={200: SOPOut, 404: MessageOut})
def get_unit_sop(request, unit_id: int, sop_id: int):
    """Retrieve a specific unit SOP."""
    unit = get_object_or_404(Unit, id=unit_id)
    return get_object_or_404(SOP, id=sop_id, unit=unit)


@unit_router.put("/{unit_id}/sops/{sop_id}", response={200: SOPOut, 404: MessageOut})
def update_unit_sop(request, unit_id: int, sop_id: int, payload: SOPIn):
    """Update an existing unit SOP."""
    unit = get_object_or_404(Unit, id=unit_id)
    sop = get_object_or_404(SOP, id=sop_id, unit=unit)

    for field, value in payload.dict(exclude_unset=True).items():
        setattr(sop, field, value)

    sop.updated_by = request.user
    sop.save()
    return sop


@unit_router.delete("/{unit_id}/sops/{sop_id}", response=MessageOut)
def delete_unit_sop(request, unit_id: int, sop_id: int):
    """Delete a unit SOP."""
    unit = get_object_or_404(Unit, id=unit_id)
    sop = get_object_or_404(SOP, id=sop_id, unit=unit)

    sop.delete()
    return {"message": "Unit SOP deleted successfully", "success": True}


# =============================================================================
#  CORE RESPONSIBILITIES
# =============================================================================

resp_router = Router(tags=["Core Responsibilities"])


@resp_router.get(
    "/my/{user_id}", response={200: List[ResponsibilityOut], 404: MessageOut}
)
def list_my_responsibilities(request, user_id: int):
    """List all responsibilities for the authenticated user."""
    return Responsibility.objects.filter(user=user_id).order_by("priority", "title")


@resp_router.post("/my/{user_id}", response={200: ResponsibilityOut, 400: MessageOut})
def create_my_responsibility(request, user_id: int, payload: ResponsibilityIn):
    """Create a new responsibility for the authenticated user."""
    user = get_object_or_404(User, id=user_id)
    responsibility = Responsibility.objects.create(
        user=user,
        **payload.dict(),
    )
    return responsibility


@resp_router.get(
    "/my/sop/{resp_id}", response={200: ResponsibilityOut, 404: MessageOut}
)
def get_my_responsibility(request, resp_id: int):
    """Retrieve a specific responsibility belonging to the user."""
    return get_object_or_404(Responsibility, id=resp_id)


@resp_router.put(
    "/edit/sop/{resp_id}", response={200: ResponsibilityOut, 404: MessageOut}
)
def update_my_responsibility(request, resp_id: int, payload: ResponsibilityIn):
    """Update an existing responsibility."""
    responsibility = get_object_or_404(Responsibility, id=resp_id)

    for field, value in payload.dict(exclude_unset=True).items():
        setattr(responsibility, field, value)

    responsibility.save()
    return responsibility


@resp_router.delete("/my/{resp_id}", response=MessageOut)
def delete_my_responsibility(request, resp_id: int):
    """Delete a responsibility."""
    responsibility = get_object_or_404(Responsibility, id=resp_id)

    responsibility.delete()
    return {"message": "Responsibility deleted successfully", "success": True}


# =============================================================================
#  DASHBOARD & UTILITIES
# =============================================================================

sop_dashboard_router = Router(tags=["Dashboard"])


@sop_dashboard_router.get(
    "/summary/{user_id}", response={200: Dict[str, Any], 404: MessageOut}
)
def get_dashboard_summary(request, user_id: int):
    """Get summary statistics for the dashboard."""
    user_responsibilities = Responsibility.objects.filter(user=user_id)

    return {
        "user": {
            "username": request.user.username,
            "email": request.user.email,
        },
        "statistics": {
            "total_responsibilities": user_responsibilities.count(),
            "by_priority": {
                "high": user_responsibilities.filter(priority="High").count(),
                "medium": user_responsibilities.filter(priority="Medium").count(),
                "low": user_responsibilities.filter(priority="Low").count(),
            },
            "by_category": {
                category: user_responsibilities.filter(category=category).count()
                for category in user_responsibilities.values_list(
                    "category", flat=True
                ).distinct()
            },
        },
        "recent_updates": list(
            user_responsibilities.order_by("-updated_at")[:5].values(
                "id", "title", "updated_at", "category"
            )
        ),
    }


@sop_dashboard_router.get("/recent-activity", response={200: Dict[str, Any]})
def get_recent_activity(request):
    # Assuming User model has related fields
    user_departments = (
        request.user.department_set.all()
        if hasattr(request.user, "department_set")
        else []
    )
    user_units = (
        request.user.unit_set.all() if hasattr(request.user, "unit_set") else []
    )

    recent_sops = SOP.objects.filter(
        models.Q(department__in=user_departments) | models.Q(unit__in=user_units)
    ).order_by("-updated_at")[:5]

    recent_responsibilities = Responsibility.objects.filter(user=request.user).order_by(
        "-updated_at"
    )[:5]

    return {
        "recent_sops": [
            {"id": s.id, "title": s.title, "type": "sop", "updated_at": s.updated_at}
            for s in recent_sops
        ],
        "recent_responsibilities": [
            {
                "id": r.id,
                "title": r.title,
                "type": "responsibility",
                "updated_at": r.updated_at,
            }
            for r in recent_responsibilities
        ],
    }
