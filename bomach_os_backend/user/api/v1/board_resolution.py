"""Compatibility module alias for canonical domain ownership."""

import importlib
import sys

_canonical = importlib.import_module("domains.governance.api.v1.routers.board_resolution")
sys.modules[__name__] = _canonical
