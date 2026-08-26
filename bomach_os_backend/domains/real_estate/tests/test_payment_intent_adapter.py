from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from domains.crm.models.client import Client
from domains.real_estate.models.estate import Estate, Property
from domains.real_estate.models.property_purchase import PropertyPurchase
from domains.real_estate.services.payment_intents import (
    PURPOSE_TYPE,
    create_property_purchase_payment_intent,
)
from domains.real_estate.services.purchase import create_property_purchase
from system.identity.models.user import User


class PropertyPurchasePaymentIntentAdapterTests(TestCase):
    def setUp(self):
        self.creator = User.objects.create_user(
            username="intent-admin",
            email="intent-admin@example.com",
            password="StrongPass123!",
        )
        buyer = User.objects.create_user(
            username="intent-buyer",
            email="intent-buyer@example.com",
            password="StrongPass123!",
            first_name="Intent",
            last_name="Buyer",
        )
        self.client = Client.objects.create(user=buyer)
        self.estate = Estate.objects.create(
            estate_name="Intent Estate",
            estate_code="INTENT-001",
            estate_type="residential",
            developer_company_name="Bomach",
            estate_description="Intent adapter estate.",
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
            property_name="Plot INT-01",
            price=Decimal("10000000.00"),
            plot_size=Decimal("500.00"),
            plot_size_unit="sqm",
            status="available",
        )
        self.purchase = create_property_purchase(
            property_id=self.property.id,
            client_id=self.client.id,
            mode=PropertyPurchase.MODE_RESERVATION,
            agreed_price=Decimal("10000000.00"),
            created_by=self.creator,
        )
        self.purchase.status = PropertyPurchase.STATUS_AWAITING_PAYMENT
        self.purchase.payment_window_expires_at = timezone.now() + timedelta(hours=48)
        self.purchase.save(
            update_fields=["status", "payment_window_expires_at", "updated_at"]
        )

    def test_adapter_snapshots_purchase_without_mutating_real_estate_state(self):
        intent, created = create_property_purchase_payment_intent(
            self.purchase,
            amount=Decimal("2000000.00"),
            idempotency_key="purchase-intent-1",
            created_by=self.creator,
        )
        self.purchase.refresh_from_db()
        self.property.refresh_from_db()
        self.assertTrue(created)
        self.assertEqual(intent.purpose_type, PURPOSE_TYPE)
        self.assertEqual(intent.purpose_id, str(self.purchase.id))
        self.assertEqual(intent.amount, Decimal("2000000.00"))
        self.assertEqual(intent.accounting_total_due, self.purchase.agreed_price)
        self.assertEqual(intent.accounting_prior_paid, Decimal("0.00"))
        self.assertEqual(intent.revenue_account_code, "4200")
        self.assertEqual(self.purchase.amount_paid, Decimal("0.00"))
        self.assertEqual(self.purchase.status, PropertyPurchase.STATUS_AWAITING_PAYMENT)
        self.assertEqual(self.property.status, "available")
        self.assertIsNone(self.property.owner_id)

    def test_adapter_rejects_purchase_that_is_not_payable(self):
        self.purchase.status = PropertyPurchase.STATUS_AWAITING_APPROVAL
        self.purchase.save(update_fields=["status", "updated_at"])
        with self.assertRaises(ValidationError):
            create_property_purchase_payment_intent(
                self.purchase,
                amount=Decimal("2000000.00"),
                idempotency_key="purchase-intent-not-payable",
                created_by=self.creator,
            )
