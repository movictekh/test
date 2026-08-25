"""Compatibility module alias for canonical System ownership."""

import importlib
import sys

_canonical = importlib.import_module("system.automation.api.v1.routers.workflow_rule")
sys.modules[__name__] = _canonical
