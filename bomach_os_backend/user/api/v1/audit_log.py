"""Compatibility exports for the canonical System Audit API router."""

from system.audit.api.v1.routers.audit_log import audit_log_api, list_audit_logs

__all__ = ["audit_log_api", "list_audit_logs"]
