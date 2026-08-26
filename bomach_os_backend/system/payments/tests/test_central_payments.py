from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from finance.models import FinanceAccount, JournalEntry, LedgerAccount
from system.identity.models.user import User
from system.payments.models import (
    ConfirmedReceipt,
    PaymentAttempt,
    PaymentIntent,
    PaymentProviderEvent,
)
from system.payments.providers import (
    PaymentProviderVerificationError,
    ProviderAttemptResult,
    VerifiedProviderPayment,
    clear_provider_registry,
    register_provider,
)
from system.payments.services import (
    create_payment_intent,
    expire_payment_intent,
    mark_receipt_applied,
    record_verified_provider_event,
    start_payment_attempt,
    verify_and_apply_provider_event,
)


class FakeProvider:
    name = "fake"

    def __init__(self):
        self.create_calls = 0

    def create_attempt(self, request):
        self.create_calls += 1
        return ProviderAttemptResult(
            provider_reference=f"FAKE-{request.attempt_reference}",
            status="pending",
            checkout_url="https://payments.example.test/checkout",
            metadata={"request_seen": True},
        )

    def verify_event(self, *, payload, headers):
        if headers.get("x-fake-signature") != "valid":
            raise PaymentProviderVerificationError("Invalid fake signature.")
        return VerifiedProviderPayment(
            event_key=str(payload["event_key"]),
            event_type=str(payload.get("event_type", "payment.success")),
            provider_reference=str(payload["provider_reference"]),
            intent_reference=str(payload["intent_reference"]),
            amount=Decimal(str(payload["amount"])),
            currency=str(payload["currency"]),
            paid_at=timezone.now(),
            payment_method="bank_transfer",
            metadata={"verified_by": "fake"},
        )


