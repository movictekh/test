import json
from unittest.mock import Mock, patch

from django.test import SimpleTestCase, override_settings

from system.messaging.email.providers import zeptomail
from system.messaging.email.providers.zeptomail import send_zepto_email


class ZeptoMailTransportTests(SimpleTestCase):
    @override_settings(ZOHOZEPTOMAIL_KEY="test-zepto-key")
    @patch("system.messaging.email.providers.zeptomail.requests.post")
    def test_send_zepto_email_preserves_provider_request_contract(self, post_mock):
        response = Mock()
        response.ok = True
        post_mock.return_value = response

        result = send_zepto_email(
            to_address="client@example.com",
            to_name="Client Name",
            subject="Subject",
            html_content="<p>Hello</p>",
        )

        self.assertIs(result, response)
        post_mock.assert_called_once()
        self.assertEqual(post_mock.call_args.args[0], zeptomail.ZEPTO_URL)
        kwargs = post_mock.call_args.kwargs
        self.assertEqual(
            kwargs["headers"],
            {
                "accept": "application/json",
                "content-type": "application/json",
                "authorization": "test-zepto-key",
            },
        )
        self.assertEqual(
            json.loads(kwargs["data"]),
            {
                "from": {
                    "address": zeptomail.FROM_ADDRESS,
                    "name": zeptomail.FROM_NAME,
                },
                "to": [
                    {
                        "email_address": {
                            "address": "client@example.com",
                            "name": "Client Name",
                        }
                    }
                ],
                "subject": "Subject",
                "htmlbody": "<p>Hello</p>",
            },
        )

    @override_settings(ZOHOZEPTOMAIL_KEY="test-zepto-key")
    @patch("system.messaging.email.providers.zeptomail.requests.post")
    def test_send_zepto_email_preserves_recipient_name_fallback(self, post_mock):
        response = Mock()
        response.ok = True
        post_mock.return_value = response
        send_zepto_email(
            to_address="fallback@example.com",
            to_name="",
            subject="Subject",
            html_content="<p>Hello</p>",
        )
        payload = json.loads(post_mock.call_args.kwargs["data"])
        self.assertEqual(payload["to"][0]["email_address"]["name"], "fallback")

    def test_legacy_private_transport_symbol_is_compatibility_alias(self):
        from user.utils.send_email import _send_zepto_email
        self.assertIs(_send_zepto_email, send_zepto_email)
