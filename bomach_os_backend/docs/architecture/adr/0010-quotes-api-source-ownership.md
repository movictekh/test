# ADR 0010: Service Operations Owns the Quotes API Source

- Status: Accepted
- Date: 2026-08-14

## Decision

The Quotes HTTP router is owned by Service Operations:

```text
domains/service_operations/api/v1/routers/quotes.py
```

The legacy router path is removed:

```text
services/api/v1/quotes.py
```

The global API composition root imports and registers the Quotes router directly from
`domains.service_operations.api.v1`.

## Why only the router moves now

Quote schemas currently live inside the shared legacy file:

```text
services/api/schema/schemas.py
```

That file also contains Service Order, execution-task, deliverable and other schemas.
Moving or duplicating only the Quote classes now would introduce an unnecessary partial
schema split and more cross-file ceremony.

The shared schema file remains temporarily in place until the adjacent Service Operations
lifecycle routers (especially Orders/Execution and Invoice-adjacent transport) have been
migrated. At that point it can be split once by actual ownership.

## Domain ownership

Quotes belong to the Service Operations lifecycle:

```text
Service Request
  -> Quote
  -> Invoice / payment condition
  -> Service Order
```

The router may reference the provisional Invoice model as part of quote-to-invoice workflow,
but this decision does not modify Finance endpoints or transfer Finance-owned payment logic.

## Compatibility

ARCH-5D preserves:

- Quote paths and HTTP methods;
- tags, parameters, request bodies, responses and security;
- RBAC and branch scoping;
- email and quote lifecycle behavior;
- Django model identity;
- migration state.

Generated OpenAPI operation IDs are not a hard compatibility boundary because this project
does not generate SDK clients from Swagger/OpenAPI.
