from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase

from system.audit.api.v1.routers.audit_log import audit_log_api as canonical_router
from system.audit.models import AuditLog as CanonicalAuditLog
from system.audit.services import log_activity as canonical_log_activity
from user.api.v1.audit_log import audit_log_api as legacy_router
from user.models.audit_log import AuditLog as LegacyAuditLog
from user.utils.audit import log_activity as legacy_log_activity


class AuditCompatibilityTests(SimpleTestCase):
    def test_legacy_model_is_canonical_model(self):
        self.assertIs(LegacyAuditLog, CanonicalAuditLog)
        self.assertEqual(CanonicalAuditLog._meta.label, "user.AuditLog")

    def test_legacy_service_is_canonical_service(self):
        self.assertIs(legacy_log_activity, canonical_log_activity)

    def test_legacy_router_is_canonical_router(self):
        self.assertIs(legacy_router, canonical_router)

    @patch("system.audit.models.AuditLog.objects.create")
    def test_log_activity_preserves_ip_and_payload_mapping(self, create_mock):
        request = SimpleNamespace(
            META={
                "HTTP_X_FORWARDED_FOR": "203.0.113.10, 10.0.0.2",
                "REMOTE_ADDR": "10.0.0.1",
            }
        )

        canonical_log_activity(
            audit_type="login",
            activity="User logged in",
            user=None,
            request=request,
            audit_status="success",
            metadata={"source": "test"},
        )

        create_mock.assert_called_once_with(
            audit_type="login",
            audit_status="success",
            activity="User logged in",
            user=None,
            ip_address="203.0.113.10",
            metadata={"source": "test"},
        )


class AuditSelectorTests(TestCase):
    def test_selector_filters_by_type_and_status(self):
        from system.audit.selectors import list_audit_logs

        CanonicalAuditLog.objects.create(
            audit_type=CanonicalAuditLog.AuditType.LOGIN,
            audit_status=CanonicalAuditLog.AuditStatus.SUCCESS,
            activity="Successful login",
        )
        CanonicalAuditLog.objects.create(
            audit_type=CanonicalAuditLog.AuditType.LOGIN_FAILED,
            audit_status=CanonicalAuditLog.AuditStatus.WARNING,
            activity="Failed login",
        )

        queryset = list_audit_logs(
            audit_type=CanonicalAuditLog.AuditType.LOGIN,
            audit_status=CanonicalAuditLog.AuditStatus.SUCCESS,
        )

        self.assertEqual(queryset.count(), 1)
        self.assertEqual(queryset.get().activity, "Successful login")
