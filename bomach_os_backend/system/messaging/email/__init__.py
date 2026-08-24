"""Canonical email messaging boundary for Bomach OS."""

from system.messaging.email.providers.django_mail import send_django_mail
from system.messaging.email.providers.zeptomail import send_zepto_email
from system.messaging.email.services import send_email, send_text_email

__all__ = [
    "send_email",
    "send_text_email",
    "send_django_mail",
    "send_zepto_email",
]
