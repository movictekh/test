"""Compatibility module alias for canonical System Identity ownership."""

import importlib
import sys

_canonical = importlib.import_module("system.identity.authentication")
sys.modules[__name__] = _canonical
