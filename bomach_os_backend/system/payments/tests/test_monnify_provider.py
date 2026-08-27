import hashlib
import hmac
import json
from datetime import timedelta
from decimal import Decimal
from unittest.mock import Mock, patch

from django.test import TestCase, override_settings
from django.utils import timezone

from system.payments.providers import (
    PaymentProviderIgnoredEvent,
    PaymentProviderVerificationError,
    ProviderAttemptRequest,
)
from system.payments.providers.monnify import MonnifyProvider

CFG = {
    "MONNIFY_API_KEY": "MK_TEST_X",
    "MONNIFY_SECRET_KEY": "SECRET_X",
    "MONNIFY_CONTRACT_CODE": "1234567890",
    "MONNIFY_BASE_URL": "https://sandbox.monnify.com",
    "MONNIFY_CONNECT_TIMEOUT": 2.0,
    "MONNIFY_RESPONSE_TIMEOUT": 5.0,
    "MONNIFY_ALLOW_UNSIGNED_SANDBOX_WEBHOOKS": False,
}


def resp(data):
    r = Mock()
    r.raise_for_status.return_value = None
    r.json.return_value = data
    return r


@override_settings(**CFG)
class MonnifyProviderTests(TestCase):
    def setUp(self):
        self.provider = MonnifyProvider()

    @patch("system.payments.providers.monnify.requests.post")
    def test_dynamic_invoice(self, post):
        post.side_effect = [
            resp({"requestSuccessful": True, "responseBody": {"accessToken": "token"}}),
            resp({"requestSuccessful": True, "responseBody": {
                "checkoutUrl": "https://sandbox.monnify.com/checkout/x",
                "accountNumber": "1234567890",
            }}),
        ]
        result = self.provider.create_attempt(ProviderAttemptRequest(
            intent_reference="PI-1",
            attempt_reference="PA-1",
            amount=Decimal("2000000.00"),
            currency="NGN",
            description="Plot payment",
            metadata={"customer_email": "buyer@example.com", "customer_name": "Ada Buyer"},
            idempotency_key="k",
            expires_at=timezone.now() + timedelta(hours=2),
        ))
        self.assertEqual(result.provider_reference, "PA-1")
        self.assertTrue(result.checkout_url)
        body = post.call_args_list[1].kwargs["json"]
        self.assertEqual(body["invoiceReference"], "PA-1")
        self.assertEqual(body["contractCode"], "1234567890")
        self.assertEqual(body["customerEmail"], "buyer@example.com")

    def signed(self):
        payload = {"eventType": "SUCCESSFUL_TRANSACTION", "eventData": {
            "transactionReference": "MNFY|TEST|1",
            "paymentReference": "PAY-1",
            "amountPaid": "2000000.00",
            "paymentStatus": "PAID",
            "paymentMethod": "ACCOUNT_TRANSFER",
            "currency": "NGN",
            "paidOn": "2026-08-26T20:00:00+00:00",
            "product": {"reference": "PA-1"},
        }}
        raw = json.dumps(payload, separators=(",", ":")).encode()
        sig = hmac.new(CFG["MONNIFY_SECRET_KEY"].encode(), raw, hashlib.sha512).hexdigest()
        return payload, raw, sig

    @patch.object(MonnifyProvider, "_verify_transaction")
    def test_signed_webhook_and_server_verify(self, verify):
        verify.return_value = {
            "transactionReference": "MNFY|TEST|1",
            "paymentStatus": "PAID",
            "amountPaid": "2000000.00",
            "currencyCode": "NGN",
            "paidOn": "2026-08-26T20:00:00+00:00",
        }
        payload, raw, sig = self.signed()
        result = self.provider.verify_event(
            payload=payload, headers={"monnify-signature": sig}, raw_body=raw
        )
        self.assertEqual(result.provider_reference, "PA-1")
        self.assertEqual(result.transaction_reference, "MNFY|TEST|1")
        verify.assert_called_once_with("PAY-1")

    def test_exact_raw_body_signature(self):
        payload, raw, sig = self.signed()
        with self.assertRaises(PaymentProviderVerificationError):
            self.provider.verify_event(
                payload=payload, headers={"monnify-signature": sig}, raw_body=raw + b" "
            )

    def test_missing_signature_rejected(self):
        payload, raw, _ = self.signed()
        with self.assertRaises(PaymentProviderVerificationError):
            self.provider.verify_event(payload=payload, headers={}, raw_body=raw)

    def test_other_event_ignored(self):
        payload = {"eventType": "SETTLEMENT_COMPLETION", "eventData": {}}
        raw = json.dumps(payload).encode()
        sig = hmac.new(CFG["MONNIFY_SECRET_KEY"].encode(), raw, hashlib.sha512).hexdigest()
        with self.assertRaises(PaymentProviderIgnoredEvent):
            self.provider.verify_event(
                payload=payload, headers={"monnify-signature": sig}, raw_body=raw
            )
