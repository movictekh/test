# ADR 0017: Service Operations Owns Its Core Model Source

- Status: Accepted
- Date: 2026-08-14

## Decision

The real source for the core Service Operations models moves from:

```text
services/models/service.py
```

to:

```text
domains/service_operations/models.py
```

Every moved Django model explicitly retains:

```python
class Meta:
    app_label = "services"
```

in addition to its existing metadata.

This preserves the existing Django model identities, database tables and migration ownership
under the installed `services` app.

## Compatibility shell

`services/models/service.py` remains intentionally as a thin Django compatibility shell:

```python
from domains.service_operations.models import *
```

This is not a business-logic forwarding layer. It exists because:

- `services` remains an installed Django app;
- existing migrations identify these models as `services.*`;
- `services.models` still imports `.service`;
- transitional modules such as `services.models.payment` import through
  `services.models.service`;
- changing the Django app label is a separate migration concern and is not part of this
  source-ownership refactor.

## Canonical imports

Code inside `domains/service_operations` imports models directly from:

```text
domains.service_operations.models
```

and does not depend on the compatibility shell.

Legacy/non-domain consumers may continue importing `services.models.service` until their own
domain migrations are performed.

## Scope

This move covers the models physically defined in the former `services/models/service.py`,
including catalogue/configuration, ServiceLead, commercial ServiceRequest, Quote,
ServiceOrder, milestones, execution tasks and deliverables.

It does not move:

- `Invoice` / `Payment` from `services/models/payment.py`;
- `ClientFeedback` from `services/models/feedback.py`;
- generic CRM models;
- Real Estate models;
- Budget / Expense;
- other mixed legacy `services` models.

Those are separate ownership decisions.

## Compatibility requirements

ARCH-5K preserves:

- `services.<ModelName>` Django labels;
- database table names;
- fields and relations;
- ordering;
- indexes and constraints;
- migration state;
- HTTP/OpenAPI contract.

A future true Django app-label migration, if ever desired, must be designed separately.
