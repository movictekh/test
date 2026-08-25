from django.test import SimpleTestCase

from system.authorization import (
    check_obj_permission as canonical_check_obj_permission,
    require_permission as canonical_require_permission,
    scope_queryset as canonical_scope_queryset,
)
from user.utils.perm import (
    check_obj_permission as legacy_check_obj_permission,
    require_permission as legacy_require_permission,
    scope_queryset as legacy_scope_queryset,
)


class AuthorizationCompatibilityTests(SimpleTestCase):
    def test_legacy_permission_exports_are_canonical_objects(self):
        self.assertIs(legacy_require_permission, canonical_require_permission)
        self.assertIs(legacy_scope_queryset, canonical_scope_queryset)
        self.assertIs(legacy_check_obj_permission, canonical_check_obj_permission)
