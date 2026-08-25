"""Compatibility module alias for canonical domain ownership."""

import importlib
import sys

_canonical = importlib.import_module("domains.legal_compliance.api.v1.schemas.cases")
sys.modules[__name__] = _canonical
