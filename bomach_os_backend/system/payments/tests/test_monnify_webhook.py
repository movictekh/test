import json
from unittest.mock import patch

from django.test import TestCase

from system.payments.providers import PaymentProviderIgnoredEvent, PaymentProviderVerificationError


class MonnifyWebhookTests(TestCase):
    @patch("system.payments.api.v1.routers.webhook.verify_and_apply_provider_event")
    def test_public_webhook_forwards_raw_body(self, verify):
        verify.return_value = type("Receipt", (), {"reference": "CR-1"})()
        raw = json.dumps({"eventType": "SUCCESSFUL_TRANSACTION"}).encode()
        response = self.client.post(
            "/api/v1/payment-webhooks/monnify/", data=raw, content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(verify.call_args.kwargs["raw_body"], raw)
        self.assertIsNone(verify.call_args.kwargs["confirmed_by"])

    @patch("system.payments.api.v1.routers.webhook.verify_and_apply_provider_event")
    def test_verification_failure_401(self, verify):
        verify.side_effect = PaymentProviderVerificationError("bad signature")
        response = self.client.post(
            "/api/v1/payment-webhooks/monnify/",
            data=b'{"eventType":"SUCCESSFUL_TRANSACTION"}',
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)

    @patch("system.payments.api.v1.routers.webhook.verify_and_apply_provider_event")
    def test_ignored_event_200(self, verify):
        verify.side_effect = PaymentProviderIgnoredEvent("ignored")
        response = self.client.post(
            "/api/v1/payment-webhooks/monnify/",
            data=b'{"eventType":"SETTLEMENT_COMPLETION"}',
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
