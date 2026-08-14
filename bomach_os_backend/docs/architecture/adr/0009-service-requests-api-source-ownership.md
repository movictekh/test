# ADR 0009: Service Operations Owns the Service Requests API Source

- Status: Accepted
- Date: 2026-08-14

## Decision

The Service Requests HTTP source is owned by Service Operations:

```text
domains/service_operations/api/v1/
├── routers/
│   └── service_requests.py
└── schemas/
    └── service_requests.py
```

The legacy source paths are removed:

```text
services/api/v1/service_requests.py
services/api/schema/service_request_schemas.py
```

The global API composition root imports and registers the Service Requests router directly
from `domains.service_operations.api.v1`.

## Domain ownership

Service Requests are part of the Service Operations lifecycle:

```text
Catalogue
  -> Service Request
  -> Quote
  -> Invoice
  -> Service Order
  -> Execution
  -> Deliverable
```

Finance-owned behavior called from the Service Requests router remains Finance-owned. This
source move does not alter Finance endpoint implementation or payment-review business rules.

## OpenAPI compatibility policy

This project does not generate an SDK from OpenAPI/Swagger, so generated `operationId` values
are not treated as a hard compatibility boundary for internal source moves.

Architecture migrations must preserve the contract that application clients actually depend on:

- paths;
- HTTP methods;
- tags;
- parameters;
- request bodies;
- responses;
- authentication/security behavior;
- permissions and branch scoping.

Explicit operation IDs already pinned in the catalogue router remain unchanged, but future
source moves do not need to preserve automatically generated module-derived operation IDs.

## Compatibility

ARCH-5C preserves:

- all Service Request paths and HTTP methods;
- tags, parameters, request/response schemas and security;
- permissions and branch scoping;
- Finance service calls and behavior;
- Django model identity;
- migration state.

No Finance endpoint implementation is modified.
