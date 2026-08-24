from django.test import SimpleTestCase


class DomainEmailCompositionOwnershipTests(SimpleTestCase):
    def test_real_estate_invoice_email_uses_domain_owner_and_legacy_alias(self):
        from domains.real_estate.api.v1.routers.estate_property_invoice import (
            send_invoice_email as router_binding,
        )
        from domains.real_estate.email import send_invoice_email as canonical
        from user.utils.send_email import send_invoice_email as legacy

        self.assertIs(router_binding, canonical)
        self.assertIs(legacy, canonical)

    def test_project_operations_task_email_uses_domain_owner_and_legacy_aliases(self):
        from domains.project_operations.email import (
            send_associate_task_assignment_email as canonical_associate,
            send_task_assignment_email as canonical_task,
        )
        from domains.project_operations.services import (
            send_associate_task_assignment_email as service_associate,
            send_task_assignment_email as service_task,
        )
        from user.utils.send_email import (
            send_associate_task_assignment_email as legacy_associate,
            send_task_assignment_email as legacy_task,
        )

        self.assertIs(service_task, canonical_task)
        self.assertIs(service_associate, canonical_associate)
        self.assertIs(legacy_task, canonical_task)
        self.assertIs(legacy_associate, canonical_associate)
