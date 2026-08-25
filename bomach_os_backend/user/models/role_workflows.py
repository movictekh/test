"""Compatibility module alias for canonical Organization ownership."""

import importlib
import sys

_canonical = importlib.import_module("domains.organization.models.role_workflows")
sys.modules[__name__] = _canonical
