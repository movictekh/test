# Service Catalogue

This document explains the backend model shape behind the Service Catalogue in
`Bomach_Service_Operations_OS_v1(1).html`.

Commercial request execution is documented separately in
[`service-requests.md`](service-requests.md).

The catalogue is intentionally built around `services.Service` as the canonical
service definition. The older `user.ClientService` model is left unchanged and
should not be treated as the operational catalogue.

## Design Rationale

A Bomach service is broader than a name, description, and price. The HTML design
shows service setup as a collection of related operating rules:

- subservices
- request form fields
- pricing calculators
- fulfillment workflows
- branch activation

Those areas are separate models instead of JSON blobs on `Service` because they
need their own lifecycle, ordering, validation, and future expansion. `Service`
holds the service identity and default metadata. The related models hold the
configurable operating parts.

This also protects existing commercial records. `Quote`, `ServiceLead`,
`ServiceOrder`, `Invoice`, and `Payment` already point at `services.Service`, so
the current implementation extends that model instead of replacing it.

## Core Service Model

`Service` remains the main service catalogue record.

Important fields:

- `code`: unique operational service code, such as `SUR-CAD`.
- `name`: human-readable service name.
- `category`: existing FK to `ServiceCategory`.
- `division`: operational grouping used by the Service OS UI.
- `description`: service summary.
- `base_price`: simple display or starting price, not the full pricing engine.
- `delivery_time`: existing duration text for backward compatibility.
- `status`: now supports `active`, `inactive`, `draft`, and `paused`.
- `owner_role`: FK to `user.Role`; ownership is role-based, not employee-based.
- `default_sla_days`: default SLA for the service.
- `fulfillment_mode`: high-level execution mode, such as quick order or project.
- `client_visibility`: whether the service is visible, internal, or hidden.

`Service` also has nullable links to active configuration versions:

- `active_request_form`
- `active_pricing_config`
- `active_workflow`

These fields make the current effective setup easy to fetch without losing the
version history in the related tables.

## Related Configuration Models

`ServiceSubService` stores child offerings under a service, such as "Perimeter
Survey" or "Plot Reservation". Subservices are modeled as records, not enums,
because they are expected to gain their own pricing, forms, SLAs, visibility, or
reporting later.

`ServiceRequestForm` is the versioned container for intake questions. Only one
form can be active per service. `ServiceRequestField` stores each field in that
form with its key, label, type, required flag, options, validation metadata,
placeholder, help text, and order.

`ServicePricingConfig` is the versioned calculator definition. It stores the
pricing type, formula, tax rate, deposit percent, discount approval threshold,
and active status. `ServicePricingField` stores the named calculator inputs used
by that pricing config.

`ServiceWorkflow` is the versioned fulfillment definition. Only one workflow can
be active per service. `ServiceWorkflowStage` stores ordered stages, role
ownership, SLA days, approval requirements, evidence requirements, and client
visibility.

`ServiceBranchActivation` links a service to a branch with status, client
visibility, capacity, and activation timestamp. This is a join model rather than
a plain many-to-many because branch availability needs operational metadata.

## Field Types

`ServiceFieldType` defines the shared field type registry used by request fields
and pricing fields:

- `text`
- `textarea`
- `number`
- `money`
- `date`
- `select`
- `multiselect`
- `checkbox`
- `file`
- `location`
- `email`
- `phone`

A later API endpoint should expose this registry so the frontend form builder
can render valid field choices from the backend instead of hardcoding them.

That endpoint is:

```http
GET /api/v1/services/request-field-types
```

## Endpoint Flow

The Service Catalogue API is incremental instead of one large wizard payload.
The frontend can still use a multi-page wizard by saving each page through the
endpoint for that configuration area.

Basic service page:

```http
POST /api/v1/services
GET /api/v1/services
GET /api/v1/services/{service_id}
PUT /api/v1/services/{service_id}
DELETE /api/v1/services/{service_id}
```

Catalogue display:

```http
GET /api/v1/services/catalogue
GET /api/v1/services/catalogue/{service_id}
```

