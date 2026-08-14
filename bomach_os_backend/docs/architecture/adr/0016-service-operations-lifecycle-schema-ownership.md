# ADR 0016: Service Operations Owns Its Lifecycle HTTP Schemas

- Status: Accepted
- Date: 2026-08-14

## Decision

Service Operations routers no longer import transport schemas from the legacy mixed module:

```text
services/api/schema/schemas.py
```

Schemas used by the Service Operations lifecycle are extracted, together with their class
dependencies, into:

```text
domains/service_operations/api/v1/schemas/lifecycle.py
```

The affected domain routers include:

- Categories;
- Service Leads;
- Service Requests;
- Quotes;
- Service Invoices;
- Service Orders / execution / deliverables.

## Why extraction instead of deleting the old file

The legacy `schemas.py` still has consumers outside the Service Operations domain, including
Finance-adjacent Payment transport and potentially other transitional routers.

Deleting or wholesale-moving the file would incorrectly force unrelated domain migration into
this step.

Therefore ARCH-5J establishes the important boundary:

```text
Service Operations routers
        ↓
domains/service_operations/api/v1/schemas/lifecycle.py
```

while:

```text
legacy non-domain routers
        ↓
services/api/schema/schemas.py
```

remains transitional until those routers are migrated to their real owners.

## One lifecycle schema file

A single `lifecycle.py` is used instead of creating separate `quotes.py`, `orders.py`,
`invoices.py`, etc. schema modules because many of these transport types reference one another
and form one coherent Service Operations API lifecycle. Splitting them further now would add
indirection without a real ownership benefit.

## Compatibility

Class names and definitions are copied without behavioral changes. Service Operations HTTP
paths, methods, request/response contracts, permissions, Django model identity and migration
state remain unchanged. Generated OpenAPI operation IDs are not a compatibility requirement
because the project does not generate SDK clients.
