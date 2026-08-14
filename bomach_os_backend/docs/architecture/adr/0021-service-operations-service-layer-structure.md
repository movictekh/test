# ADR 0021: Service Operations Application Services Are Grouped by Use-Case Family

- Status: Accepted
- Date: 2026-08-14

## Context

`domains/service_operations/services.py` accumulated two independent responsibilities:

1. catalogue/configuration mutations;
2. Service Order creation workflows.

Keeping both in one file would recreate the same god-file problem being removed elsewhere.

## Decision

Replace the single service module with:

```text
domains/service_operations/services/
├── __init__.py
├── catalogue.py
└── orders.py
```

### `catalogue.py`

Owns application operations for:

- request-form field creation;
- pricing-field creation;
- workflow-stage creation;
- activation of request forms;
- activation of pricing configurations;
- activation of workflows;
- validation helpers used only by those operations.

### `orders.py`

Owns:

- creating a Service Order from an Invoice after activation threshold;
- creating a manual Service Order;
- seeding milestones and recording creation activity as part of those use cases.

## Import rule

Consumers import concrete modules directly:

```python
from domains.service_operations.services.catalogue import activate_workflow
from domains.service_operations.services.orders import create_order_from_invoice
```

The package `__init__.py` does not re-export application-service functions.

This avoids a forwarding facade that would hide the actual responsibility boundary.

## File growth rule

Service-layer modules are split by use-case family, not by arbitrary function count.

Create another service module only when a genuinely separate family of state-changing business
operations emerges. Do not create empty modules for architectural symmetry.

## Compatibility

This is a source-organization refactor only. It preserves:

- business behavior;
- HTTP paths/methods/contracts;
- RBAC;
- Django model identity;
- database/migration state.
