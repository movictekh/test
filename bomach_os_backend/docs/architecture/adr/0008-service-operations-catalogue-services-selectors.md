# ADR 0008: Service Operations Catalogue Uses Domain Services and Selectors

- Status: Accepted
- Date: 2026-08-14

## Decision
The Service Operations catalogue/configuration API remains a single v1 router for now, but meaningful query and state-changing logic is moved out of the transport module.

```text
domains/service_operations/
├── services.py
├── selectors.py
└── api/v1/routers/catalogue.py
```

`selectors.py` owns reusable catalogue reads: the optimized Service queryset, filtering, and dependent-count lookup.

`services.py` owns meaningful catalogue/configuration mutations and validation helpers: choice validation, nested request/pricing/workflow child creation, and activation of request forms, pricing configs, and workflows.

`catalogue.py` continues to own route declarations, permissions, request/response schemas, transport error/status mapping, and HTTP response serialization. Serialization remains transport-owned because those dictionaries are the v1 response contract.

This ADR does not split the catalogue into multiple router files and does not move Service Operations models yet. Both are separate decisions.

## Compatibility
ARCH-5B preserves all 42 catalogue/configuration operations, public paths, HTTP methods, explicit operation IDs, OpenAPI tags, permission decorators, schemas, Django model identity, and migration state.
