"""People API routers."""

from domains.people.api.v1.routers.biometric import biometric_api
from domains.people.api.v1.routers.target_report import target_report_api

__all__ = ["biometric_api", "target_report_api"]