class CentralPaymentTests(TestCase):
    def setUp(self):
        clear_provider_registry()
        self.provider = register_provider(FakeProvider())
        self.user = User.objects.create_user(
            username="central-payments",
            email="central-payments@example.com",
            password="StrongPass123!",
        )
        LedgerAccount.objects.get_or_create(
            code="1100",
            defaults={
                "name": "Cash & Bank",
                "account_type": LedgerAccount.ACCOUNT_TYPE.ASSET,
                "normal_balance": LedgerAccount.NORMAL_BALANCE.DEBIT,
                "is_postable": False,
                "created_by": self.user,
            },
        )
        LedgerAccount.objects.get_or_create(
            code="4200",
            defaults={
                "name": "Real Estate Revenue",
                "account_type": LedgerAccount.ACCOUNT_TYPE.REVENUE,
                "normal_balance": LedgerAccount.NORMAL_BALANCE.CREDIT,
                "is_postable": True,
                "created_by": self.user,
            },
        )
        LedgerAccount.objects.get_or_create(
            system_role=LedgerAccount.SYSTEM_ROLE.STATUTORY_PAYABLE,
            defaults={
                "code": "2299-TST",
                "name": "Statutory Payable",
                "account_type": LedgerAccount.ACCOUNT_TYPE.LIABILITY,
                "normal_balance": LedgerAccount.NORMAL_BALANCE.CREDIT,
                "is_postable": True,
                "created_by": self.user,
            },
        )
        self.finance_account = FinanceAccount.objects.create(
            account_type=FinanceAccount.ACCOUNT_TYPE.BANK,
            display_name="Company Collections",
            currency="NGN",
            bank_name="Test Bank",
            account_number="1234567890",
            account_name="Bomach Test",
            created_by=self.user,
        )

    def intent(
        self,
        *,
        key="intent-1",
        amount="100000.00",
        total_due="500000.00",
        purpose_id="41",
        expires_at=None,
    ):
        return create_payment_intent(
            idempotency_key=key,
            purpose_type="real_estate_property_purchase",
            purpose_id=purpose_id,
            amount=Decimal(amount),
            currency="NGN",
            description="Plot payment",
            metadata={"purchase_id": purpose_id},
            expires_at=expires_at or timezone.now() + timedelta(hours=2),
            created_by=self.user,
            accounting_total_due=Decimal(total_due),
            accounting_total_tax=Decimal("0.00"),
            accounting_prior_paid=Decimal("0.00"),
            revenue_account_code="4200",
        )[0]

    def attempt(self, intent=None, *, key="attempt-1"):
        intent = intent or self.intent()
        return start_payment_attempt(
            intent=intent,
            provider_name="fake",
            idempotency_key=key,
        )[0]

    def success_payload(self, intent, attempt, *, event_key="evt-1", amount=None):
        return {
            "event_key": event_key,
            "event_type": "payment.success",
            "provider_reference": attempt.provider_reference,
            "intent_reference": intent.reference,
            "amount": str(amount if amount is not None else intent.amount),
            "currency": intent.currency,
        }

    def test_payment_intent_creation_is_idempotent_and_conflict_safe(self):
        intent, created = create_payment_intent(
            idempotency_key="stable-intent",
            purpose_type="real_estate_property_purchase",
            purpose_id="99",
            amount=Decimal("50000.00"),
            currency="NGN",
            created_by=self.user,
            accounting_total_due=Decimal("50000.00"),
            revenue_account_code="4200",
        )
        repeated, repeated_created = create_payment_intent(
            idempotency_key="stable-intent",
            purpose_type="real_estate_property_purchase",
            purpose_id="99",
            amount=Decimal("50000.00"),
            currency="NGN",
            created_by=self.user,
            accounting_total_due=Decimal("50000.00"),
            revenue_account_code="4200",
        )
        self.assertTrue(created)
        self.assertFalse(repeated_created)
        self.assertEqual(repeated.id, intent.id)
        with self.assertRaises(ValidationError):
            create_payment_intent(
                idempotency_key="stable-intent",
                purpose_type="real_estate_property_purchase",
                purpose_id="99",
                amount=Decimal("60000.00"),
                currency="NGN",
                created_by=self.user,
                accounting_total_due=Decimal("60000.00"),
                revenue_account_code="4200",
            )

    def test_provider_attempt_creation_is_idempotent(self):
        intent = self.intent()
        first, created = start_payment_attempt(
            intent=intent,
            provider_name="fake",
            idempotency_key="stable-attempt",
        )
        second, repeated_created = start_payment_attempt(
            intent=intent,
            provider_name="fake",
            idempotency_key="stable-attempt",
        )
        self.assertTrue(created)
        self.assertFalse(repeated_created)
        self.assertEqual(first.id, second.id)
        self.assertEqual(self.provider.create_calls, 1)
        self.assertEqual(first.status, PaymentAttempt.STATUS.PENDING)

    def test_invalid_provider_verification_does_not_create_event_or_receipt(self):
        intent = self.intent()
        attempt = self.attempt(intent)
        with self.assertRaises(PaymentProviderVerificationError):
            verify_and_apply_provider_event(
                provider_name="fake",
                payload=self.success_payload(intent, attempt),
                headers={"x-fake-signature": "invalid"},
                confirmed_by=self.user,
            )
        self.assertEqual(PaymentProviderEvent.objects.count(), 0)
        self.assertEqual(ConfirmedReceipt.objects.count(), 0)

    def test_verified_receipt_posts_finance_once_without_account_prompt(self):
        intent = self.intent()
        attempt = self.attempt(intent)
        payload = self.success_payload(intent, attempt)
        receipt = verify_and_apply_provider_event(
            provider_name="fake",
            payload=payload,
            headers={"x-fake-signature": "valid"},
            confirmed_by=self.user,
        )
        repeated = verify_and_apply_provider_event(
            provider_name="fake",
            payload=payload,
            headers={"x-fake-signature": "valid"},
            confirmed_by=self.user,
        )
        intent.refresh_from_db()
        attempt.refresh_from_db()
        receipt.refresh_from_db()
        self.assertEqual(receipt.id, repeated.id)
        self.assertEqual(receipt.finance_account_id, self.finance_account.id)
        self.assertIsNotNone(receipt.finance_journal_id)
        self.assertIsNotNone(receipt.finance_posted_at)
        self.assertEqual(intent.status, PaymentIntent.STATUS.CONFIRMED)
        self.assertEqual(attempt.status, PaymentAttempt.STATUS.SUCCEEDED)
        self.assertEqual(ConfirmedReceipt.objects.count(), 1)
        self.assertEqual(
            JournalEntry.objects.filter(
                source_type="central_payment_receipt",
                source_id=receipt.reference,
                source_event="confirmed",
            ).count(),
            1,
        )

    def test_verified_amount_mismatch_fails_without_finance_posting(self):
        intent = self.intent()
        attempt = self.attempt(intent)
        with self.assertRaises(ValidationError):
            verify_and_apply_provider_event(
                provider_name="fake",
                payload=self.success_payload(
                    intent,
                    attempt,
                    amount=Decimal("99999.99"),
                ),
                headers={"x-fake-signature": "valid"},
                confirmed_by=self.user,
            )
        event = PaymentProviderEvent.objects.get(event_key="evt-1")
        self.assertEqual(event.status, PaymentProviderEvent.STATUS.FAILED)
        self.assertEqual(ConfirmedReceipt.objects.count(), 0)
        self.assertEqual(
            JournalEntry.objects.filter(source_type="central_payment_receipt").count(),
            0,
        )

    def test_provider_event_key_cannot_be_reused_with_different_payload(self):
        record_verified_provider_event(
            provider="fake",
            event_key="same-event",
            event_type="payment.success",
            payload={"amount": "10.00"},
        )
        with self.assertRaises(ValidationError):
            record_verified_provider_event(
                provider="fake",
                event_key="same-event",
                event_type="payment.success",
                payload={"amount": "11.00"},
            )

    def test_receipt_application_is_separate_and_idempotent(self):
        intent = self.intent()
        attempt = self.attempt(intent)
        receipt = verify_and_apply_provider_event(
            provider_name="fake",
            payload=self.success_payload(intent, attempt),
            headers={"x-fake-signature": "valid"},
            confirmed_by=self.user,
        )
        applied, created = mark_receipt_applied(
            receipt=receipt,
            application_reference="real-estate:purchase:41",
        )
        repeated, repeated_created = mark_receipt_applied(
            receipt=receipt,
            application_reference="real-estate:purchase:41",
        )
        self.assertTrue(created)
        self.assertFalse(repeated_created)
        self.assertEqual(applied.id, repeated.id)
        self.assertIsNotNone(applied.applied_at)
        with self.assertRaises(ValidationError):
            mark_receipt_applied(
                receipt=receipt,
                application_reference="real-estate:purchase:OTHER",
            )

    def test_expiry_expires_open_attempts_without_receipt(self):
        intent = self.intent(
            key="expiring-intent",
            expires_at=timezone.now() + timedelta(minutes=1),
        )
        attempt = self.attempt(intent, key="expiring-attempt")
        expired, changed = expire_payment_intent(
            intent=intent,
            at=timezone.now() + timedelta(minutes=2),
        )
        attempt.refresh_from_db()
        self.assertTrue(changed)
        self.assertEqual(expired.status, PaymentIntent.STATUS.EXPIRED)
        self.assertEqual(attempt.status, PaymentAttempt.STATUS.EXPIRED)
        self.assertEqual(ConfirmedReceipt.objects.count(), 0)

    def test_concurrent_intent_snapshots_cannot_over_receipt_same_purpose(self):
        first = self.intent(
            key="concurrent-1",
            amount="100000.00",
            total_due="150000.00",
            purpose_id="shared-purpose",
        )
        second = self.intent(
            key="concurrent-2",
            amount="100000.00",
            total_due="150000.00",
            purpose_id="shared-purpose",
        )
        first_attempt = self.attempt(first, key="concurrent-attempt-1")
        second_attempt = self.attempt(second, key="concurrent-attempt-2")
        verify_and_apply_provider_event(
            provider_name="fake",
            payload=self.success_payload(
                first,
                first_attempt,
                event_key="concurrent-event-1",
            ),
            headers={"x-fake-signature": "valid"},
            confirmed_by=self.user,
        )
        with self.assertRaises(ValidationError):
            verify_and_apply_provider_event(
                provider_name="fake",
                payload=self.success_payload(
                    second,
                    second_attempt,
                    event_key="concurrent-event-2",
                ),
                headers={"x-fake-signature": "valid"},
                confirmed_by=self.user,
            )
        self.assertEqual(ConfirmedReceipt.objects.count(), 1)
        self.assertEqual(
            JournalEntry.objects.filter(source_type="central_payment_receipt").count(),
            1,
        )
