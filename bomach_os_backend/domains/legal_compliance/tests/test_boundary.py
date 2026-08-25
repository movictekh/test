import importlib

from django.test import SimpleTestCase

from domains.legal_compliance.models.cases import LegalCase
from domains.legal_compliance.models.compliance import ComplianceRecord
from domains.legal_compliance.models.compliance_audit import Audit
from domains.organization.models.roles import Department
from system.audit.models import AuditLog


class LegalComplianceBoundaryTests(SimpleTestCase):
    def test_historical_model_identity_is_preserved(self):
        self.assertEqual(LegalCase._meta.label, "user.LegalCase")
        self.assertEqual(ComplianceRecord._meta.label, "user.ComplianceRecord")
        self.assertEqual(Audit._meta.label, "user.Audit")

    def test_compliance_audit_is_distinct_from_technical_audit_log(self):
        self.assertIsNot(Audit, AuditLog)
        self.assertEqual(AuditLog._meta.label, "user.AuditLog")
        self.assertIs(
            ComplianceRecord._meta.get_field("department").remote_field.model,
            Department,
        )

    def test_legacy_model_and_api_modules_are_true_aliases(self):
        pairs = [
            ("user.models.cases", "domains.legal_compliance.models.cases"),
            ("user.models.compliance", "domains.legal_compliance.models.compliance"),
            (
                "user.models.compliance_audit",
                "domains.legal_compliance.models.compliance_audit",
            ),
            ("user.api.schemas.cases", "domains.legal_compliance.api.v1.schemas.cases"),
            (
                "user.api.schemas.compliance",
                "domains.legal_compliance.api.v1.schemas.compliance",
            ),
            ("user.api.schemas.audit", "domains.legal_compliance.api.v1.schemas.audit"),
            ("user.api.v1.cases", "domains.legal_compliance.api.v1.routers.cases"),
            (
                "user.api.v1.compliance",
                "domains.legal_compliance.api.v1.routers.compliance",
            ),
            ("user.api.v1.audit", "domains.legal_compliance.api.v1.routers.audit"),
        ]
        for legacy, canonical in pairs:
            self.assertIs(
                importlib.import_module(legacy),
                importlib.import_module(canonical),
            )
