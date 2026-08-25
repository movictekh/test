import importlib

from django.test import SimpleTestCase

from domains.governance.models.announcement import Announcement
from domains.governance.models.board_resolution import BoardResolution
from domains.governance.models.meeting import Meeting
from domains.governance.models.policy import Policy
from domains.governance.models.shareholder import Shareholder
from domains.organization.models.branch import Branch
from domains.organization.models.roles import Department


class GovernanceBoundaryTests(SimpleTestCase):
    def test_historical_model_identity_is_preserved(self):
        expected = {
            Announcement: "user.Announcement",
            Policy: "user.Policy",
            Meeting: "user.Meeting",
            BoardResolution: "user.BoardResolution",
            Shareholder: "user.Shareholder",
        }
        for model, label in expected.items():
            self.assertEqual(model._meta.label, label)

    def test_announcement_targets_canonical_organization_models(self):
        self.assertIs(
            Announcement._meta.get_field("branches").remote_field.model,
            Branch,
        )
        self.assertIs(
            Announcement._meta.get_field("departments").remote_field.model,
            Department,
        )

    def test_legacy_model_and_api_modules_are_true_aliases(self):
        pairs = [
            ("user.models.announcement", "domains.governance.models.announcement"),
            ("user.models.policy", "domains.governance.models.policy"),
            ("user.models.meeting", "domains.governance.models.meeting"),
            (
                "user.models.board_resolution",
                "domains.governance.models.board_resolution",
            ),
            ("user.models.shareholder", "domains.governance.models.shareholder"),
            (
                "user.api.schemas.announcement",
                "domains.governance.api.v1.schemas.announcement",
            ),
            ("user.api.schemas.policy", "domains.governance.api.v1.schemas.policy"),
            ("user.api.schemas.meeting", "domains.governance.api.v1.schemas.meeting"),
            (
                "user.api.schemas.board_resolution",
                "domains.governance.api.v1.schemas.board_resolution",
            ),
            (
                "user.api.schemas.shareholder",
                "domains.governance.api.v1.schemas.shareholder",
            ),
            (
                "user.api.v1.announcement",
                "domains.governance.api.v1.routers.announcement",
            ),
            ("user.api.v1.policy", "domains.governance.api.v1.routers.policy"),
            ("user.api.v1.meeting", "domains.governance.api.v1.routers.meeting"),
            (
                "user.api.v1.board_resolution",
                "domains.governance.api.v1.routers.board_resolution",
            ),
            (
                "user.api.v1.shareholder",
                "domains.governance.api.v1.routers.shareholder",
            ),
        ]
        for legacy, canonical in pairs:
            self.assertIs(
                importlib.import_module(legacy),
                importlib.import_module(canonical),
            )
