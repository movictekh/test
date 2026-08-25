"""Compatibility module alias for canonical domain ownership."""

import importlib
import sys

_canonical = importlib.import_module("domains.people.api.v1.schemas.target_report")
sys.modules[__name__] = _canonical
