"""Django compatibility shell for Service Operations models.

The real model source lives in ``domains.service_operations.models``.

The ``services`` Django app remains the installed app and migration owner, so this
module intentionally re-exports the domain-owned classes for legacy imports and
Django model loading.
"""

from domains.service_operations.models import *  # noqa: F401,F403
