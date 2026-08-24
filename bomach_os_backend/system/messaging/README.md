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

## Email — Phase 2

`system.messaging.email.services.send_email()` is now the canonical
provider-agnostic service used by application/business code.

The dependency direction is:

```text
business/domain composition
    -> system.messaging.email.services.send_email
    -> system.messaging.email.providers.zeptomail.send_zepto_email
```

Existing business templates and composition remain outside `system.messaging`.
`user.utils.send_email` is still a compatibility/composition module, but its
email-producing helpers now depend on the generic service instead of the
ZeptoMail adapter.

Marketing is the first domain caller migrated away from
`user.utils.send_email`: its router already owns the subject/body composition,
so it imports the generic service directly while preserving the local
`send_marketing_email` symbol for behavioral/test compatibility.

The Phase 1 private `_send_zepto_email` compatibility alias remains available.
Direct Django `send_mail()` users are still unchanged; transport convergence is
deliberately deferred.

## Email — Phase 3

Business email composition now starts moving out of the legacy
`user.utils.send_email` catch-all and into the domain that owns the business
meaning.

This phase moves the clearest ownership cases:

- Real Estate invoice composition -> `domains.real_estate.email`
- Project Operations task-assignment composition ->
  `domains.project_operations.email`

Those domain modules depend on
`system.messaging.email.services.send_email()` and do not import the ZeptoMail
provider directly.

The existing Real Estate and Project Operations callers now import their
domain-owned functions directly. `user.utils.send_email` keeps compatibility
re-exports so older imports continue to resolve to the same canonical function
objects.

Authentication/2FA, employee/client/associate onboarding, shareholder access,
and the generic custom-email helper intentionally remain in the legacy module
until their owning Identity, People, and Organization boundaries are handled.
Direct Django `send_mail()` paths are still outside this phase.
