# Bomach Service Operations — Revised Product Implementation Phases

## 1. Why the roadmap was revised

The previous roadmap used a “walking skeleton” phase that combined service requests, quotations, and service orders in one temporary module.

That approach is useful for proving architecture, but it is not the correct long-term product structure.

The revised roadmap follows these rules:

1. each phase delivers one coherent product capability;
2. each phase creates or completes a correctly named business module;
3. cross-module work is composed through explicit module APIs;
4. backend endpoints are mapped before implementation;
5. mocks are owned by the same module that owns the real API integration;
6. a phase is not complete until its agreed feature scope works end to end.

Stages 1–3 remain complete and are not renumbered.

---

# Completed Stage 1 — Repository and Engineering Foundation

Status: **Complete**

Delivered:

- application structure;
- strict TypeScript;
- TanStack Router;
- TanStack Query;
- TanStack Form;
- API client;
- environment configuration;
- MSW;
- tests;
- Storybook;
- quality commands;
- engineering standards.

---

# Completed Stage 2 — Design System and Application Shell

Status: **Complete**

Delivered:

- shared UI components;
- application shell;
- client portal shell;
- overlays;
- state components;
- toast system;
- responsive navigation;
- Storybook component catalogue;
- prototype-aligned visual language.

---

# Completed Stage 3 — Authentication, User Context, Permissions, and Error Presentation

Status: **Complete**

Delivered:

- login;
- 2FA;
- JWT handling;
- refresh;
- logout;
- current user;
- staff and client detection;
- permissions;
- protected routes;
- session expiry;
- safe redirects;
- centralized user-facing error presentation.

Temporary security decision:

- access token in sessionStorage;
- refresh token in localStorage.

Production target:

- access token in memory;
- refresh token in a Secure HttpOnly cookie.

---

# Phase 4 — Operations Dashboard

## Product goal

Implement the internal Command Center as a real dashboard module.

The dashboard should help an operations user answer:

- what requires attention now;
- what is overdue;
- what is awaiting approval;
- which requests or orders are at risk;
- what recent operational activity occurred.

## Module

```text
src/modules/dashboard/
```

## Backend APIs

Primary:

- `GET /api/v1/dashboard/summary`
- `GET /api/v1/dashboard/performance-card`
- `GET /api/v1/dashboard/overview`
- `GET /api/v1/dashboard/stats`
- `GET /api/v1/sop/dashboard/summary/{user_id}`
- `GET /api/v1/sop/dashboard/recent-activity`

The exact combination must be confirmed from response schemas before implementation. Avoid calling all summary endpoints unless each has a distinct responsibility.

## Features

- operational KPI cards;
- attention queue;
- recent activity;
- role-aware summary;
- loading and partial-error states;
- links into the owning modules;
- responsive prototype-aligned command-center layout.

## Exit criteria

A staff user sees a useful role-aware operational overview backed by dashboard APIs or contract-shaped mocks.

---

# Phase 5 — Service Catalogue and Configuration

## Product goal

Allow authorized staff to define and publish a usable Bomach service.

## Module

```text
src/modules/service-catalogue/
```

## Backend APIs

### Catalogue and services

- `GET /api/v1/services/request-field-types`
- `GET /api/v1/services/catalogue`
- `GET /api/v1/services/catalogue/{service_id}`
- `GET /api/v1/services`
- `POST /api/v1/services`
- `GET /api/v1/services/{service_id}`
- `PUT /api/v1/services/{service_id}`
- `DELETE /api/v1/services/{service_id}`
- `POST /api/v1/services/{service_id}/publish`

### Sub-services

- `GET /api/v1/services/{service_id}/subservices`
- `POST /api/v1/services/{service_id}/subservices`
- `PUT /api/v1/services/{service_id}/subservices`
- `PUT /api/v1/services/{service_id}/subservices/{subservice_id}`
- `DELETE /api/v1/services/{service_id}/subservices/{subservice_id}`

### Request forms

