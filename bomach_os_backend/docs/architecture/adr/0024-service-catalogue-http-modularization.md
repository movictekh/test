# ADR 0024: Service Catalogue HTTP Source Is Split by Configuration Responsibility

- Status: Accepted
- Date: 2026-08-14

## Context

The Service catalogue router exceeded 1,000 lines and combined three independently evolving
HTTP responsibilities.

## Decision

Keep the external `/services` API contract while splitting source into:

```text
api/v1/routers/
├── catalogue.py
├── service_configuration.py
├── service_branch_activation.py
└── _catalogue_support.py
```

### `catalogue.py`

Core catalogue responsibilities:

- catalogue list/detail;
- Service CRUD and publish;
- subservices.

### `service_configuration.py`

Configuration workspace responsibilities:

- request field types;
- request forms;
- pricing configurations;
- workflows and workflow stages.

### `service_branch_activation.py`

Branch activation matrix and branch activation mutations.

### `_catalogue_support.py`

Private v1 transport helpers and serializers shared by these routers. It exposes no HTTP
surface.

## Route precedence

Configuration and branch routers are registered before the core catalogue router because the
core surface includes generic `/{service_id}` routes.

## Application-service imports

Routers/support import the concrete catalogue application-service module directly:

```python
from domains.service_operations.services import catalogue as domain_services
```

They do not depend on the non-forwarding service package as if it exposed application
functions.

## Compatibility

All existing explicit catalogue operation IDs remain unchanged.

The refactor preserves:

- `/services` paths;
- HTTP methods;
- tags;
- request/response schemas;
- RBAC/security;
- model/migration state.
