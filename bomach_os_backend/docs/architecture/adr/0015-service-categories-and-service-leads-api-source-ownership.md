# ADR 0015: Service Operations Owns Categories and Service Leads API Source

- Status: Accepted
- Date: 2026-08-14

## Decision

The legacy Service Category and Service Lead HTTP routers belong to Service Operations:

```text
domains/service_operations/api/v1/routers/
├── categories.py
└── service_leads.py
```

The old router paths are removed:

```text
services/api/v1/categories.py
services/api/v1/service_leads.py
```

## Why these belong to Service Operations

`ServiceCategory` organizes the service catalogue.

`ServiceLead` is the narrower service-specific lead model that directly connects a client to a
Bomach service and estimated service value. It is distinct from the broader generic CRM Lead
model in `services/models/crm.py`.

Therefore generic Lead stays CRM-owned, while ServiceLead remains part of the service lifecycle.

## Shared transport schemas

Both routers still temporarily import classes from:

```text
services/api/schema/schemas.py
```

That file mixes Service Operations and Finance Payment schemas. The routers move first so the
next architecture step can split the shared file using actual remaining consumers instead of
duplicating schemas or adding forwarding modules.

## Compatibility

ARCH-5I preserves paths, HTTP methods, schemas, tags, security, RBAC, model identity and
migration state. Generated OpenAPI operation IDs are not treated as a hard compatibility
boundary because the project does not generate SDK clients.
