"""Compatibility module alias for canonical domain ownership."""

import importlib
import sys

_canonical = importlib.import_module("domains.legal_compliance.models.compliance_audit")
sys.modules[__name__] = _canonical
