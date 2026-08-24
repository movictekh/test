from unittest.mock import patch

from django.test import SimpleTestCase

from system.messaging.email.providers.django_mail import send_django_mail
from system.messaging.email.services import send_text_email


class DjangoMailProviderTests(SimpleTestCase):
    @patch("system.messaging.email.providers.django_mail.django_send_mail")
    def test_provider_preserves_django_send_mail_arguments_and_return(self, django_mock):
        django_mock.return_value = 1

        result = send_django_mail(
            subject="Invoice INV-1",
            message="Plain-text body",
            from_email=None,
            recipient_list=["client@example.com"],
            fail_silently=False,
        )

        self.assertEqual(result, 1)
        django_mock.assert_called_once_with(
            subject="Invoice INV-1",
            message="Plain-text body",
            from_email=None,
            recipient_list=["client@example.com"],
            fail_silently=False,
        )


class TextEmailServiceTests(SimpleTestCase):
    @patch("system.messaging.email.services.send_django_mail")
    def test_service_delegates_to_django_provider_with_exact_mapping(self, provider_mock):
        provider_mock.return_value = 1

        result = send_text_email(
            subject="Payment reminder",
            message="Reminder body",
            from_email="noreply@example.com",
            recipient_list=["client@example.com"],
            fail_silently=False,
        )

        self.assertEqual(result, 1)
        provider_mock.assert_called_once_with(
            subject="Payment reminder",
            message="Reminder body",
            from_email="noreply@example.com",
            recipient_list=["client@example.com"],
            fail_silently=False,
        )

    @patch(
        "system.messaging.email.services.send_django_mail",
        side_effect=RuntimeError("backend unavailable"),
    )
    def test_service_preserves_backend_exception_behavior(self, provider_mock):
        with self.assertRaisesRegex(RuntimeError, "backend unavailable"):
            send_text_email(
                subject="Subject",
                message="Body",
                from_email=None,
                recipient_list=["client@example.com"],
                fail_silently=False,
            )
        provider_mock.assert_called_once()
