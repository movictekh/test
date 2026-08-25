"""People API v1."""

from domains.people.api.v1.routers import biometric_api, target_report_api

__all__ = ["biometric_api", "target_report_api"]
