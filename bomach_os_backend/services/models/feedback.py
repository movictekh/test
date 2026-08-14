"""Django compatibility shell for Service Operations ClientFeedback.

The real model source lives in ``domains.service_operations.models``.
The ``services`` Django app remains the migration/model-identity owner.
"""

from domains.service_operations.models import ClientFeedback

__all__ = ["ClientFeedback"]
