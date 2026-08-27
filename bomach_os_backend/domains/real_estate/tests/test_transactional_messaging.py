from decimal import Decimal
from unittest.mock import patch
from django.test import SimpleTestCase
from django.utils import timezone
from domains.real_estate.services.messaging import (
    enqueue_payment_request_message,
    enqueue_payment_receipt_message,
    enqueue_reservation_message,
    enqueue_sale_completion_message,
)


class U: id = 77; email = "buyer@example.com"
class C: user = U()
class P: property_name = "Plot A"
class Purchase:
    id = 9; property_id = 3; property = P(); client = C(); amount_paid = Decimal("250000.00")
class Intent: reference = "PI-1"; expires_at = None
class Attempt:
    reference = "PA-1"; provider_reference = "INV-1"; amount = Decimal("100000.00")
    currency = "NGN"; checkout_url = "https://pay.example/INV-1"
class Receipt:
    reference = "RCPT-1"; provider = "monnify"; provider_transaction_reference = "TX-1"
    amount = Decimal("100000.00"); currency = "NGN"; paid_at = timezone.now()


class TransactionalMessagingContractTests(SimpleTestCase):
    @patch("domains.real_estate.services.messaging.enqueue_user_message")
    def test_payment_request_contains_checkout_link(self, enqueue):
        enqueue_payment_request_message(purchase=Purchase(), intent=Intent(), attempt=Attempt())
        self.assertEqual(enqueue.call_args.kwargs["link"], "https://pay.example/INV-1")
        self.assertEqual(enqueue.call_args.kwargs["event_type"], "real_estate.payment_request")

    @patch("domains.real_estate.services.messaging.enqueue_user_message")
    def test_stable_distinct_lifecycle_keys(self, enqueue):
        purchase, receipt = Purchase(), Receipt()
        enqueue_payment_receipt_message(purchase=purchase, receipt=receipt)
        enqueue_reservation_message(purchase=purchase, receipt=receipt)
        enqueue_sale_completion_message(purchase=purchase, receipt=receipt)
        keys = [c.kwargs["event_key"] for c in enqueue.call_args_list]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertTrue(any("receipt:RCPT-1:received" in k for k in keys))
        self.assertTrue(any("reservation-confirmed" in k for k in keys))
        self.assertTrue(any("sale-completed" in k for k in keys))
