"""Compatibility exports for the canonical System Audit producer."""

from system.audit.services import _get_client_ip, log_activity

__all__ = ["_get_client_ip", "log_activity"]
