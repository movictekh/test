from functools import wraps

from django.core.exceptions import ValidationError
from ninja.errors import HttpError

# ── Role-based permission system with branch scoping ─────────────────────────


def require_permission(resource, action, owner_lookup=None):
    """
    Decorator for Django Ninja endpoints that checks Role-based permissions.

    Args:
        resource:     Key from PERMISSIONS_MAP, e.g. "estates", "leave_requests"
        action:       Action to check, e.g. "create", "view", "list", "update", "delete"
        owner_lookup: Django ORM lookup path to the owner User, e.g. "employee__user".
                      If set and the broad action is denied, the decorator falls back
                      to checking ``{action}_own``.

    Sets on ``request``:
        _perm_employee   – the Employee instance
        _perm_owner_only – True when only the ``_own`` variant was granted
        _perm_scope      – 'company' | 'branches'
        _perm_branch_ids – list of branch IDs the role is scoped to (empty = company-wide)

    Usage::

        @router.get("/")
        @paginate(LimitOffsetPagination, page_size=10)
        @require_permission("estates", "list")
        def list_estates(request, ...):

        @router.get("/{leave_id}")
        @require_permission("leave_requests", "view", owner_lookup="employee__user")
        def get_leave(request, leave_id: int):
    """

    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            from domains.organization.models.role import Role

            try:
                employee = request.user.employee_profile
            except Exception:
                raise HttpError(403, "Employee profile not found.")

            if not employee.role:
                raise HttpError(403, "No role assigned.")

            has_broad = Role.employee_has_permission(employee, resource, action)
            has_own = False

            if not has_broad and owner_lookup:
                has_own = Role.employee_has_permission(
                    employee, resource, f"{action}_own"
                )

            if not has_broad and not has_own:
                raise HttpError(
                    403, "You do not have permission to perform this action."
                )

            # Attach helpers to request for use inside the view
            request._perm_employee = employee
            request._perm_owner_only = not has_broad and has_own

            # Branch scoping from the role
            branch_ids = employee.role.get_branch_ids()
            request._perm_branch_ids = branch_ids

            if not branch_ids:
                request._perm_scope = "company"
            else:
                request._perm_scope = "branches"

            return func(request, *args, **kwargs)

        return wrapper

    return decorator


def scope_queryset(
    request, qs, owner_field=None, branch_field=None, department_field=None
):
    """
    Filter a queryset based on the permission scope set by ``@require_permission``.

    Call this inside list views after building the base queryset::

        qs = scope_queryset(
            request, qs,
            owner_field="employee__user",       # for _own filtering
            branch_field="employee__branch",    # for branch scoping
            department_field="employee__department",
        )

    Returns the filtered queryset.
    """
    employee = getattr(request, "_perm_employee", None)
    if not employee:
        return qs

    # Owner-only access: show only their own records
    if getattr(request, "_perm_owner_only", False):
        if owner_field:
            return qs.filter(**{owner_field: request.user})
        return qs.none()

    # Broad permission: scope by role's branches
    scope = getattr(request, "_perm_scope", "branches")

    if scope == "company":
        return qs

    # Branch-scoped: filter to the role's branches
    branch_ids = getattr(request, "_perm_branch_ids", [])
    if branch_ids and branch_field:
        return qs.filter(**{f"{branch_field}__in": branch_ids})

    return qs


def check_obj_permission(request, obj, owner_field=None):
    """
    For detail / update / delete endpoints, verify the user can access a
    specific object when they only have ``_own`` permission.

    Raises ``HttpError(403)`` if the ownership check fails.

    Args:
        obj:         The model instance to check.
        owner_field: Dot-separated path to the owner User on the object,
                     e.g. ``"employee.user"`` or ``"created_by"``.

    Usage::

        leave = get_object_or_404(LeaveRequest, id=leave_id)
        check_obj_permission(request, leave, owner_field="employee.user")
    """
    if not getattr(request, "_perm_owner_only", False):
        return  # has broad permission — nothing to check

    if not owner_field:
        raise HttpError(403, "You do not have permission to access this resource.")

    # Walk the dot-separated path
    current = obj
    for attr in owner_field.split("."):
        current = getattr(current, attr, None)
        if current is None:
            raise HttpError(403, "You do not have permission to access this resource.")

    if current != request.user:
        raise HttpError(403, "You do not have permission to access this resource.")
