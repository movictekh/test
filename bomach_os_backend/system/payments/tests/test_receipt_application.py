from types import SimpleNamespace

from django.test import SimpleTestCase

from system.payments.application import (
    PaymentReceiptApplicationError,
    _RECEIPT_APPLICATIONS,
    apply_confirmed_receipt,
    register_receipt_application,
)


class ReceiptApplicationRegistryTests(SimpleTestCase):
    def tearDown(self):
        _RECEIPT_APPLICATIONS.pop("phase6-test", None)

    def receipt(self, purpose_type="phase6-test"):
        return SimpleNamespace(
            reference="CR-DEMO",
            intent=SimpleNamespace(purpose_type=purpose_type),
        )

    def test_unknown_purpose_is_left_unapplied(self):
        self.assertFalse(apply_confirmed_receipt(self.receipt("unknown-purpose")))

    def test_registered_handler_is_called(self):
        calls = []
        register_receipt_application(
            "phase6-test",
            lambda receipt: calls.append(receipt.reference),
            replace=True,
        )
        self.assertTrue(apply_confirmed_receipt(self.receipt()))
        self.assertEqual(calls, ["CR-DEMO"])

    def test_handler_error_is_retryable_wrapper(self):
        def fail(receipt):
            raise RuntimeError("settlement unavailable")

        register_receipt_application("phase6-test", fail, replace=True)
        with self.assertRaises(PaymentReceiptApplicationError):
            apply_confirmed_receipt(self.receipt())