- `GET /api/v1/services/{service_id}/request-forms`
- `POST /api/v1/services/{service_id}/request-forms`
- `GET /api/v1/services/{service_id}/request-forms/{form_id}`
- `PUT /api/v1/services/{service_id}/request-forms/{form_id}`
- `DELETE /api/v1/services/{service_id}/request-forms/{form_id}`
- `POST /api/v1/services/{service_id}/request-forms/{form_id}/activate`

### Pricing

- `GET /api/v1/services/pricing-configs`
- `POST /api/v1/services/{service_id}/pricing-configs`
- `GET /api/v1/services/{service_id}/pricing-configs/{config_id}`
- `PUT /api/v1/services/{service_id}/pricing-configs/{config_id}`
- `DELETE /api/v1/services/{service_id}/pricing-configs/{config_id}`
- `POST /api/v1/services/{service_id}/pricing-configs/{config_id}/activate`

### Workflows

- `GET /api/v1/services/{service_id}/workflows`
- `POST /api/v1/services/{service_id}/workflows`
- `GET /api/v1/services/{service_id}/workflows/{workflow_id}`
- `PUT /api/v1/services/{service_id}/workflows/{workflow_id}`
- `DELETE /api/v1/services/{service_id}/workflows/{workflow_id}`
- `GET /api/v1/services/{service_id}/workflows/{workflow_id}/stages`
- `POST /api/v1/services/{service_id}/workflows/{workflow_id}/stages`
- `PUT /api/v1/services/{service_id}/workflows/{workflow_id}/stages`
- `PUT /api/v1/services/{service_id}/workflows/{workflow_id}/stages/{stage_id}`
- `DELETE /api/v1/services/{service_id}/workflows/{workflow_id}/stages/{stage_id}`
- `POST /api/v1/services/{service_id}/workflow-seed`
- `GET /api/v1/services/{service_id}/workflow-summary`
- `POST /api/v1/services/{service_id}/workflows/{workflow_id}/activate`

### Branch activation

- `GET /api/v1/services/branch-activation-matrix`
- `GET /api/v1/services/{service_id}/branch-activations`
- `PUT /api/v1/services/{service_id}/branch-activations`
- `GET /api/v1/branch/branches`
- `GET /api/v1/branch/branches/choices/fields`

## Features

- service register;
- service detail;
- create and edit service;
- sub-service management;
- request-form builder;
- pricing configuration;
- workflow designer;
- branch activation;
- publish validation.

## Exit criteria

An authorized administrator can configure and publish a service without changing frontend source code for each new service.

---

# Phase 6 — Service Request Operations

## Product goal

Implement the complete staff request-management capability.

## Module

```text
src/modules/service-requests/
```

## Backend APIs

### Reference and intake

- `GET /api/v1/service-requests/choices`
- `GET /api/v1/service-requests/services/{service_id}/intake-form`
- `GET /api/v1/services/catalogue`
- `GET /api/v1/clients/admin/clients`
- `GET /api/v1/clients/admin/clients/{client_id}`
- `GET /api/v1/branch/branches`

### Staff requests

- `GET /api/v1/service-requests/admin`
- `POST /api/v1/service-requests/admin`
- `GET /api/v1/service-requests/admin/{request_id}`
- `PATCH /api/v1/service-requests/admin/{request_id}`
- `POST /api/v1/service-requests/admin/{request_id}/activities`
- `POST /api/v1/service-requests/admin/{request_id}/attachments`

Do not implement quotation creation inside this module. Request detail may provide an entry point into the quotation module.

## Features

- request register;
- server-side filters and pagination;
- create request;
- dynamic intake form from active service form;
- request detail / Request 360;
- status, priority, owner, due date, and next action;
- activity journal;
- attachments;
- client and service summary;
- permission-aware actions.

## Exit criteria

Staff can capture, find, review, update, and document a service request through a complete request lifecycle up to the point where commercial quotation work begins.

---

# Phase 7 — Quotations

## Product goal

Implement quotation preparation and client decision handling as its own commercial module.

## Module

```text
src/modules/quotations/
```

## Backend APIs

### Staff quotations

