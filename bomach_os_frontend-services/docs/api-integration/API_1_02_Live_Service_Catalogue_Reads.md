# API-1.02 — Live Service Catalogue Reads

## Scope

API-1.02 makes the Service Catalogue the first Service Administration surface
that reads real backend data.

Live endpoints:

```text
GET /services/catalogue
GET /services/catalogue/{service_id}
```

Required backend permissions remain:

```text
services.list
services.view
```

The existing route/navigation permission gates already use those exact values.

## Data flow

```text
GET /services/catalogue
    ↓
ServiceCatalogueCardDto
    ↓
mapServiceCatalogueCard
    ↓
TanStack Query catalogueList
    ↓
ServiceCatalogueScreen
```

Detail:

```text
user selects View
    ↓
GET /services/catalogue/{id}
    ↓
ServiceCatalogueDetailDto
    ↓
mapServiceCatalogueDetail
    ↓
ConfigureServiceWorkspace in read-only mode
```

## Why Catalogue mutations are temporarily withheld

Before API-1.02 the Service Catalogue and its mutations shared one mock workspace.

Once the list becomes a real backend read, leaving Create, Duplicate or
Configure Save pointed at the mock workspace would create split-brain behavior:

```text
real backend list
+
mock-only writes
=
misleading UI
```

Therefore, on the live Catalogue route:

```text
Create Service   -> temporarily withheld
Duplicate        -> temporarily withheld
Configure Save   -> temporarily withheld
View Detail      -> live and enabled when services.view exists
```

Those affordances return progressively when their real backend mutation stages
land.

This is deliberate migration behavior, not a permission change.

## Other Service Administration surfaces

Calculator Library, Request Form Builder, Workflow Designer and Branch
Activation continue using the existing aggregate mock workspace until their
respective API-1 stages.

## Pagination

API-1.02 requests up to 100 catalogue records as an interim read strategy.

Router-search-driven remote filtering and proper user-facing limit/offset
pagination are intentionally deferred to API-1.10.

## Command Center

No Command Center data contract is changed by API-1.02.
