"""Provider-agnostic email sending services.

Business/domain code should depend on this module rather than importing a
provider adapter directly.
"""

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


__all__ = ["send_email"]
