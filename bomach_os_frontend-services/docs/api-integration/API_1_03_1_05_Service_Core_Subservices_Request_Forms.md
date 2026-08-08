# API-1.03–API-1.05 — Service Core, Subservices, Request Forms

## Batch scope

This batch completes three adjacent Service Administration integration stages:

```text
API-1.03 — real Service core creation
API-1.04 — real Subservice persistence
API-1.05 — real Request Form persistence
```

Pricing, Workflow, Branch Activation and Publish remain later stages.

## Category dependency

The backend requires `category_id` for Service creation.

The frontend therefore loads:

```text
GET /categories
permission: categories.list
```

and passes the selected stable category ID to:

```text
POST /services
permission: services.create
```

No category ID is hard-coded or inferred from division text.

## Initial create sequence

The visual wizard is preserved, but this integration batch persists only the
domains whose backend stages are complete:

```text
POST /services
    ↓
PUT /services/{service_id}/subservices
    ↓
POST /services/{service_id}/request-forms
    ↓
GET /services/catalogue/{service_id}
```

The Service is always created as `draft`.

This is deliberate because backend publish currently requires:

- an active request form;
- an active pricing config;
- at least one active branch.

Pricing and branch integration have not landed yet.

## Partial failure semantics

These are separate backend transactions, so the browser cannot make the entire
three-endpoint sequence database-atomic.

If Service core creation succeeds and a later step fails, the frontend does
**not** pretend the whole operation rolled back. It reports that a Service draft
already exists and identifies the failed setup stage.

This prevents blind retries that could create duplicate Services.

## Exact permissions for the integrated create wizard

The full initial setup action requires:

```text
services.create
categories.list
service_subservices.update
service_request_forms.create
```

`services.create` alone is insufficient because the wizard persists nested
resources owned by separate backend permission domains.

## Owner role

The current wizard previously collected an owner role as free text.

The backend accepts `owner_role_id`, not a role name string.

Until a verified role-list/selector contract is integrated, the frontend does
not invent or guess a role ID. `owner_role_id` is omitted during Service create.

## Request Form Builder

Request Forms are backend resources scoped to a Service:

```text
GET /services/{service_id}/request-forms
POST /services/{service_id}/request-forms
PUT /services/{service_id}/request-forms/{form_id}
```

There is no global request-form list endpoint.

The frontend therefore scopes the Request Form Builder to a selected Service
instead of issuing an N+1 request across the entire catalogue.

Field types are loaded from:

```text
GET /services/request-field-types
permission: service_request_forms.list
```

The palette is driven by that backend response rather than a hard-coded list.

## Status adapter

Backend Request Form lifecycle:

```text
draft
active
archived
```

The existing frontend UI domain historically used `inactive`. During this batch
the mapper explicitly translates:

```text
frontend inactive -> backend archived
backend archived   -> frontend inactive
```

A later UI-domain cleanup may rename the visible lifecycle value without
changing the backend contract.
