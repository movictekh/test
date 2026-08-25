"""Compatibility exports for Organization SOP and People Responsibility."""

from domains.organization.models.sop import SOP
from domains.people.models.responsibility import Responsibility

__all__ = ["SOP", "Responsibility"]
