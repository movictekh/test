from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from domains.real_estate.api.v1.schemas.estate import EstateUpdateSchema
from domains.real_estate.models.estate import Estate
from domains.real_estate.services.estate import update_estate


class EstateSalesPolicyTests(TestCase):
    def estate(self, **overrides):
        data = {
            "estate_name": "Policy Estate",
            "estate_code": "POLICY-001",
            "estate_type": "residential",
            "developer_company_name": "Bomach",
            "estate_description": "Policy test estate.",
            "country": "Nigeria",
            "country_code": "NGA",
            "state": "Lagos",
            "city_town": "Lekki, Eti-Osa",
            "precise_address": "Lekki",
            "price_per_sqm": Decimal("100000.00"),
            "estate_status": "available",
        }
        data.update(overrides)
        return Estate(**data)

    def test_defaults_are_conservative(self):
        estate = self.estate()
        estate.full_clean()
        self.assertFalse(estate.reservation_allowed)
        self.assertIsNone(estate.reservation_threshold_percent)
        self.assertFalse(estate.installment_allowed)
        self.assertIsNone(estate.max_installment_months)
        self.assertEqual(estate.reservation_payment_window_hours, 72)

    def test_reservation_requires_threshold(self):
        with self.assertRaises(ValidationError) as error:
            self.estate(reservation_allowed=True).full_clean()
        self.assertIn("reservation_threshold_percent", error.exception.message_dict)

    def test_disabled_reservation_rejects_threshold(self):
        with self.assertRaises(ValidationError) as error:
            self.estate(
                reservation_allowed=False,
                reservation_threshold_percent=Decimal("20.00"),
            ).full_clean()
        self.assertIn("reservation_threshold_percent", error.exception.message_dict)

    def test_threshold_cannot_exceed_one_hundred_percent(self):
        with self.assertRaises(ValidationError) as error:
            self.estate(
                reservation_allowed=True,
                reservation_threshold_percent=Decimal("101.00"),
            ).full_clean()
        self.assertIn("reservation_threshold_percent", error.exception.message_dict)

    def test_disabled_installment_rejects_max_months(self):
        with self.assertRaises(ValidationError) as error:
            self.estate(
                installment_allowed=False,
                max_installment_months=12,
            ).full_clean()
        self.assertIn("max_installment_months", error.exception.message_dict)

    def test_valid_enabled_policy(self):
        self.estate(
            reservation_allowed=True,
            reservation_threshold_percent=Decimal("20.00"),
            installment_allowed=True,
            max_installment_months=12,
            reservation_payment_window_hours=48,
        ).full_clean()

    def test_update_service_can_disable_and_clear_policy_terms(self):
        estate = self.estate(
            reservation_allowed=True,
            reservation_threshold_percent=Decimal("20.00"),
            installment_allowed=True,
            max_installment_months=12,
        )
        estate.save()

        update_estate(
            estate,
            EstateUpdateSchema(
                reservation_allowed=False,
                reservation_threshold_percent=None,
                installment_allowed=False,
                max_installment_months=None,
            ),
        )

        estate.refresh_from_db()
        self.assertFalse(estate.reservation_allowed)
        self.assertIsNone(estate.reservation_threshold_percent)
        self.assertFalse(estate.installment_allowed)
        self.assertIsNone(estate.max_installment_months)
