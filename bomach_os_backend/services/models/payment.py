"""Compatibility module alias for canonical Finance ownership."""

import importlib
import sys

_canonical = importlib.import_module("finance.transactions.payment")
sys.modules[__name__] = _canonical
