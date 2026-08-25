"""Compatibility module alias for canonical System ownership."""

import importlib
import sys

_canonical = importlib.import_module("system.automation.models.workflow_rule")
sys.modules[__name__] = _canonical
