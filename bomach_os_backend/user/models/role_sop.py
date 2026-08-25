"""Compatibility module alias for canonical Organization ownership."""

import importlib
import sys

_canonical = importlib.import_module("domains.organization.models.role_sop")
sys.modules[__name__] = _canonical
