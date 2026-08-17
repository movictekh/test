"""Marketing & Sales model ownership.

Django model identity intentionally remains under the legacy ``services`` app.
"""

from .marketing import *  # noqa: F401,F403
from .revenue_execution import *  # noqa: F401,F403
from .sales import *  # noqa: F401,F403
