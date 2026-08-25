"""Compatibility exports for the canonical System Authorization boundary."""

from system.authorization import (
    check_obj_permission,
    require_permission,
    scope_queryset,
)

__all__ = [
    "check_obj_permission",
    "require_permission",
    "scope_queryset",
]
