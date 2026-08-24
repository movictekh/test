from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from system.messaging.email.services import send_email


class EmailServiceTests(SimpleTestCase):
    @patch("system.messaging.email.services.send_zepto_email")
    def test_send_email_delegates_to_provider_with_exact_mapping(self, provider_mock):
        response = Mock()
        provider_mock.return_value = response

        result = send_email(
            recipient="client@example.com",
            name="Client Name",
            subject="Subject",
            html_content="<p>Hello</p>",
        )

        self.assertIs(result, response)
        provider_mock.assert_called_once_with(
            to_address="client@example.com",
            to_name="Client Name",
            subject="Subject",
            html_content="<p>Hello</p>",
        )

    @patch("system.messaging.email.services.send_zepto_email")
    def test_send_email_preserves_empty_name_for_provider_fallback(self, provider_mock):
        provider_mock.return_value = Mock()

        send_email(
            recipient="fallback@example.com",
            name="",
            subject="Subject",
            html_content="<p>Hello</p>",
        )

        provider_mock.assert_called_once_with(
            to_address="fallback@example.com",
            to_name="",
            subject="Subject",
            html_content="<p>Hello</p>",
        )

    @patch(
        "system.messaging.email.services.send_zepto_email",
        side_effect=RuntimeError("provider unavailable"),
    )
    def test_send_email_preserves_provider_exception_behavior(self, provider_mock):
        with self.assertRaisesRegex(RuntimeError, "provider unavailable"):
            send_email(
                recipient="client@example.com",
                name="Client",
                subject="Subject",
                html_content="<p>Hello</p>",
            )
        provider_mock.assert_called_once()
