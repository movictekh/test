# ADR 0007: Service Operations Owns the Catalogue and Configuration API

- Status: Accepted
- Date: 2026-08-14

## Decision

The genuine Service Operations catalogue/configuration HTTP source is owned by:

```text
domains/service_operations/api/v1/
├── routers/
│   └── catalogue.py
└── schemas/
    └── catalogue.py
```

The application API root imports the v1 router directly from the Service Operations domain.

The legacy source paths:

```text
services/api/v1/services.py
services/api/schema/service_catalogue_schemas.py
```

are removed rather than retained as forwarding wrappers.

Existing consumers that still need catalogue transport types import those types directly from
the domain-owned schema path. In particular, the current Service Requests router imports
`FieldTypeOut` from `domains.service_operations.api.v1.schemas.catalogue`.

## Scope

This slice owns:

- service catalogue;
- service core configuration;
- subservices;
- request-form configuration;
- pricing configuration;
- workflow configuration;
- workflow stages;
- branch activation;
- catalogue publication controls.

## Explicit non-scope

This migration does not claim ownership of unrelated code that happens to live in the legacy
`services` Django app.

In particular:

- Budget and Expense are Finance-owned;
- generic CRM Lead/Funnel logic is CRM-owned;
- Property is Real Estate-owned;
- Payment is Finance-owned long-term;
- Invoice remains provisionally Service Operations-owned because it is still tightly coupled
  to ServiceRequest -> Quote -> Invoice -> ServiceOrder.

## Versioning

Only the HTTP contract is versioned. Service Operations business models/services/selectors are
not placed beneath `api/v1`.

## Compatibility

The move preserves:

- all public paths;
- HTTP methods;
- OpenAPI tags;
- legacy generated OpenAPI operation IDs, captured from the final pre-move global OpenAPI schema and now made explicit;
- authentication and permission decorators;
- request/response schemas;
- Django model identity;
- migration state.

Making operation IDs explicit is a permanent API-contract decision, not a compatibility shim.