- `GET /api/v1/quotes`
- `POST /api/v1/quotes`
- `GET /api/v1/quotes/{quote_id}`
- `PATCH /api/v1/quotes/{quote_id}`
- `PUT /api/v1/quotes/{quote_id}`
- `DELETE /api/v1/quotes/{quote_id}`
- `POST /api/v1/quotes/{quote_id}/approve`

### Request linkage

- `POST /api/v1/service-requests/admin/{request_id}/quote`

### Client quotation decisions

- `GET /api/v1/service-requests/quotes`
- `GET /api/v1/service-requests/quotes/{quote_id}`
- `POST /api/v1/service-requests/quotes/{quote_id}/accept`
- `POST /api/v1/service-requests/quotes/{quote_id}/reject`

## Features

- quotation register;
- create quotation;
- quotation builder;
- scope, description, fees, discounts, taxes, deposit, validity, and terms;
- request linkage;
- quotation detail;
- update;
- approval state;
- client-visible representation;
- client accept or reject flow.

## Exit criteria

An authorized staff user can prepare and manage a quotation, and the client can review and decide on it through the client-scoped flow.

---

# Phase 8 — Approval Management

## Product goal

Implement reusable approval configuration and decision queues.

## Module

```text
src/modules/approvals/
```

## Backend APIs

- `GET /api/v1/approvals/flows/choices`
- `GET /api/v1/approvals/flows`
- `POST /api/v1/approvals/flows`
- `GET /api/v1/approvals/flows/{flow_id}`
- `PUT /api/v1/approvals/flows/{flow_id}`
- `DELETE /api/v1/approvals/flows/{flow_id}`
- `GET /api/v1/approvals/requests`
- `POST /api/v1/approvals/requests`
- `GET /api/v1/approvals/requests/{request_id}`
- `DELETE /api/v1/approvals/requests/{request_id}`
- `POST /api/v1/approvals/requests/{request_id}/approve`
- `POST /api/v1/approvals/requests/{request_id}/reject`

## Features

- approval-flow register;
- flow configuration;
- approval queue;
- approval detail;
- approve;
- reject;
- cancel;
- linked record context;
- permission checks;
- non-optimistic sensitive mutations.

## Exit criteria

Approval-requiring modules can create approval requests and authorized users can make traceable decisions.

---

# Phase 9 — Billing: Invoices and Payments

## Product goal

Implement the financial record flow after commercial acceptance.

## Module

```text
src/modules/billing/
├── invoices/
└── payments/
```

## Backend APIs

### Invoices

- `GET /api/v1/invoices`
- `POST /api/v1/invoices`
- `GET /api/v1/invoices/{invoice_id}`
- `PUT /api/v1/invoices/{invoice_id}`
- `DELETE /api/v1/invoices/{invoice_id}`

### Payments

- `GET /api/v1/payments`
- `POST /api/v1/payments`
- `GET /api/v1/payments/{payment_id}`
- `DELETE /api/v1/payments/{payment_id}`

### Client payment submissions

- `GET /api/v1/service-requests/payments/`
- `POST /api/v1/service-requests/payments/submit`
- `GET /api/v1/service-requests/payments/{invoice_id}`
- `GET /api/v1/service-requests/admin/payment-submissions`
- `POST /api/v1/service-requests/admin/payment-submissions/{submission_id}/review`

## Features

- invoice register and detail;
- invoice creation;
- payment register and detail;
- payment submission;
- staff review;
- status and reconciliation;
- client invoice and payment views;
- backend-confirmed success;
- no optimistic payment confirmation.

## Exit criteria

Accepted commercial work can be invoiced, client payment evidence can be submitted, and authorized staff can review and record payment outcomes.

---

# Phase 10 — Service Orders

## Product goal

Implement fulfilment-order management after commercial and payment eligibility.

## Module

```text
src/modules/service-orders/
```

## Backend APIs

- `GET /api/v1/orders`
- `POST /api/v1/orders`
- `GET /api/v1/orders/{order_id}`
- `PUT /api/v1/orders/{order_id}`
- `DELETE /api/v1/orders/{order_id}`

Supporting:

- quotation detail;
- invoice and payment state;
- service workflow summary;
- client detail;
- documents by order.

