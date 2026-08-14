# ADR 0011: Service Operations Owns Service Orders and Execution Source

- Status: Accepted
- Date: 2026-08-14

## Decision

Service Operations owns the Service Orders / execution HTTP router:

```text
domains/service_operations/api/v1/routers/orders.py
```

The legacy router is removed:

```text
services/api/v1/orders.py
```

Service Order creation commands also move out of the legacy utility module and into the
domain service layer:

```text
domains/service_operations/services.py
```

Specifically:

- `create_manual_order(...)`
- `create_order_from_invoice(...)`

The old helper module is removed:

```text
services/utils/service_orders.py
```

The Invoice router remains at its current transitional location for now, but calls
`domains.service_operations.services.create_order_from_invoice` because Service Operations,
not the Invoice transport module, owns creation of a Service Order.

## Boundary

Service Order creation is part of the Service Operations lifecycle even when triggered by an
Invoice:

```text
Quote
  -> Invoice / payment threshold
  -> create Service Order
  -> milestones
  -> execution tasks
  -> deliverables
```

Finance/payment rules remain separate. This ADR does not change Finance endpoints or payment
implementation.

## Shared schemas

`services/api/schema/schemas.py` remains temporarily because it currently mixes Quote,
Invoice-adjacent, Service Order, execution-task and deliverable schemas. It will be split in
one coordinated Service Operations schema migration after the adjacent lifecycle routers have
moved.

## Compatibility

ARCH-5E preserves:

- `/orders` paths and HTTP methods;
- tags, parameters, request/response schemas and security;
- RBAC and branch scope;
- Service Order creation behavior;
- Invoice-to-order behavior;
- Django model identity and migration state.

Generated OpenAPI operation IDs are not a hard compatibility boundary because no SDK is
generated from Swagger/OpenAPI.
