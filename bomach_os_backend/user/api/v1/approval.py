"""Compatibility module alias for canonical System ownership."""

import importlib
import sys

_canonical = importlib.import_module("system.approvals.api.v1.routers.approval")
sys.modules[__name__] = _canonical
