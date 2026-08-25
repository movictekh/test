import importlib

from django.test import SimpleTestCase

from domains.crm.models.client import Client, Lead
from domains.crm.models.partner import Partner, PartnerAgreement
from domains.marketing_sales.models.sales import Lead as ModernSalesLead
from domains.people.models.employee import Employee


class CRMBoundaryTests(SimpleTestCase):
    def test_historical_model_identity_is_preserved(self):
        self.assertEqual(Lead._meta.label, "user.Lead")
        self.assertEqual(Client._meta.label, "user.Client")
        self.assertEqual(Partner._meta.label, "user.Partner")
        self.assertEqual(PartnerAgreement._meta.label, "user.PartnerAgreement")

    def test_legacy_and_modern_leads_remain_distinct(self):
        self.assertIsNot(Lead, ModernSalesLead)
        self.assertEqual(ModernSalesLead._meta.label, "services.Lead")
        self.assertIs(
            Lead._meta.get_field("assigned_to").remote_field.model,
            Employee,
        )
        self.assertIs(
            ModernSalesLead._meta.get_field("referral_partner").remote_field.model,
            Partner,
        )

    def test_legacy_model_and_api_modules_are_true_aliases(self):
        pairs = [
            ("user.models.client", "domains.crm.models.client"),
            ("user.models.partner", "domains.crm.models.partner"),
            ("user.api.schemas.clients", "domains.crm.api.v1.schemas.clients"),
            ("user.api.schemas.partner", "domains.crm.api.v1.schemas.partner"),
            ("user.api.v1.clients", "domains.crm.api.v1.routers.clients"),
            ("user.api.v1.partner", "domains.crm.api.v1.routers.partner"),
        ]
        for legacy, canonical in pairs:
            self.assertIs(
                importlib.import_module(legacy),
                importlib.import_module(canonical),
            )