Subservices page:

```http
GET /api/v1/services/{service_id}/subservices
PUT /api/v1/services/{service_id}/subservices
POST /api/v1/services/{service_id}/subservices
PUT /api/v1/services/{service_id}/subservices/{subservice_id}
DELETE /api/v1/services/{service_id}/subservices/{subservice_id}
```

Request form builder:

```http
GET /api/v1/services/{service_id}/request-forms
POST /api/v1/services/{service_id}/request-forms
GET /api/v1/services/{service_id}/request-forms/{form_id}
PUT /api/v1/services/{service_id}/request-forms/{form_id}
DELETE /api/v1/services/{service_id}/request-forms/{form_id}
POST /api/v1/services/{service_id}/request-forms/{form_id}/activate
```

Calculator library:

```http
GET /api/v1/services/pricing-configs
POST /api/v1/services/{service_id}/pricing-configs
GET /api/v1/services/{service_id}/pricing-configs/{config_id}
PUT /api/v1/services/{service_id}/pricing-configs/{config_id}
DELETE /api/v1/services/{service_id}/pricing-configs/{config_id}
POST /api/v1/services/{service_id}/pricing-configs/{config_id}/activate
```

Branch activation:

```http
GET /api/v1/services/{service_id}/branch-activations
PUT /api/v1/services/{service_id}/branch-activations
GET /api/v1/services/branch-activation-matrix
```

Workflow designer:

```http
GET /api/v1/services/{service_id}/workflows
POST /api/v1/services/{service_id}/workflows
GET /api/v1/services/{service_id}/workflows/{workflow_id}
PUT /api/v1/services/{service_id}/workflows/{workflow_id}
DELETE /api/v1/services/{service_id}/workflows/{workflow_id}
POST /api/v1/services/{service_id}/workflows/{workflow_id}/activate
GET /api/v1/services/{service_id}/workflows/{workflow_id}/stages
PUT /api/v1/services/{service_id}/workflows/{workflow_id}/stages
POST /api/v1/services/{service_id}/workflows/{workflow_id}/stages
PUT /api/v1/services/{service_id}/workflows/{workflow_id}/stages/{stage_id}
DELETE /api/v1/services/{service_id}/workflows/{workflow_id}/stages/{stage_id}
POST /api/v1/services/{service_id}/workflow-seed
GET /api/v1/services/{service_id}/workflow-summary
```

`workflow-seed` and `workflow-summary` exist for the service creation wizard.
The `/workflows` and `/stages` endpoints are the full Workflow Designer surface.

Final publish step:

```http
POST /api/v1/services/{service_id}/publish
```

Publishing activates the selected request form, pricing config, and workflow,
then sets the service status and client visibility. Publishing an active service
requires an active/request-ready form, pricing config, and at least one active
branch.

## Constraints

The model layer enforces the main catalogue rules:

- `Service.code` is unique when present.
- `ServiceSubService.code` is unique within one service.
- `ServiceRequestForm.version` is unique within one service.
- only one `ServiceRequestForm` can have `is_active=True` per service.
- `ServiceRequestField.key` is unique within one form.
- `ServicePricingConfig.version` is unique within one service.
- only one `ServicePricingConfig` can have `is_active=True` per service.
- `ServicePricingField.key` is unique within one pricing config.
- `ServiceWorkflow.version` is unique within one service.
- only one `ServiceWorkflow` can have `is_active=True` per service.
- `ServiceBranchActivation` is unique per service and branch.

These constraints are intentionally definition-level constraints. Request/order
execution records should later reference or snapshot the active definitions used
at the time they are created, so catalogue changes do not rewrite history.

## Current Implementation Files

- Models: `services/models/service.py`
- API schemas: `services/api/schema/service_catalogue_schemas.py`
- API router: `services/api/v1/services.py`
- Migration: `services/migrations/0024_service_client_visibility_service_code_and_more.py`
- Tests: `services/tests.py`, `ServiceCatalogueModelTests` and `ServiceCatalogueAPITests`