## Features

- order register;
- create order from eligible commercial work;
- order detail;
- assignment;
- status updates;
- linked request, quotation, invoice, and payment;
- payment eligibility explanation;
- order documents.

## Exit criteria

An eligible accepted service can become an operational service order with traceable commercial links.

---

# Phase 11 — Execution Tasks and Operational Work

## Product goal

Implement work assignment and execution tracking.

## Modules

```text
src/modules/execution-tasks/
src/modules/projects/
```

Create `projects` only where the service-order model actually requires a project record.

## Backend APIs

### Tasks

- `GET /api/v1/tasks`
- `POST /api/v1/tasks`
- `GET /api/v1/tasks/{task_id}`
- `PUT /api/v1/tasks/{task_id}`
- `DELETE /api/v1/tasks/{task_id}`

### Projects

- `GET /api/v1/projects`
- `POST /api/v1/projects`
- `GET /api/v1/projects/{project_id}`
- `PUT /api/v1/projects/{project_id}`
- `DELETE /api/v1/projects/{project_id}`
- `GET /api/v1/projects/stats/`
- `GET /api/v1/projects/{project_id}/employees`

### Work reports

- `GET /api/v1/work-reports/`
- `POST /api/v1/work-reports/`
- `GET /api/v1/work-reports/{report_id}`
- `PUT /api/v1/work-reports/{report_id}`
- `DELETE /api/v1/work-reports/{report_id}`
- `POST /api/v1/work-reports/{report_id}/approve`
- `POST /api/v1/work-reports/{report_id}/reject`

## Features

- task register;
- task detail;
- assignment;
- progress;
- work report;
- work-report approval;
- order or project linkage.

## Exit criteria

Operational work can be assigned, updated, reported, and reviewed.

---

# Phase 12 — Deliverables and Completion

## Product goal

Implement controlled delivery outputs and completion rules.

## Module

```text
src/modules/deliverables/
```

## Backend status

The uploaded OpenAPI document does not provide a complete dedicated deliverables contract.

Before implementation, define:

- deliverable list;
- deliverable detail;
- file upload;
- versions;
- internal review;
- client visibility;
- client acceptance;
- rejection or revision;
- completion eligibility.

Documents APIs may support file metadata, but they are not a substitute for a deliverable lifecycle.

## Exit criteria

This phase begins only after the backend contract is approved. It is complete when deliverables can move through review and client acceptance with order-completion rules.

---

# Phase 13 — Client Portal Product

## Product goal

Complete the client-facing product as a coherent portal rather than scattered staff-page variants.

## Module

```text
src/modules/client-portal/
```

## Backend APIs

### Requests

- `GET /api/v1/service-requests/summary`
- `GET /api/v1/service-requests/`
- `POST /api/v1/service-requests/`
- `GET /api/v1/service-requests/{request_id}`
- `POST /api/v1/service-requests/{request_id}/activities`
- `POST /api/v1/service-requests/{request_id}/attachments`
- `GET /api/v1/service-requests/services/{service_id}/intake-form`

### Quotations

- `GET /api/v1/service-requests/quotes`
- `GET /api/v1/service-requests/quotes/{quote_id}`
- `POST /api/v1/service-requests/quotes/{quote_id}/accept`
- `POST /api/v1/service-requests/quotes/{quote_id}/reject`

### Payments

- `GET /api/v1/service-requests/payments/`
- `POST /api/v1/service-requests/payments/submit`
- `GET /api/v1/service-requests/payments/{invoice_id}`

### Profile

- `GET /api/v1/clients/clients/profile`
- `PATCH /api/v1/clients/clients/profile/personal`
- `PATCH /api/v1/clients/clients/profile/company`

### Documents and orders

- client-scoped order endpoint must be confirmed;
- document access must be confirmed as client-scoped before use.

## Features

- portal dashboard;
- request creation and tracking;
- quote review and decision;
- invoice and payment submission;
- order progress where backend scoping exists;
- documents;
- profile management.

## Exit criteria

A client can complete their approved self-service journey without seeing internal staff data.

