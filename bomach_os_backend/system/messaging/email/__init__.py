"""Canonical email transport boundary for Bomach OS."""

from system.messaging.email.providers.zeptomail import send_zepto_email

__all__ = ["send_zepto_email"]
