import importlib

from django.test import SimpleTestCase

from system.approvals.api.v1.routers.approval import approval_api
from system.approvals.models import (
    ApprovalDecision,
    ApprovalFlow,
    ApprovalFlowStep,
    ApprovalRequest,
)


class ApprovalsBoundaryTests(SimpleTestCase):
    def test_models_preserve_user_identity_and_canonical_modules(self):
        for model in (
            ApprovalFlow,
            ApprovalFlowStep,
            ApprovalRequest,
            ApprovalDecision,
        ):
            self.assertTrue(model._meta.label.startswith("user."))
            self.assertTrue(model.__module__.startswith("system.approvals.models."))

    def test_legacy_modules_are_true_aliases(self):
        pairs = [
            ("user.models.approval", "system.approvals.models.approval"),
            (
                "user.api.schemas.approval",
                "system.approvals.api.v1.schemas.approval",
            ),
            (
                "user.api.v1.approval",
                "system.approvals.api.v1.routers.approval",
            ),
        ]
        for legacy, canonical in pairs:
            self.assertIs(
                importlib.import_module(legacy),
                importlib.import_module(canonical),
            )

    def test_legacy_router_object_is_canonical(self):
        legacy = importlib.import_module("user.api.v1.approval")
        self.assertIs(legacy.approval_api, approval_api)
