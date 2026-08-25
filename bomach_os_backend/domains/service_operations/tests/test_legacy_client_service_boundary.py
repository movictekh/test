from django.test import SimpleTestCase

from domains.service_operations.models.legacy_client_service import (
    ClientService,
    ServiceRequest,
)
from domains.service_operations.models.requests import (
    ServiceRequest as ModernServiceRequest,
)
from system.identity.models.user import User


class LegacyClientServiceBoundaryTests(SimpleTestCase):
    def test_historical_identity_is_preserved(self):
        self.assertEqual(ClientService._meta.label, "user.ClientService")
        self.assertEqual(ServiceRequest._meta.label, "user.ServiceRequest")

    def test_legacy_and_modern_requests_remain_distinct(self):
        self.assertIsNot(ServiceRequest, ModernServiceRequest)
        self.assertEqual(ModernServiceRequest._meta.label, "services.ServiceRequest")
        self.assertIs(
            ServiceRequest._meta.get_field("client").remote_field.model,
            User,
        )
        self.assertIs(
            ServiceRequest._meta.get_field("service").remote_field.model,
            ClientService,
        )

    def test_legacy_mixed_module_exports_canonical_models(self):
        from user.models.client_service import (
            ClientService as LegacyClientService,
            ServiceRequest as LegacyServiceRequest,
        )

        self.assertIs(LegacyClientService, ClientService)
        self.assertIs(LegacyServiceRequest, ServiceRequest)
