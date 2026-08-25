import importlib

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import SimpleTestCase

from system.identity.authentication import JWTAuthenticator
from system.identity.models.otp import OTPCode
from system.identity.models.token_blacklist import TokenBlacklist
from system.identity.models.user import User
from system.identity.services.auth import AuthService
from system.identity.services.jwt import JWTService


class IdentityBoundaryTests(SimpleTestCase):
    def test_historical_django_identity_is_preserved(self):
        self.assertEqual(User._meta.label, "user.User")
        self.assertEqual(OTPCode._meta.label, "user.OTPCode")
        self.assertEqual(TokenBlacklist._meta.label, "user.TokenBlacklist")
        self.assertEqual(settings.AUTH_USER_MODEL, "user.User")
        self.assertIs(get_user_model(), User)

    def test_otp_and_blacklist_relations_use_canonical_user(self):
        self.assertIs(OTPCode._meta.get_field("user").remote_field.model, User)
        self.assertIs(
            TokenBlacklist._meta.get_field("user").remote_field.model,
            User,
        )

    def test_legacy_modules_are_true_aliases(self):
        pairs = [
            ("user.models.user", "system.identity.models.user"),
            ("user.models.otp", "system.identity.models.otp"),
            (
                "user.models.token_blacklist",
                "system.identity.models.token_blacklist",
            ),
            (
                "user.api.schemas.auth",
                "system.identity.api.v1.schemas.auth",
            ),
            ("user.api.v1.auth", "system.identity.api.v1.routers.auth"),
            ("user.services.auth_service", "system.identity.services.auth"),
            ("user.services.jwt_service", "system.identity.services.jwt"),
            ("user.utils.auth", "system.identity.authentication"),
        ]
        for legacy, canonical in pairs:
            self.assertIs(
                importlib.import_module(legacy),
                importlib.import_module(canonical),
            )

    def test_service_and_authenticator_objects_are_canonical(self):
        self.assertIs(
            importlib.import_module("user.services.auth_service").AuthService,
            AuthService,
        )
        self.assertIs(
            importlib.import_module("user.services.jwt_service").JWTService,
            JWTService,
        )
        self.assertIs(
            importlib.import_module("user.utils.auth").JWTAuthenticator,
            JWTAuthenticator,
        )
