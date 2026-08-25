import importlib
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from system.automation.engine import _evaluate_conditions, evaluate_workflow_rules
from system.automation.models import WorkflowRule, WorkflowRuleLog


class AutomationBoundaryTests(SimpleTestCase):
    def test_models_preserve_user_identity_and_canonical_modules(self):
        for model in (WorkflowRule, WorkflowRuleLog):
            self.assertTrue(model._meta.label.startswith("user."))
            self.assertTrue(model.__module__.startswith("system.automation.models."))

    def test_legacy_modules_are_true_aliases(self):
        pairs = [
            ("user.models.workflow_rule", "system.automation.models.workflow_rule"),
            ("user.services.workflow_engine", "system.automation.engine"),
            (
                "user.api.schemas.workflow_rule",
                "system.automation.api.v1.schemas.workflow_rule",
            ),
            (
                "user.api.v1.workflow_rule",
                "system.automation.api.v1.routers.workflow_rule",
            ),
        ]
        for legacy, canonical in pairs:
            self.assertIs(
                importlib.import_module(legacy),
                importlib.import_module(canonical),
            )

    def test_condition_engine_preserves_and_semantics(self):
        instance = SimpleNamespace(status="approved", amount=200)
        self.assertTrue(
            _evaluate_conditions(
                [
                    {"field": "status", "operator": "eq", "value": "approved"},
                    {"field": "amount", "operator": "gte", "value": 100},
                ],
                instance,
            )
        )
        self.assertFalse(
            _evaluate_conditions(
                [
                    {"field": "status", "operator": "eq", "value": "approved"},
                    {"field": "amount", "operator": "lt", "value": 100},
                ],
                instance,
            )
        )

    def test_public_engine_remains_legacy_compatible(self):
        legacy = importlib.import_module("user.services.workflow_engine")
        self.assertIs(legacy.evaluate_workflow_rules, evaluate_workflow_rules)
