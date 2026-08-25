"""Compatibility module alias for canonical System Identity ownership."""

import importlib
import sys

_canonical = importlib.import_module("system.identity.api.v1.schemas.auth")
sys.modules[__name__] = _canonical
