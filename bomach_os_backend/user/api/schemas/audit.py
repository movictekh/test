"""Compatibility module alias for canonical domain ownership."""

import importlib
import sys

_canonical = importlib.import_module("domains.legal_compliance.api.v1.schemas.audit")
sys.modules[__name__] = _canonical
