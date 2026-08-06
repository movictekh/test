# Bomach Service Operations — Module Architecture and Naming Standard

## 1. Purpose

This document defines how the remaining Service Operations frontend should be divided into business modules.

The earlier Stage 4 “walking skeleton” proposal is superseded. “Walking skeleton” remains a delivery technique, not a permanent source-code module name.

Every production module must be named after a business capability or product area that users and developers can understand without knowing the implementation history.

## 2. Core rule

A module owns one coherent business capability.

A module should normally own its:

- routes;
- pages;
- domain components;
- API functions;
- Query keys and Query options;
- mutations;
- schemas;
- domain types;
- mock handlers;
- tests;
- module documentation.

Do not create permanent modules named after:

- roadmap stages;
- sprints;
- temporary experiments;
- technical implementation strategies;
- broad containers such as `misc`, `features`, or `walking-skeleton`.

## 3. Approved top-level modules

```text
src/modules/
├── auth/
├── dashboard/
├── service-catalogue/
├── service-requests/
├── quotations/
├── approvals/
├── billing/
├── service-orders/
├── execution-tasks/
├── deliverables/
├── client-portal/
├── real-estate/
├── documents/
├── notifications/
├── reports/
└── audit/
```

These names describe actual business capabilities.

## 4. Module ownership

### `dashboard`

Owns the operations command centre and summary views.

It may read data from several domains, but it does not own those domains.

### `service-catalogue`

Owns service definition and administration:

- service catalogue;
- service detail;
- sub-services;
- request forms;
- pricing configurations;
- workflows;
- workflow stages;
- branch activations;
- publication.

### `service-requests`

Owns demand capture and request management:

- staff request register;
- create request;
- request detail;
- request activity;
- request attachments;
- request ownership;
- request status and priority;
- request intake fields.

The user-facing detail workspace may be called “Request 360”, while the technical page should remain `RequestDetailPage`.

### `quotations`

Owns commercial quotation work:

- quotation register;
- quotation builder;
- line items and commercial values;
- quote detail;
- quote update;
- quote approval submission;
- quote lifecycle;
- client quote acceptance or rejection.

### `approvals`

Owns reusable approval infrastructure:

- approval flows;
- approval request queue;
- approval detail;
- approve;
- reject;
- cancel;
- comments and history where supported.

### `billing`

Owns invoices and payments:

```text
billing/
├── invoices/
└── payments/
```

It includes:

- invoice register;
- invoice detail;
- invoice creation;
- payment register;
- payment creation or confirmation;
- payment submissions;
- reconciliation status;
- client payment views.

### `service-orders`

Owns fulfilment orders:

- order register;
- order creation;
- order detail;
- order update;
- lifecycle status;
- commercial linkage;
- assignment;
- completion rules.

### `execution-tasks`

Owns tasks created from operational work:

- task register;
- task detail;
- assignment;
- progress;
- evidence;
- completion.

### `deliverables`

Owns client-facing and internal delivery outputs:

- deliverable register;
- versions;
- files;
- review;
- approval;
- client visibility.

The current backend specification does not expose a complete dedicated deliverables API. This module should not be implemented as a fake production module until the backend contract is agreed.

### `client-portal`

Owns client-facing composition:

- client dashboard;
- my requests;
- my quotations;
- quote acceptance or rejection;
- invoices and payment submissions;
- my orders;
- documents;
- profile.

It consumes client-scoped APIs and must never expose internal staff records.

### `real-estate`

Owns specialized estate and property workflows:

- estates;
- estate properties;
- standalone properties;
- inventory;
- reservations or sales when supported;
- estate invoices.

### `documents`

Owns shared document metadata and attachment experiences:

- document register;
- document detail;
- order documents;
- property documents;
- user documents.

Business modules may embed document components, but the generic document contract belongs here.

### `notifications`

Owns notification centre state, unread counts, links, and mark-as-read actions.

The backend specification must be checked for the final notification API before this module is considered fully connected.

### `reports`

Owns reports and analytics composition.

It may consume dashboard, operational, finance, and performance APIs, but should not duplicate their domain models unnecessarily.

### `audit`

Owns audit-log viewing and filtering.

It does not create audit events in the frontend. Backend actions create the authoritative audit history.

## 5. Nested module rule

Use a nested module only when a product area has strongly related but independently growing subdomains.

Approved example:

```text
src/modules/billing/
├── invoices/
└── payments/
```

Avoid unnecessary depth such as:

```text
src/modules/commercial-operations/service-management/request-processing/...
```

The default should remain one clear module per business capability.

## 6. Shared versus domain code

Place code in `src/shared` only when it has no business-specific meaning.

Shared examples:

- Button;
- Dialog;
- API client;
- error presentation;
- date formatting;
- currency formatting;
- generic DataTable;
- generic file uploader.

Domain examples:

- RequestStatusBadge;
- QuotationTotals;
- PaymentStatusSummary;
- OrderMilestoneTimeline;
- EstatePlotGrid.

## 7. Cross-module actions

One module may start an action owned by another module without taking ownership of it.

Example:

- Request detail may render `CreateQuotationDialog`;
- the dialog, schema, mutation, DTO, and Query invalidation rules belong to `quotations`;
- request detail only composes the quotation feature.

Similarly:

- a quotation may create an invoice;
- the invoice creation capability belongs to `billing/invoices`;
- quotation pages only invoke it.

## 8. Route naming

Approved route families:

```text
/app/dashboard

/app/services
/app/services/new
/app/services/$serviceId
/app/services/$serviceId/request-forms
/app/services/$serviceId/pricing
/app/services/$serviceId/workflows
/app/services/$serviceId/branches

/app/requests
/app/requests/new
/app/requests/$requestId

/app/quotations
/app/quotations/new
/app/quotations/$quoteId

/app/approvals
/app/approvals/$approvalId

/app/invoices
/app/invoices/$invoiceId
/app/payments
/app/payments/$paymentId

/app/orders
/app/orders/$orderId

/app/tasks
/app/tasks/$taskId

/app/documents
/app/reports
/app/audit

/portal/dashboard
/portal/requests
/portal/requests/new
/portal/requests/$requestId
/portal/quotations
/portal/quotations/$quoteId
/portal/payments
/portal/orders
/portal/documents
/portal/profile
```

## 9. Naming “Request 360”

“Request 360” is approved as a product label for the complete request workspace.

Use:

```text
Technical page: RequestDetailPage
Route: /app/requests/$requestId
UI eyebrow or section name: Request 360
```

Do not create a source folder called `request-360`.

## 10. Mock ownership

Each module owns its own mock handlers.

Example:

```text
src/modules/service-requests/
└── mocks/
    ├── service-requests.mock-data.ts
    └── service-requests.handlers.ts
```

The global MSW handler index only combines module handlers.

Mock data must follow the real API contract and must not invent fields that production pages rely on unless those fields are clearly marked as frontend-only view models.

## 11. Completion rule

A phase is complete only when its named business capability is usable within the agreed scope.

A module phase should include:

- list or entry page;
- detail page where required;
- create or update flows in scope;
- backend integration or contract-shaped MSW;
- loading, empty, error, unauthorized, forbidden, and success states;
- permissions;
- responsive design;
- tests;
- documentation;
- confirmed API mapping.

A phase should not be declared complete when it contains only placeholders for most of the named module.
