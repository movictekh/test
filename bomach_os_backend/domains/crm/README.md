# CRM domain

`domains.crm` owns the existing customer-relationship identities that
historically live in Django's `user` app:

- `user.Lead`
- `user.Client`
- `user.Partner`
- `user.PartnerAgreement`

This source move does **not** merge `user.Lead` with the newer
`services.Lead` already owned by `domains.marketing_sales`. They are separate
persisted models with different schemas and workflows. Consolidation, if ever
desired, requires a data/API migration and is outside architecture cleanup.

Historical Django labels, tables, migrations, URLs, permission keys and legacy
Python module paths remain compatible.
