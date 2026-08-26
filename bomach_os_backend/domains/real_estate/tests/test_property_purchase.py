from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from domains.crm.models.client import Client
from domains.real_estate.models.estate import Estate, Property
from domains.real_estate.models.property_purchase import PropertyPurchase
from domains.real_estate.services.purchase import create_property_purchase, create_purchase_client
from system.identity.models.user import User


class PropertyPurchaseTests(TestCase):
    def setUp(self):
        self.creator = User.objects.create_user(
            username="purchase-admin", email="purchase-admin@example.com", password="StrongPass123!"
        )
        buyer = User.objects.create_user(
            username="buyer", email="buyer@example.com", password="StrongPass123!",
            first_name="Ada", last_name="Buyer"
        )
        self.client = Client.objects.create(user=buyer, phone="+2348012345678", company_name="Buyer Ltd")

    def estate(self, code="PURCHASE-001", **overrides):
        data = {
            "estate_name": "Purchase Estate",
            "estate_code": code,
            "estate_type": "residential",
            "developer_company_name": "Bomach",
            "estate_description": "Purchase test estate.",
            "country": "Nigeria",
            "country_code": "NGA",
            "state": "Lagos",
            "city_town": "Lekki",
            "precise_address": "Lekki",
            "price_per_sqm": Decimal("100000.00"),
            "estate_status": "available",
            "reservation_allowed": True,
            "reservation_threshold_percent": Decimal("20.00"),
            "installment_allowed": True,
            "max_installment_months": 12,
            "reservation_payment_window_hours": 48,
        }
        data.update(overrides)
        return Estate.objects.create(**data)

    def property(self, estate=None, name="Plot P-01"):
        return Property.objects.create(
            estate=estate, property_type="plot", property_name=name,
            price=Decimal("10000000.00"), plot_size=Decimal("500.00"),
            plot_size_unit="sqm", status="available"
        )

    def test_manual_purchaser_defaults_to_no_portal_credentials_or_email(self):
        with patch("domains.real_estate.services.purchase.send_client_welcome_email") as send_email:
            client = create_purchase_client(
                email="newbuyer@example.com", first_name="New", last_name="Buyer",
                phone_number="+2348098765432", company_name="New Buyer Ltd"
            )
        self.assertFalse(client.user.has_usable_password())
        self.assertEqual(client.company_name, "New Buyer Ltd")
        send_email.assert_not_called()

    def test_reservation_snapshots_terms_without_mutating_property(self):
        estate = self.estate()
        prop = self.property(estate)
        before = timezone.now()
        purchase = create_property_purchase(
            property_id=prop.id, client_id=self.client.id,
            mode=PropertyPurchase.MODE_RESERVATION,
            agreed_price=Decimal("10000000.00"), created_by=self.creator
        )
        prop.refresh_from_db()
        self.assertEqual(purchase.status, PropertyPurchase.STATUS_AWAITING_APPROVAL)
        self.assertEqual(purchase.reservation_threshold_percent, Decimal("20.00"))
        self.assertEqual(purchase.reservation_amount, Decimal("2000000.00"))
        self.assertGreaterEqual(purchase.payment_window_expires_at, before + timedelta(hours=47, minutes=59))
        self.assertEqual(prop.status, "available")
        self.assertIsNone(prop.owner_id)
        self.assertEqual(prop.client_name, "")

    def test_full_payment_does_not_snapshot_reservation_terms(self):
        estate = self.estate(code="PURCHASE-002")
        prop = self.property(estate, "Plot P-02")
        purchase = create_property_purchase(
            property_id=prop.id, client_id=self.client.id,
            mode=PropertyPurchase.MODE_FULL_PAYMENT, created_by=self.creator
        )
        self.assertEqual(purchase.agreed_price, prop.price)
        self.assertIsNone(purchase.reservation_threshold_percent)
        self.assertIsNone(purchase.installment_months)

    def test_installment_snapshots_months_and_reservation_policy(self):
        estate = self.estate(code="PURCHASE-003")
        prop = self.property(estate, "Plot P-03")
        purchase = create_property_purchase(
            property_id=prop.id, client_id=self.client.id,
            mode=PropertyPurchase.MODE_INSTALLMENT,
            agreed_price=Decimal("12000000.00"), installment_months=6,
            created_by=self.creator
        )
        self.assertEqual(purchase.installment_months, 6)
        self.assertEqual(purchase.reservation_amount, Decimal("2400000.00"))

    def test_installment_cannot_exceed_estate_maximum(self):
        estate = self.estate(code="PURCHASE-004")
        prop = self.property(estate, "Plot P-04")
        with self.assertRaises(ValidationError):
            create_property_purchase(
                property_id=prop.id, client_id=self.client.id,
                mode=PropertyPurchase.MODE_INSTALLMENT, installment_months=13,
                created_by=self.creator
            )

    def test_disabled_reservation_is_rejected(self):
        estate = self.estate(
            code="PURCHASE-005", reservation_allowed=False,
            reservation_threshold_percent=None
        )
        prop = self.property(estate, "Plot P-05")
        with self.assertRaises(ValidationError):
            create_property_purchase(
                property_id=prop.id, client_id=self.client.id,
                mode=PropertyPurchase.MODE_RESERVATION, created_by=self.creator
            )

    def test_only_one_active_purchase_per_property(self):
        estate = self.estate(code="PURCHASE-006")
        prop = self.property(estate, "Plot P-06")
        create_property_purchase(
            property_id=prop.id, client_id=self.client.id,
            mode=PropertyPurchase.MODE_FULL_PAYMENT, created_by=self.creator
        )
        with self.assertRaises(ValidationError):
            create_property_purchase(
                property_id=prop.id, client_id=self.client.id,
                mode=PropertyPurchase.MODE_FULL_PAYMENT, created_by=self.creator
            )

    def test_snapshot_survives_later_estate_policy_change(self):
        estate = self.estate(code="PURCHASE-007")
        prop = self.property(estate, "Plot P-07")
        purchase = create_property_purchase(
            property_id=prop.id, client_id=self.client.id,
            mode=PropertyPurchase.MODE_RESERVATION, created_by=self.creator
        )
        estate.reservation_threshold_percent = Decimal("30.00")
        estate.save()
        purchase.refresh_from_db()
        self.assertEqual(purchase.reservation_threshold_percent, Decimal("20.00"))
        self.assertEqual(purchase.reservation_amount, Decimal("2000000.00"))

    def test_standalone_property_is_not_accepted_in_phase_three(self):
        prop = self.property(None, "Standalone P-01")
        with self.assertRaises(ValidationError):
            create_property_purchase(
                property_id=prop.id, client_id=self.client.id,
                mode=PropertyPurchase.MODE_FULL_PAYMENT, created_by=self.creator
            )
