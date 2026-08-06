# UI-1.01 — Service Administration Foundation

## Scope of this update

This is the first implementation update in Prototype-First Phase UI-1.

It replaces the five Service Administration placeholder pages with connected mock-backed workspaces:

- Service Catalogue;
- Calculator Library;
- Request Form Builder;
- Workflow Designer;
- Branch Activation.

The existing compact shell, authentication, permission guard, Query client, API client, error handling, toast system, and MSW infrastructure are reused.

## Prototype-first decisions

The Service Operations prototype remains the UI and product source of truth.

This update prioritizes:

- compact page toolbar;
- dense summary strip;
- restrained card padding;
- small operational type scale;
- service configuration relationships;
- lifecycle-ready service records;
- pricing calculator representation;
- request-form field representation;
- workflow-stage sequence;
- service/branch matrix;
- side-panel service profile;
- create-service dialog.

## Routes replaced

The existing route remains:

```text
/app/shell/$section
```

The following parameter values now render real Phase UI-1 pages:

```text
service-catalogue
calculator-library
request-form-builder
workflow-designer
branch-activation
```

Other sections continue to render the placeholder shell until their own phase begins.

## Frontend mock API

Base contract:

```text
GET /api/v1/ui-prototype/service-administration
```

Mutations:

```text
POST  /api/v1/ui-prototype/service-administration/services
PATCH /api/v1/ui-prototype/service-administration/configuration-status
PATCH /api/v1/ui-prototype/service-administration/branch-activation
```

These are **Frontend mock contracts**.

They do not claim to be existing production backend routes.

They are intentionally designed around the complete frontend product needed by the prototype.

## Data flow

```text
ServiceAdministrationSectionPage
    → TanStack Query
    → serviceAdministrationApi
    → shared apiClient
    → MSW handlers
    → mutable mock database
    → typed workspace response
```

Pages do not import seed arrays directly.

## Mutable behaviours implemented

### Create service

Creating a service:

- validates required fields in the MSW handler;
- creates a draft service;
- inserts it into the mock catalogue;
- invalidates the workspace Query;
- updates summary counts;
- displays success feedback.

### Configuration status

The mock status mutation supports:

- services;
- calculators;
- request forms;
- workflows.

The current visible actions use it for calculator activation, form activation/version transition, and workflow activation/version transition.

### Branch activation

Clicking a matrix cell cycles through:

```text
active
→ inactive
→ setup-required
→ active
```

The workspace and summary are updated through the mock API response.

## Safe TypeScript contracts

Types were added for:

- service catalogue items;
- calculator variables;
- calculator charges;
- pricing calculators;
- request form fields;
- request forms;
- workflow stages;
- workflows;
- branch activations;
- workspace summary;
- create-service input;
- status mutations.

## Backend status

| Capability                       | Current frontend route                               | Status                 | Production backend relationship                                              |
| -------------------------------- | ---------------------------------------------------- | ---------------------- | ---------------------------------------------------------------------------- |
| Combined service-admin workspace | `GET /ui-prototype/service-administration`           | Frontend mock contract | Backend has several separate service endpoints; reconciliation deferred      |
| Create service                   | `POST /ui-prototype/service-administration/services` | Frontend mock contract | Backend create-service route exists, but this UI contract is prototype-owned |
| Calculator library               | Combined workspace                                   | Frontend mock contract | Backend pricing structure does not yet prove full calculator-builder support |
| Request form builder             | Combined workspace                                   | Frontend mock contract | Backend request-form routes exist; detailed UI reconciliation deferred       |
| Workflow designer                | Combined workspace                                   | Frontend mock contract | Backend workflow routes exist; full stage UI contract remains frontend-owned |
| Branch activation matrix         | Combined workspace                                   | Frontend mock contract | Backend activation routes exist; matrix response shape not yet reconciled    |

## Reused project infrastructure

- `apiClient`;
- `ApiError`;
- centralized error presentation;
- TanStack Query;
- existing route guards;
- current permissions;
- current compact app shell;
- current navigation;
- existing toast provider;
- existing loading and page-error states;
- MSW browser and test setup;
- design tokens and Tailwind utilities.

## Current limitations

This first slice establishes complete registers and primary interactions, but some deeper prototype editors remain for the next UI-1 update:

- full calculator variable/formula editor;
- drag-and-drop request-form canvas;
- drag-and-drop workflow-stage editor;
- service subservice editor;
- bulk branch update confirmation;
- prototype screenshot comparison records;
- focused component interaction tests.

These are Phase UI-1 work, not backend-reconciliation work.

## Review checklist

Verify:

- all five sidebar items open real pages;
- layout remains compact;
- create service updates the catalogue;
- calculator status updates;
- request-form status updates;
- workflow status updates;
- branch cells update;
- browser refresh resets the in-memory mock seed;
- no page imports mock data directly;
- other product sections still show placeholders;
- mobile shell remains usable.
