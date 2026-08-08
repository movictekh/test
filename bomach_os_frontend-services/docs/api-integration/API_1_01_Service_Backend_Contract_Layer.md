# API-1.01 — Service Backend Contract Layer

## Purpose

Define the real Service Administration backend boundary without switching the
completed UI screens away from their existing aggregate mock workspace yet.

This keeps the migration ordered:

```text
backend transport DTO
    ↓
real backend API client
    ↓
mapper
    ↓
frontend domain model
    ↓
TanStack Query
    ↓
screen
```

API-1.01 implements the first three layers only.

## Backend source of truth

Verified from:

```text
bomach_os_backend/services/api/schema/service_catalogue_schemas.py
bomach_os_backend/services/api/v1/services.py
```

## Files introduced

```text
src/modules/service-administration/api/
├── service-administration.contracts.ts
├── service-administration.backend-api.ts
├── service-administration.backend-api.test.ts
└── service-administration.keys.ts

src/modules/service-administration/mappers/
├── service-catalogue.mapper.ts
└── service-catalogue.mapper.test.ts
```

The existing:

```text
service-administration.api.ts
```

remains the aggregate MSW/workspace adapter until API-1.02+ migrates individual
screens.

## Important transport rules

### Backend names remain backend names

DTO fields use the exact backend payload names:

```text
category_id
owner_role_id
client_visibility
active_request_form_id
active_pricing_config_id
active_workflow_id
```

Frontend filter inputs may use camelCase, but the API client serializes them to
the exact backend query parameter names.

### Decimal transport

Backend schemas use Python Decimal.

The frontend transport boundary accepts:

```ts
type BackendDecimal = string | number
```

so domain/UI code does not depend on a serializer-specific Decimal representation.

### created_by_id

Some backend create schemas expose `created_by_id`, but backend route code
defaults ownership from `request.user`.

The frontend contract therefore intentionally does not require or normally send
`created_by_id` for new records.

### Pagination

The backend uses Django Ninja `LimitOffsetPagination` on:

```text
GET /services
GET /services/catalogue
GET /services/pricing-configs
```

The frontend transport contract represents those responses as:

```ts
interface LimitOffsetPageDto<T> {
  items: T[]
  count: number
}
```

The branch activation matrix is not paginated and remains an array response.

## Catalogue domain mapping

Screens must not consume backend catalogue DTOs directly.

The mapper adapts:

```text
ServiceCatalogueCardDto
ServiceCatalogueDetailDto
```

into the existing:

```text
ServiceCatalogueItem
```

domain model.

This lets API-1.02 replace data transport without rewriting the finished visual
screen at the same time.

## Readiness rule

Readiness follows the actual backend publish requirement:

1. active request form;
2. active pricing config;
3. at least one active branch.

Workflow is deliberately **not** included because the current backend publish
route does not require one.

## Scope intentionally deferred

API-1.01 does not:

- replace `serviceAdministrationQueries.workspace()`;
- make Service Catalogue perform live reads;
- enable live Service create/update/delete;
- retire Service Administration MSW handlers;
- wire Command Center.

Those are later API-1 stages.
