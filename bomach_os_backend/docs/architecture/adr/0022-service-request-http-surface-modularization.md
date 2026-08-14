# ADR 0022: Service Request HTTP Surface Is Split by Actor and Responsibility

- Status: Accepted
- Date: 2026-08-14

## Context

The Service Request v1 router had become an oversized HTTP module containing:

- staff/admin request management;
- client request intake and self-service;
- client quotes and invoices;
- legacy payment submission compatibility;
- client order/task/deliverable access;
- shared query and serialization helpers.

All endpoints belong to Service Operations and must keep the existing external
`/service-requests/` contract, but they do not need to share one source file.

## Decision

Split the source into:

```text
api/v1/routers/
├── service_request_admin.py
├── client_service_portal.py
├── service_requests.py
└── _service_request_support.py
```

### `service_request_admin.py`

Owns `/admin...` endpoints.

### `client_service_portal.py`

Owns client commercial/delivery endpoints:

- invoices;
- quotes;
- orders;
- execution tasks;
- deliverables;
- client payment-submission compatibility endpoints.

### `service_requests.py`

Owns request intake/self-service:

- choices/intake-form discovery;
- client summary;
- request list/create/get;
- request activities;
- request attachments.

### `_service_request_support.py`

Contains only shared v1 API-layer query, validation and serialization helpers.
It defines no HTTP endpoints.

## URL contract

All three routers remain mounted under:

```text
/service-requests/
```

Router registration order is:

1. staff/admin;
2. client commercial/delivery portal;
3. request self-service.

Generic `/{request_id}` routes therefore remain last.

## Compatibility

ARCH-5P preserves:

- URL paths;
- HTTP methods;
- request/response schemas;
- tags;
- security;
- RBAC;
- Finance delegation;
- Django model identity;
- migration state.

Generated OpenAPI operation IDs are not a compatibility requirement because this project does
not generate SDK clients.
