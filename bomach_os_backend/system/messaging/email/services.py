"""Provider-agnostic email sending services.

Business/domain code should depend on this module rather than importing a
provider adapter directly.
"""

from system.messaging.email.providers.django_mail import send_django_mail
from system.messaging.email.providers.zeptomail import send_zepto_email


def send_email(
    *,
    recipient: str,
    name: str,
    subject: str,
    html_content: str,
):
    """Send one HTML email through the configured Bomach OS email provider."""
    return send_zepto_email(
        to_address=recipient,
        to_name=name,
        subject=subject,
        html_content=html_content,
    )


def send_text_email(
    subject,
    message,
    from_email=None,
    recipient_list=None,
    fail_silently=False,
):
    """Send one plain-text email through Django's configured email backend."""
    return send_django_mail(
        subject=subject,
        message=message,
        from_email=from_email,
        recipient_list=recipient_list,
        fail_silently=fail_silently,
    )


__all__ = ["send_email", "send_text_email"]
