import importlib

from django.test import SimpleTestCase

from domains.organization.models.role import Role
from domains.organization.models.role_career_path import RoleCareerPath
from domains.organization.models.role_sop import RoleSOP
from domains.organization.models.role_success_playbook import RoleSuccessPlaybookItem
from domains.organization.models.role_workflows import (
    RoleDailyRoutineItem,
    RoleTaskTemplate,
)
from domains.organization.models.sop import SOP


class OrganizationRoleKnowledgeBoundaryTests(SimpleTestCase):
    def test_historical_labels_are_preserved(self):
        expected = {
            RoleCareerPath: "user.RoleCareerPath",
            RoleSOP: "user.RoleSOP",
            RoleSuccessPlaybookItem: "user.RoleSuccessPlaybookItem",
            RoleTaskTemplate: "user.RoleTaskTemplate",
            RoleDailyRoutineItem: "user.RoleDailyRoutineItem",
            SOP: "user.SOP",
        }
        for model, label in expected.items():
            self.assertEqual(model._meta.label, label)

    def test_role_metadata_resolves_to_canonical_role_and_sop(self):
        self.assertIs(
            RoleCareerPath._meta.get_field("from_role").remote_field.model,
            Role,
        )
        self.assertIs(
            RoleCareerPath._meta.get_field("to_role").remote_field.model,
            Role,
        )
        self.assertIs(RoleSOP._meta.get_field("role").remote_field.model, Role)
        self.assertIs(RoleSOP._meta.get_field("sop").remote_field.model, SOP)
        self.assertIs(
            RoleSuccessPlaybookItem._meta.get_field("role").remote_field.model,
            Role,
        )
        self.assertIs(
            RoleTaskTemplate._meta.get_field("role").remote_field.model,
            Role,
        )
        self.assertIs(
            RoleDailyRoutineItem._meta.get_field("role").remote_field.model,
            Role,
        )

    def test_single_owner_legacy_modules_are_true_aliases(self):
        pairs = [
            (
                "user.models.role_career_path",
                "domains.organization.models.role_career_path",
            ),
            ("user.models.role_sop", "domains.organization.models.role_sop"),
            (
                "user.models.role_success_playbook",
                "domains.organization.models.role_success_playbook",
            ),
            (
                "user.models.role_workflows",
                "domains.organization.models.role_workflows",
            ),
        ]
        for legacy, canonical in pairs:
            self.assertIs(
                importlib.import_module(legacy),
                importlib.import_module(canonical),
            )
