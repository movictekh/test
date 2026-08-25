from django.test import SimpleTestCase

from shared.api.schema import MessageSchema as CanonicalMessageSchema
from services.api.schema.others import MessageSchema as LegacyMessageSchema


class SharedSchemaCompatibilityTests(SimpleTestCase):
    def test_legacy_message_schema_is_canonical_shared_schema(self):
        self.assertIs(LegacyMessageSchema, CanonicalMessageSchema)
