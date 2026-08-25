"""Compatibility module alias for canonical domain ownership."""

import importlib
import sys

_canonical = importlib.import_module("domains.organization.models.role")
sys.modules[__name__] = _canonical
