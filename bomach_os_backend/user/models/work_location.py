"""Compatibility module alias for canonical domain ownership."""

import importlib
import sys

_canonical = importlib.import_module("domains.people.models.work_location")
sys.modules[__name__] = _canonical
