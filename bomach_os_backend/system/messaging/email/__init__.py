"""Canonical email messaging boundary for Bomach OS."""

from system.messaging.email.providers.zeptomail import send_zepto_email
from system.messaging.email.services import send_email

__all__ = ["send_email", "send_zepto_email"]
