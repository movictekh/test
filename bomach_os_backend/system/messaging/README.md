# System Messaging

`system.messaging` owns reusable outbound messaging mechanisms shared across
Bomach OS domains.

## Email — Phase 1

`system.messaging.email.providers.zeptomail.send_zepto_email()` is the
canonical ZeptoMail transport.

The provider adapter owns provider-specific transport only: endpoint/sender
configuration, authorization, payload construction, HTTP execution, error
logging, and returning the provider response.

Business email composition remains in its current owners during this phase.
That includes authentication/2FA, estate invoices, marketing, employee/client/
associate/shareholder onboarding, and task-assignment templates.

`user.utils.send_email._send_zepto_email` remains as a compatibility alias.
Existing callers are intentionally unchanged.

Direct `django.core.mail.send_mail()` usage elsewhere is also intentionally
unchanged in this phase. Transport convergence is later work.
