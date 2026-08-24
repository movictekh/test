"""Email provider adapters."""

from system.messaging.email.providers.django_mail import send_django_mail
from system.messaging.email.providers.zeptomail import send_zepto_email

__all__ = ["send_django_mail", "send_zepto_email"]
