from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from domains.crm.models.client import Client
from domains.real_estate.api.v1.schemas.estate import PropertyCreateSchema
from domains.real_estate.models.estate import Estate, Property
from domains.real_estate.models.property_purchase import PropertyPurchase
from domains.real_estate.payment_contract import PROPERTY_PURCHASE_PURPOSE_TYPE
from domains.real_estate.services.estate import create_property, quick_update_plot
from domains.real_estate.services.payment_intents import (
    create_property_purchase_payment_intent,
    expected_next_payment_amount,
    installment_schedule,
)
from domains.real_estate.services.purchase import create_property_purchase
from domains.real_estate.services.settlement import (
    apply_property_purchase_receipt,
    approve_property_purchase,
    cancel_property_purchase,
    default_property_purchase,
    expire_property_purchase,
)
from finance.models import FinanceAccount
from system.identity.models.user import User
from system.payments.models import ConfirmedReceipt, PaymentAttempt, PaymentIntent


class PropertyPurchaseSettlementTests(TestCase):
    def setUp(self):
        self.creator = User.objects.create_user(
            username="settlement-admin",
            email="settlement-admin@example.com",
            password="StrongPass123!",
        )
        buyer = User.objects.create_user(
            username="settlement-buyer",
            email="settlement-buyer@example.com",
            password="StrongPass123!",
            first_name="Settlement",
            last_name="Buyer",
        )
        self.client = Client.objects.create(user=buyer)
        self.estate = Estate.objects.create(
            estate_name="Settlement Estate",
            estate_code="SETTLE-001",
            estate_type="residential",
            developer_company_name="Bomach",
            estate_description="Settlement test estate.",
            country="Nigeria",
            country_code="NGA",
            state="Lagos",
            city_town="Lekki",
            precise_address="Lekki",
            price_per_sqm=Decimal("100000.00"),
            estate_status="available",
            reservation_allowed=True,
            reservation_threshold_percent=Decimal("20.00"),
            installment_allowed=True,
            max_installment_months=12,
            reservation_payment_window_hours=48,
        )
        self.property = Property.objects.create(
            estate=self.estate,
            property_type="plot",
            property_name="Plot SET-01",
            price=Decimal("10000000.00"),
            plot_size=Decimal("500.00"),
            plot_size_unit="sqm",
            status="available",
        )
        self.finance_account = FinanceAccount.objects.create(
            account_type=FinanceAccount.ACCOUNT_TYPE.BANK,
            display_name="Settlement Collections",
            currency="NGN",
            bank_name="Test Bank",
            account_number="1234567890",
            account_name="Bomach Test",
            created_by=self.creator,
        )
        self.counter = 0

    def purchase(self, mode, *, months=None, prop=None):
        return create_property_purchase(
            property_id=(prop or self.property).id,
            client_id=self.client.id,
            mode=mode,
            agreed_price=Decimal("10000000.00"),
            installment_months=months,
            created_by=self.creator,
        )

    def receipt(self, purchase, amount, *, paid_at=None):
        self.counter += 1
        amount = Decimal(str(amount))
        paid_at = paid_at or timezone.now()
        intent = PaymentIntent.objects.create(
            idempotency_key=f"settlement-intent-{self.counter}",
            purpose_type=PROPERTY_PURCHASE_PURPOSE_TYPE,
            purpose_id=str(purchase.id),
            amount=amount,
            currency="NGN",
            status=PaymentIntent.STATUS.CONFIRMED,
            description="Settlement test",
            accounting_total_due=purchase.agreed_price,
            accounting_total_tax=Decimal("0.00"),
            accounting_prior_paid=purchase.amount_paid,
            revenue_account_code="4200",
            created_by=self.creator,
            confirmed_at=paid_at,
        )
        attempt = PaymentAttempt.objects.create(
            intent=intent,
            provider="fake",
            idempotency_key=f"settlement-attempt-{self.counter}",
            provider_reference=f"ATTEMPT-{self.counter}",
            status=PaymentAttempt.STATUS.SUCCEEDED,
            amount=amount,
            currency="NGN",
            completed_at=paid_at,
        )
        return ConfirmedReceipt.objects.create(
            intent=intent,
            attempt=attempt,
            provider="fake",
            provider_transaction_reference=f"TX-{self.counter}",
            amount=amount,
            currency="NGN",
            paid_at=paid_at,
            finance_account=self.finance_account,
            finance_posted_at=timezone.now(),
        )

    def test_approval_starts_fresh_snapshotted_payment_window(self):
        purchase = self.purchase(PropertyPurchase.MODE_RESERVATION)
        purchase.payment_window_expires_at = timezone.now() - timedelta(hours=1)
        purchase.save(update_fields=["payment_window_expires_at", "updated_at"])
        approved = approve_property_purchase(
            purchase_id=purchase.id, approved_by=self.creator
        )
        self.property.refresh_from_db()
        self.assertEqual(approved.status, PropertyPurchase.STATUS_AWAITING_PAYMENT)
        self.assertEqual(approved.payment_window_hours, 48)
        self.assertGreater(approved.payment_window_expires_at, timezone.now())
        self.assertEqual(approved.next_payment_due_at, approved.payment_window_expires_at)
        self.assertEqual(self.property.status, "available")
        self.assertIsNone(self.property.owner_id)

    def test_reservation_threshold_reserves_without_owner(self):
        purchase = self.purchase(PropertyPurchase.MODE_RESERVATION)
        approve_property_purchase(purchase_id=purchase.id, approved_by=self.creator)
        purchase.refresh_from_db()
        receipt = self.receipt(purchase, "2000000.00")
        settled = apply_property_purchase_receipt(receipt)
        self.property.refresh_from_db()
        receipt.refresh_from_db()
        self.assertEqual(settled.status, PropertyPurchase.STATUS_RESERVED)
        self.assertEqual(settled.amount_paid, Decimal("2000000.00"))
        self.assertEqual(self.property.status, "reserved")
        self.assertIsNone(self.property.owner_id)
        self.assertEqual(self.property.client_name, "Settlement Buyer")
        self.assertIsNotNone(receipt.applied_at)

    def test_full_verified_money_sells_and_assigns_client_user(self):
        purchase = self.purchase(PropertyPurchase.MODE_FULL_PAYMENT)
        approve_property_purchase(purchase_id=purchase.id, approved_by=self.creator)
        purchase.refresh_from_db()
        settled = apply_property_purchase_receipt(
            self.receipt(purchase, purchase.agreed_price)
        )
        self.property.refresh_from_db()
        self.assertEqual(settled.status, PropertyPurchase.STATUS_FULLY_PAID)
        self.assertEqual(self.property.status, "sold")
        self.assertEqual(self.property.owner_id, self.client.user_id)
        self.assertEqual(self.property.client_name, "Settlement Buyer")

    def test_duplicate_receipt_application_is_idempotent(self):
        purchase = self.purchase(PropertyPurchase.MODE_RESERVATION)
        approve_property_purchase(purchase_id=purchase.id, approved_by=self.creator)
        purchase.refresh_from_db()
        receipt = self.receipt(purchase, "2000000.00")
        apply_property_purchase_receipt(receipt)
        again = apply_property_purchase_receipt(receipt)
        receipt.refresh_from_db()
        self.assertEqual(again.amount_paid, Decimal("2000000.00"))
        self.assertIsNotNone(receipt.applied_at)

    def test_installment_without_reservation_policy_activates_on_first_payment(self):
        estate = Estate.objects.create(
            estate_name="Installment Only",
            estate_code="INST-ONLY",
            estate_type="residential",
            developer_company_name="Bomach",
            estate_description="Installment only.",
            country="Nigeria",
            country_code="NGA",
            state="Lagos",
            city_town="Ikeja",
            precise_address="Ikeja",
            price_per_sqm=Decimal("100000.00"),
            estate_status="available",
            reservation_allowed=False,
            reservation_threshold_percent=None,
            installment_allowed=True,
            max_installment_months=4,
            reservation_payment_window_hours=24,
        )
        prop = Property.objects.create(
            estate=estate,
            property_type="plot",
            property_name="Plot INST-01",
            price=Decimal("10000000.00"),
            plot_size=Decimal("500.00"),
            plot_size_unit="sqm",
            status="available",
        )
        purchase = self.purchase(
            PropertyPurchase.MODE_INSTALLMENT, months=4, prop=prop
        )
        approve_property_purchase(purchase_id=purchase.id, approved_by=self.creator)
        purchase.refresh_from_db()
        settled = apply_property_purchase_receipt(
            self.receipt(purchase, expected_next_payment_amount(purchase))
        )
        prop.refresh_from_db()
        self.assertEqual(settled.status, PropertyPurchase.STATUS_INSTALLMENT_ACTIVE)
        self.assertEqual(prop.status, "reserved")
        self.assertIsNone(prop.owner_id)
        self.assertIsNotNone(settled.next_payment_due_at)

    def test_payment_intent_requires_exact_next_amount(self):
        purchase = self.purchase(PropertyPurchase.MODE_RESERVATION)
        approve_property_purchase(purchase_id=purchase.id, approved_by=self.creator)
        purchase.refresh_from_db()
        with self.assertRaises(ValidationError):
            create_property_purchase_payment_intent(
                purchase,
                amount=Decimal("1000000.00"),
                idempotency_key="wrong-reservation-amount",
                created_by=self.creator,
            )
        intent, created = create_property_purchase_payment_intent(
            purchase,
            amount=Decimal("2000000.00"),
            idempotency_key="exact-reservation-amount",
            created_by=self.creator,
        )
        self.assertTrue(created)
        self.assertEqual(intent.amount, Decimal("2000000.00"))

    def test_installment_schedule_is_exact(self):
        purchase = self.purchase(PropertyPurchase.MODE_INSTALLMENT, months=6)
        schedule = installment_schedule(purchase)
        self.assertEqual(sum(schedule, Decimal("0.00")), purchase.agreed_price)
        self.assertGreaterEqual(schedule[0], purchase.reservation_amount)

    def test_final_installment_completes_sale(self):
        purchase = self.purchase(PropertyPurchase.MODE_INSTALLMENT, months=2)
        approve_property_purchase(purchase_id=purchase.id, approved_by=self.creator)
        purchase.refresh_from_db()
        apply_property_purchase_receipt(
            self.receipt(purchase, expected_next_payment_amount(purchase))
        )
        purchase.refresh_from_db()
        settled = apply_property_purchase_receipt(
            self.receipt(purchase, expected_next_payment_amount(purchase))
        )
        self.property.refresh_from_db()
        self.assertEqual(settled.status, PropertyPurchase.STATUS_FULLY_PAID)
        self.assertEqual(self.property.status, "sold")
        self.assertEqual(self.property.owner_id, self.client.user_id)

    def test_on_time_payment_can_apply_after_local_expiry(self):
        purchase = self.purchase(PropertyPurchase.MODE_RESERVATION)
        approve_property_purchase(purchase_id=purchase.id, approved_by=self.creator)
        purchase.refresh_from_db()
        receipt = self.receipt(
            purchase,
            "2000000.00",
            paid_at=purchase.payment_window_expires_at - timedelta(minutes=1),
        )
        purchase.status = PropertyPurchase.STATUS_EXPIRED
        purchase.save(update_fields=["status", "updated_at"])
        settled = apply_property_purchase_receipt(receipt)
        self.assertEqual(settled.status, PropertyPurchase.STATUS_RESERVED)

    def test_late_payment_after_expiry_requires_reconciliation(self):
        purchase = self.purchase(PropertyPurchase.MODE_RESERVATION)
        approve_property_purchase(purchase_id=purchase.id, approved_by=self.creator)
        purchase.refresh_from_db()
        receipt = self.receipt(
            purchase,
            "2000000.00",
            paid_at=purchase.payment_window_expires_at + timedelta(minutes=1),
        )
        purchase.status = PropertyPurchase.STATUS_EXPIRED
        purchase.save(update_fields=["status", "updated_at"])
        with self.assertRaises(ValidationError):
            apply_property_purchase_receipt(receipt)
        receipt.refresh_from_db()
        self.assertIsNone(receipt.applied_at)

    def test_unpaid_purchase_can_expire_and_remain_available(self):
        purchase = self.purchase(PropertyPurchase.MODE_FULL_PAYMENT)
        approve_property_purchase(purchase_id=purchase.id, approved_by=self.creator)
        purchase.refresh_from_db()
        expired = expire_property_purchase(
            purchase_id=purchase.id,
            at=purchase.payment_window_expires_at + timedelta(minutes=1),
        )
        self.property.refresh_from_db()
        self.assertEqual(expired.status, PropertyPurchase.STATUS_EXPIRED)
        self.assertEqual(self.property.status, "available")

    def test_cancellation_after_verified_money_is_blocked(self):
        purchase = self.purchase(PropertyPurchase.MODE_RESERVATION)
        approve_property_purchase(purchase_id=purchase.id, approved_by=self.creator)
        purchase.refresh_from_db()
        apply_property_purchase_receipt(self.receipt(purchase, "2000000.00"))
        with self.assertRaises(ValidationError):
            cancel_property_purchase(
                purchase_id=purchase.id, cancelled_by=self.creator
            )

    def test_overdue_installment_defaults_to_hold(self):
        purchase = self.purchase(PropertyPurchase.MODE_INSTALLMENT, months=4)
        approve_property_purchase(purchase_id=purchase.id, approved_by=self.creator)
        purchase.refresh_from_db()
        apply_property_purchase_receipt(
            self.receipt(purchase, expected_next_payment_amount(purchase))
        )
        purchase.refresh_from_db()
        defaulted = default_property_purchase(
            purchase_id=purchase.id,
            at=(
                purchase.next_payment_due_at
                + timedelta(hours=purchase.payment_window_hours, minutes=1)
            ),
        )
        self.property.refresh_from_db()
        self.assertEqual(defaulted.status, PropertyPurchase.STATUS_DEFAULTED)
        self.assertEqual(self.property.status, "hold")
        self.assertIsNone(self.property.owner_id)

    def test_on_time_installment_can_apply_after_local_default(self):
        purchase = self.purchase(PropertyPurchase.MODE_INSTALLMENT, months=4)
        approve_property_purchase(purchase_id=purchase.id, approved_by=self.creator)
        purchase.refresh_from_db()
        apply_property_purchase_receipt(
            self.receipt(purchase, expected_next_payment_amount(purchase))
        )
        purchase.refresh_from_db()
        paid_at = purchase.next_payment_due_at + timedelta(
            hours=purchase.payment_window_hours
        ) - timedelta(minutes=1)
        default_property_purchase(
            purchase_id=purchase.id,
            at=paid_at + timedelta(minutes=2),
        )
        # Simulate delayed provider delivery: local default happened before the
        # webhook arrived, but verified paid_at is inside the due+grace window.
        receipt = self.receipt(
            purchase,
            expected_next_payment_amount(purchase),
            paid_at=paid_at,
        )
        settled = apply_property_purchase_receipt(receipt)
        self.property.refresh_from_db()
        self.assertIn(
            settled.status,
            {
                PropertyPurchase.STATUS_INSTALLMENT_ACTIVE,
                PropertyPurchase.STATUS_FULLY_PAID,
            },
        )
        self.assertNotEqual(self.property.status, "hold")

    def test_operator_cannot_bypass_settlement_status(self):
        purchase = self.purchase(PropertyPurchase.MODE_RESERVATION)
        with self.assertRaises(ValidationError):
            quick_update_plot(self.property, {"status": "reserved"})
        with self.assertRaises(ValidationError):
            quick_update_plot(self.property, {"status": "sold"})
        with self.assertRaises(ValidationError):
            quick_update_plot(self.property, {"status": "hold"})
        self.assertEqual(purchase.status, PropertyPurchase.STATUS_AWAITING_APPROVAL)

    def test_direct_create_cannot_start_reserved_or_sold(self):
        payload = PropertyCreateSchema(
            property_type="plot",
            property_name="Illegal sold plot",
            price=Decimal("1000000.00"),
            status="sold",
            plot_size=Decimal("500.00"),
            plot_size_unit="sqm",
        )
        with self.assertRaises(ValidationError):
            create_property(payload, estate=self.estate)
