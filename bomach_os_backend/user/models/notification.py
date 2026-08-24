"""Django compatibility export for the System Notification model.

Canonical source ownership lives in ``system.notifications.models``.
The Django app identity remains ``user`` so tables, migrations, permissions,
content types, and relationships remain unchanged.
"""
from system.notifications.models import Notification
__all__ = ["Notification"]
