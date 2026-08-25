from django.test import SimpleTestCase

from domains.people.models.responsibility import Responsibility
from system.identity.models.user import User


class ResponsibilityBoundaryTests(SimpleTestCase):
    def test_historical_identity_and_user_relation_are_preserved(self):
        self.assertEqual(Responsibility._meta.label, "user.Responsibility")
        self.assertIs(
            Responsibility._meta.get_field("user").remote_field.model,
            User,
        )

    def test_legacy_mixed_module_exports_canonical_responsibility(self):
        from user.models.sops import Responsibility as LegacyResponsibility

        self.assertIs(LegacyResponsibility, Responsibility)
