from django.test import SimpleTestCase

from system.messaging.email.services import send_text_email


class ServiceOperationsEmailBoundaryTests(SimpleTestCase):
    def test_api_routers_do_not_own_email_transport_or_dead_composition(self):
        from domains.service_operations.api.v1.routers import invoices, quotes

        self.assertFalse(hasattr(invoices, "send_mail"))
        self.assertFalse(hasattr(invoices, "_client_email"))
        self.assertFalse(hasattr(invoices, "_portal_invoice_url"))
        self.assertFalse(hasattr(invoices, "_send_invoice_email"))

        self.assertFalse(hasattr(quotes, "send_mail"))
        self.assertFalse(hasattr(quotes, "_client_email"))
        self.assertFalse(hasattr(quotes, "_portal_quote_url"))
        self.assertFalse(hasattr(quotes, "_send_quote_email"))

    def test_service_layer_keeps_canonical_text_email_boundary(self):
        from domains.service_operations.services.invoices import (
            send_mail as invoice_service_mail,
        )
        from domains.service_operations.services.quotes import (
            send_mail as quote_service_mail,
        )

        self.assertIs(invoice_service_mail, send_text_email)
        self.assertIs(quote_service_mail, send_text_email)
