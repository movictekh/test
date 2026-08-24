"""Django email-backend transport adapter.

This adapter preserves the repository's existing django.core.mail.send_mail
semantics while giving System Messaging ownership of the transport dependency.
"""

from django.core.mail import send_mail as django_send_mail


def send_django_mail(
    subject,
    message,
    from_email=None,
    recipient_list=None,
    fail_silently=False,
):
    """Send a plain-text email through Django's configured email backend."""
    return django_send_mail(
        subject=subject,
        message=message,
        from_email=from_email,
        recipient_list=recipient_list,
        fail_silently=fail_silently,
    )


__all__ = ["send_django_mail"]