---

# Phase 14 — Real Estate Operations

## Product goal

Implement the specialized estate and property product separately from generic service operations.

## Module

```text
src/modules/real-estate/
```

## Backend APIs

### Estates and estate properties

- `GET /api/v1/estates/choices/fields`
- `GET /api/v1/estates/`
- `POST /api/v1/estates/`
- `GET /api/v1/estates/{estate_id}`
- `PUT /api/v1/estates/{estate_id}`
- `DELETE /api/v1/estates/{estate_id}`
- `GET /api/v1/estates/{estate_id}/properties/choices/fields`
- `GET /api/v1/estates/{estate_id}/properties`
- `POST /api/v1/estates/{estate_id}/properties`
- `GET /api/v1/estates/{estate_id}/properties/{property_id}`
- `PUT /api/v1/estates/{estate_id}/properties/{property_id}`
- `DELETE /api/v1/estates/{estate_id}/properties/{property_id}`

### Standalone properties

- `GET /api/v1/estates/properties/all`
- `POST /api/v1/estates/properties/all`
- `GET /api/v1/estates/properties/all/{property_id}`
- `PUT /api/v1/estates/properties/all/{property_id}`
- `DELETE /api/v1/estates/properties/all/{property_id}`

### Generic property records

- `GET /api/v1/properties/stats`
- `GET /api/v1/properties`
- `POST /api/v1/properties`
- `GET /api/v1/properties/{property_id}`
- `PUT /api/v1/properties/{property_id}`
- `DELETE /api/v1/properties/{property_id}`
- `GET /api/v1/properties/client/{client_id}/properties`

The apparent overlap between `/estates/.../properties` and `/properties` must be clarified before implementation.

## Exit criteria

Estate and property workflows are implemented with one agreed canonical property model and no duplicate frontend concepts.

---

# Phase 15 — Documents, Notifications, Reports, and Audit

This final platform phase should be split internally into independently reviewable modules.

## Documents

Module:

```text
src/modules/documents/
```

APIs:

- `GET /api/v1/documents`
- `POST /api/v1/documents`
- `GET /api/v1/documents/{document_id}`
- `PUT /api/v1/documents/{document_id}`
- `DELETE /api/v1/documents/{document_id}`
- `GET /api/v1/documents/user/{user_id}/documents`
- `GET /api/v1/documents/order/{order_id}/documents`
- `GET /api/v1/documents/property/{property_id}/documents`

## Audit

Module:

```text
src/modules/audit/
```

API:

- `GET /api/v1/audit-logs/`

## Reports

Module:

```text
src/modules/reports/
```

Use only approved report, dashboard, and export endpoints. Do not combine unrelated legal, HR, marketing, or revenue reports into Service Operations without product approval.

## Notifications

Module:

```text
src/modules/notifications/
```

The uploaded OpenAPI must be checked for a final notification contract. The current UI notification drawer remains a presentation foundation until the backend contract is confirmed.

---

# API contract gaps requiring backend discussion

The following gaps should be resolved before their phases begin:

1. dedicated deliverables lifecycle;
2. service-order-specific workflow stages and milestones;
3. order completion endpoint and transactional completion rules;
4. client-scoped order endpoint;
5. notification centre endpoints;
6. canonical property model between Estates and Properties APIs;
7. file-upload transport and secure download contract;
8. quotation version-history contract;
9. invoice generation directly from accepted quotation;
10. payment reversal and reconciliation rules;
11. request assessment APIs;
12. audit-event coverage for Service Operations actions.

---

# Phase implementation standard

Before coding any phase:

1. inspect the latest repository;
2. inspect the relevant OpenAPI schemas and endpoints;
3. document exact frontend DTOs;
4. identify missing backend contracts;
5. create the named module;
6. add module-owned MSW handlers;
7. implement list, detail, create, and update flows in scope;
8. add loading, empty, error, forbidden, and success states;
9. add permissions;
10. add component and integration tests;
11. run formatting, checks, production build, and Storybook build;
12. document the phase.

Do not begin a later phase by placing temporary production code into the previous module.
