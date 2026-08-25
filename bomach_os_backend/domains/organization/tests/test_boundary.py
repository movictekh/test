import importlib

from django.test import SimpleTestCase

from domains.organization.models import (
    Branch,
    BranchBusinessHours,
    CompanyBranding,
    CompanyPreferences,
    CompanyProfile,
    Department,
    Role,
    RoleDescription,
    RoleReportingLine,
    RoleResource,
    Unit,
)


class OrganizationBoundaryTests(SimpleTestCase):
    def test_models_preserve_user_identity_and_use_canonical_modules(self):
        models = [
            CompanyProfile,
            CompanyBranding,
            CompanyPreferences,
            Branch,
            BranchBusinessHours,
            Department,
            Unit,
            Role,
            RoleReportingLine,
            RoleResource,
            RoleDescription,
        ]
        for model in models:
            self.assertTrue(model._meta.label.startswith("user."))
            self.assertTrue(model.__module__.startswith("domains.organization.models."))

    def test_legacy_model_modules_are_true_aliases(self):
        pairs = [
            ("user.models.company", "domains.organization.models.company"),
            ("user.models.branch", "domains.organization.models.branch"),
            ("user.models.roles", "domains.organization.models.roles"),
            ("user.models.role", "domains.organization.models.role"),
            ("user.models.role_reporting", "domains.organization.models.role_reporting"),
            ("user.models.role_resources", "domains.organization.models.role_resources"),
            ("user.models.role_description", "domains.organization.models.role_description"),
        ]
        for legacy, canonical in pairs:
            self.assertIs(
                importlib.import_module(legacy),
                importlib.import_module(canonical),
            )

    def test_legacy_clean_api_modules_are_true_aliases(self):
        pairs = [
            (
                "user.api.schemas.company",
                "domains.organization.api.v1.schemas.company",
            ),
            (
                "user.api.schemas.branch",
                "domains.organization.api.v1.schemas.branch",
            ),
            (
                "user.api.v1.company",
                "domains.organization.api.v1.routers.company",
            ),
            (
                "user.api.v1.branch",
                "domains.organization.api.v1.routers.branch",
            ),
        ]
        for legacy, canonical in pairs:
            self.assertIs(
                importlib.import_module(legacy),
                importlib.import_module(canonical),
            )
