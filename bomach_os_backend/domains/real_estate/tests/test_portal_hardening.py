from datetime import timedelta
from decimal import Decimal
from types import SimpleNamespace

from django.test import TestCase
from django.utils import timezone

from domains.crm.models.client import Client
from domains.real_estate.api.v1.routers.purchase import (
    _payment_history_payload,
    my_purchase_detail,
)
from domains.real_estate.api.v1.schemas.purchase import PropertyPurchaseSchema
from domains.real_estate.models.estate import Estate, Property
from domains.real_estate.models.property_purchase import PropertyPurchase
from domains.real_estate.selectors.purchase import (
    get_client_property_purchase,
    list_client_property_purchases,
    list_property_purchases,
    payment_intents_for_purchase,
)
from domains.real_estate.services.purchase import create_property_purchase
from system.identity.models.user import User
from system.payments.models import PaymentAttempt, PaymentIntent


class RealEstatePortalHardeningTests(TestCase):
    def setUp(self):
        self.creator = User.objects.create_user(
            username="portal-admin",
            email="portal-admin@example.com",
            password="StrongPass123!",
        )
        buyer_user = User.objects.create_user(
            username="portal-buyer",
            email="portal-buyer@example.com",
            password="StrongPass123!",
            first_name="Ada",
            last_name="Buyer",
        )
        other_user = User.objects.create_user(
            username="portal-other",
            email="portal-other@example.com",
            password="StrongPass123!",
            first_name="Other",
            last_name="Buyer",
        )
        self.client = Client.objects.create(
            user=buyer_user,
            company_name="Ada Buyer Ltd",
        )
        self.other_client = Client.objects.create(
            user=other_user,
            company_name="Other Buyer Ltd",
        )
        self.estate = Estate.objects.create(
            estate_name="Portal Estate",
            estate_code="PORTAL-ESTATE-001",
            estate_type="residential",
            developer_company_name="Bomach",
            estate_description="Portal hardening estate.",
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
            property_name="Portal Plot A",
            price=Decimal("10000000.00"),
            plot_size=Decimal("500.00"),
            plot_size_unit="sqm",
            status="available",
        )
        self.other_property = Property.objects.create(
            estate=self.estate,
            property_type="plot",
            property_name="Portal Plot B",
            price=Decimal("12000000.00"),
            plot_size=Decimal("550.00"),
            plot_size_unit="sqm",
            status="available",
        )
        self.purchase = create_property_purchase(
            property_id=self.property.id,
            client_id=self.client.id,
            mode=PropertyPurchase.MODE_RESERVATION,
            created_by=self.creator,
        )
        self.other_purchase = create_property_purchase(
            property_id=self.other_property.id,
            client_id=self.other_client.id,
            mode=PropertyPurchase.MODE_FULL_PAYMENT,
            created_by=self.creator,
        )

    def test_client_selector_is_strictly_owner_scoped(self):
        rows = list(list_client_property_purchases(client=self.client))
        self.assertEqual([row.id for row in rows], [self.purchase.id])
        with self.assertRaises(PropertyPurchase.DoesNotExist):
            get_client_property_purchase(
                client=self.client,
                purchase_id=self.other_purchase.id,
            )

    def test_staff_purchase_list_supports_frontend_filters_and_search(self):
        by_client = list(list_property_purchases(client_id=self.client.id))
        self.assertEqual([row.id for row in by_client], [self.purchase.id])
        by_search = list(list_property_purchases(search="Portal Plot B"))
        self.assertEqual([row.id for row in by_search], [self.other_purchase.id])
        by_mode = list(
            list_property_purchases(mode=PropertyPurchase.MODE_RESERVATION)
        )
        self.assertEqual([row.id for row in by_mode], [self.purchase.id])

    def test_schema_exposes_progress_outstanding_labels_and_payability(self):
        self.purchase.status = PropertyPurchase.STATUS_AWAITING_PAYMENT
        self.purchase.amount_paid = Decimal("2500000.00")
        self.purchase.payment_window_expires_at = timezone.now() + timedelta(hours=2)
        self.purchase.save(
            update_fields=[
                "status",
                "amount_paid",
                "payment_window_expires_at",
                "updated_at",
            ]
        )
        self.assertEqual(
            PropertyPurchaseSchema.resolve_outstanding_balance(self.purchase),
            Decimal("7500000.00"),
        )
        self.assertEqual(
            PropertyPurchaseSchema.resolve_payment_progress_percent(self.purchase),
            Decimal("25.00"),
        )
        self.assertEqual(
            PropertyPurchaseSchema.resolve_status_display(self.purchase),
            "Awaiting Payment",
        )
        self.assertTrue(
            PropertyPurchaseSchema.resolve_can_request_payment(self.purchase)
        )

    def test_expired_initial_window_is_not_presented_as_payable(self):
        self.purchase.status = PropertyPurchase.STATUS_AWAITING_PAYMENT
        self.purchase.payment_window_expires_at = timezone.now() - timedelta(seconds=1)
        self.purchase.save(
            update_fields=[
                "status",
                "payment_window_expires_at",
                "updated_at",
            ]
        )
        self.assertFalse(
            PropertyPurchaseSchema.resolve_can_request_payment(self.purchase)
        )

    def test_payment_history_is_purchase_scoped_and_client_safe(self):
        intent = PaymentIntent.objects.create(
            idempotency_key="portal-history-intent-1",
            purpose_type="real_estate_property_purchase",
            purpose_id=str(self.purchase.id),
            amount=Decimal("2000000.00"),
            currency="NGN",
            status=PaymentIntent.STATUS.PROCESSING,
            description="Portal payment",
            expires_at=timezone.now() + timedelta(hours=1),
            created_by=self.creator,
            accounting_total_due=self.purchase.agreed_price,
            accounting_total_tax=Decimal("0.00"),
            accounting_prior_paid=Decimal("0.00"),
            revenue_account_code="4200",
        )
        attempt = PaymentAttempt.objects.create(
            intent=intent,
            provider="monnify",
            idempotency_key=f"{intent.reference}:monnify",
            provider_reference="INV-PORTAL-1",
            checkout_url="https://pay.example/portal",
            status=PaymentAttempt.STATUS.PENDING,
            amount=intent.amount,
            currency=intent.currency,
        )
        rows = list(payment_intents_for_purchase(self.purchase))
        self.assertEqual([row.id for row in rows], [intent.id])
        payload = _payment_history_payload(self.purchase)
        self.assertEqual(payload[0]["intent_reference"], intent.reference)
        self.assertEqual(
            payload[0]["attempts"][0]["reference"],
            attempt.reference,
        )
        self.assertNotIn("provider_metadata", payload[0]["attempts"][0])

    def test_my_detail_cannot_read_another_clients_purchase(self):
        request = SimpleNamespace(user=self.client.user)
        status, payload = my_purchase_detail(request, self.other_purchase.id)
        self.assertEqual(status, 404)
        self.assertEqual(payload["detail"], "Property purchase not found.")

    def test_my_detail_uses_authenticated_client_identity(self):
        request = SimpleNamespace(user=self.client.user)
        status, purchase = my_purchase_detail(request, self.purchase.id)
        self.assertEqual(status, 200)
        self.assertEqual(purchase.client_id, self.client.id)
