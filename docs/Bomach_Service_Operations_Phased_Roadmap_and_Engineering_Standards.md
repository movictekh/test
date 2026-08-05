# Bomach Service Operations Module

## Phased Product Roadmap, Frontend Architecture, Delivery Plan, and Engineering Standards

**Document status:** Planning baseline  
**Planning date:** 5 August 2026  
**Primary frontend workspace:** `bomach_os_frontend-services/`  
**Product reference:** `docs/Bomach_Service_Operations_OS_v1(1).html`

---

# 1. Purpose of This Document

I am using this document as the main implementation guide for the Bomach Service Operations frontend.

The prototype has already helped me understand what the Service Operations Module is expected to do. The next step is to turn that understanding into a clear engineering plan so that I do not start writing pages without knowing how the full system should be arranged.

This document explains:

- what I am building;
- why the system is needed;
- how the frontend will be structured;
- how the frontend will connect to the backend;
- which tools and libraries I will use;
- how TanStack will be used across the application;
- how the work will be divided into phases and sprints;
- what each phase must deliver;
- the coding, testing, security, accessibility, and review standards I will follow;
- how I will know when a feature or phase is complete;
- how the prototype will be converted into a production application without copying its technical weaknesses.

The goal is to build the module deliberately. Each phase should create a stable base for the next phase. I do not want a codebase where every page is built differently, every developer makes a new pattern, and important business rules are hidden inside random components.

---

# 2. Executive Summary

The Bomach Service Operations Module will manage the complete life cycle of every service Bomach offers.

The main business journey is:

```text
Service Configuration
        ↓
Service Request
        ↓
Review or Assessment
        ↓
Quotation
        ↓
Internal Approval
        ↓
Client Acceptance
        ↓
Invoice
        ↓
Payment Confirmation
        ↓
Service Order
        ↓
Milestones and Tasks
        ↓
Deliverables and Quality Review
        ↓
Client Acceptance
        ↓
Completion
        ↓
Feedback, Reporting, and Audit
```

The system will bring four areas together:

1. **Commercial operations** — requests, assessments, quotations, approvals, invoices, and payments.
2. **Operational delivery** — service orders, milestones, tasks, deliverables, and quality control.
3. **Client experience** — progress, documents, payments, approvals, and feedback.
4. **Governance and intelligence** — permissions, reports, alerts, audit history, and management visibility.

The current HTML prototype is the product and design reference. It is not the production codebase. The production frontend will be built as a modular React and TypeScript application inside `bomach_os_frontend-services/`.

The frontend will lean heavily on the TanStack ecosystem:

- **TanStack Router** for routes, layouts, URL state, route validation, and route-level access checks;
- **TanStack Query** for backend data, caching, synchronization, mutations, and invalidation;
- **TanStack Form** for forms, complex forms, and multi-step wizards;
- **TanStack Table** for registers, sorting, filtering, selection, and pagination;
- **TanStack Virtual** where large lists or grids need virtualization;
- **TanStack Pacer** for selected cases such as debounced search, throttled events, queues, and batching;
- **TanStack Store** only for small application-wide interface state that does not belong to Router, Query, or Form.

The work will begin with architecture, standards, the design system, routing, authentication, and a thin end-to-end service journey. Full modules will be added only after the foundation has been tested.

---

# 3. What I Am Building

I am building a service operating system for Bomach Group.

It is not only a dashboard and it is not only a collection of forms. It is a connected business application where each record leads into the next part of the service journey.

For example:

```text
A configured service
        ↓
creates the rules for a request
        ↓
which produces a quotation
        ↓
which may require approval
        ↓
which produces an invoice
        ↓
which receives payment
        ↓
which becomes a service order
        ↓
which is delivered through tasks, stages, and documents
        ↓
which is accepted and reviewed by the client
```

The system must support both shared business processes and division-specific processes.

The shared records are:

- services;
- requests;
- assessments;
- quotations;
- approvals;
- invoices;
- payments;
- service orders;
- milestones;
- tasks;
- deliverables;
- feedback;
- notifications;
- audit events.

Specialized areas can then add their own behaviour. Examples include:

- estate and plot inventory for Real Estate;
- field work and survey plans for Land Surveying;
- site inspections and project stages for Engineering;
- pickup, transit, delivery, and proof of delivery for Logistics;
- discovery, design, development, testing, and deployment for Information Technology.

The shared system should not be copied separately for every division. Specialized modules should extend the common service process.

---

# 4. Product Vision

The long-term vision is to create one trusted place where Bomach can answer the following questions:

- What services do we currently offer?
- In which branches is each service available?
- How is each service priced?
- What information must a client provide?
- What stage should the service follow?
- Who owns a request?
- What has been communicated to the client?
- What was quoted and who approved it?
- What has the client paid?
- What work is active?
- What task should happen next?
- What document or evidence has been produced?
- Is the work late, blocked, or waiting for the client?
- What does the client still need to approve?
- How satisfied was the client?
- Which branch, service, or team is performing well?
- Who carried out an important action?

The system should reduce the use of disconnected spreadsheets, informal approvals, lost WhatsApp conversations, hidden work, duplicated records, and unclear ownership.

---

# 5. Source of Truth and Planning Assumptions

## 5.1 Product source of truth

The HTML prototype is currently the main visual and functional reference.

It shows:

- the business areas;
- the navigation groups;
- the roles;
- the page layouts;
- the sample records;
- the lifecycle stages;
- the service creation flow;
- the forms and modal actions;
- the expected dashboards and registers;
- the design direction.

When the prototype and a later approved product requirement disagree, the approved product requirement should replace the prototype.

## 5.2 Engineering source of truth

The production source code will live in the React and TypeScript frontend project.

The prototype must not be copied into one large React component. Its responsibilities must be separated into:

- routes;
- layouts;
- business modules;
- API functions;
- Query definitions;
- forms;
- tables;
- reusable user-interface components;
- validation schemas;
- domain types;
- tests.

## 5.3 Backend assumption

This roadmap assumes that the frontend will communicate with a backend API.

The frontend must not become the final authority for:

- authentication;
- authorization;
- payments;
- approval decisions;
- price calculation where security matters;
- status transitions;
- audit integrity;
- file permissions;
- data consistency;
- concurrency control.

The backend must validate every important business action even when the frontend has already validated it.

---

# 6. Scope of the First Production Release

## 6.1 In scope

The first complete production release should include:

- login and secure session handling;
- role and permission-based access;
- application shell and navigation;
- service catalogue;
- service configuration;
- service calculator configuration;
- service request form configuration;
- workflow configuration;
- branch activation;
- service request capture and management;
- request activity and communication history;
- assessments;
- quotations and quotation versions;
- approval queues;
- invoices and payment records;
- service order creation and management;
- milestones;
- execution tasks;
- deliverables and files;
- quality review;
- client approvals;
- client portal;
- feedback and complaints;
- notifications;
- reports;
- audit history;
- responsive desktop, tablet, and mobile behaviour;
- automated tests;
- CI/CD and production deployment controls.

## 6.2 Not required in the earliest phases

The following should not delay the first useful release unless they are confirmed as immediate business requirements:

- full offline-first support;
- complex real-time collaboration;
- advanced predictive analytics;
- artificial intelligence recommendations;
- a public search-engine-optimized service marketplace;
- deep accounting-ledger functionality;
- a full customer relationship management system outside service operations;
- a native mobile application;
- TanStack DB adoption;
- migration to TanStack Start.

These may be added later after the core service life cycle is stable.

---

# 7. Main Engineering Principles

## 7.1 Build by business domain

Files should be grouped around business features, not placed in one large global `components`, `hooks`, or `services` folder.

A developer working on quotations should be able to find the quotation pages, Query logic, forms, schemas, types, and components inside the quotation module.

## 7.2 One clear owner for each type of state

The application should not store the same data in several places.

The ownership rule will be:

```text
Route and URL state        → TanStack Router
Backend and server state   → TanStack Query
Form and wizard state      → TanStack Form
Table behaviour            → TanStack Table
Large rendering workloads  → TanStack Virtual
Execution timing           → TanStack Pacer
Small global UI state      → TanStack Store or React Context
Temporary component state  → React state
```

## 7.3 The backend remains the authority

The frontend can hide buttons, validate forms, and guide the user, but it cannot guarantee security by itself.

Every important action must still be checked by the backend.

## 7.4 Reuse without over-abstraction

Repeated interface patterns should become shared components.

Business-specific behaviour should remain inside its module.

I should not create a general component only because two pieces of JSX look slightly similar. Reuse should make the system easier to understand, not more complicated.

## 7.5 Deliver working vertical slices

I should avoid building every empty screen before connecting any full workflow.

A vertical slice means completing one small journey through the whole system, for example:

```text
Login
  ↓
View requests
  ↓
Create request
  ↓
Open request details
  ↓
Prepare quotation
  ↓
Create service order
```

This proves the architecture early.

## 7.6 Quality is part of the work

Loading states, empty states, error states, accessibility, tests, and documentation are not final decorations. They must be included while each feature is being built.

---

# 8. Current Frontend Starting Point

The current frontend project already has a basic Vite setup with React, TypeScript, Tailwind CSS, TanStack Query, Query Devtools, and ESLint.

It is still close to the default Vite starter application. This is useful because the production structure can be introduced before a large amount of feature code exists.

The initial engineering work should therefore focus on:

1. removing the starter demonstration interface;
2. adding the agreed directory structure;
3. configuring TanStack Router;
4. configuring the Query client;
5. creating the shared design tokens;
6. setting up linting, formatting, tests, mocks, and CI;
7. creating the application shell;
8. documenting the standards before multiple feature patterns appear.

---

# 9. Technology Stack

## 9.1 Core application stack

### React

React will be used to build the application interface from reusable components.

It will handle:

- page composition;
- interface state;
- reusable controls;
- dialogs and drawers;
- dashboards;
- lists and cards;
- user interaction.

### TypeScript

TypeScript will be used across all production frontend code.

It will help make the following safer:

- API data;
- route parameters;
- search filters;
- form values;
- domain statuses;
- component properties;
- Query keys;
- mutation responses.

### Vite

Vite will remain the frontend build and development tool.

It will provide:

- the local development server;
- fast development updates;
- production builds;
- plugin integration;
- environment variable handling.

### Tailwind CSS

Tailwind CSS will be used to implement the design system and responsive layouts.

It should not be used as an excuse for random one-off styling. Shared components and semantic tokens will still define the approved design language.

---

# 10. TanStack Responsibility Map

## 10.1 TanStack Router

TanStack Router will own application routing and URL state.

It will be used for:

- file-based routes;
- nested layouts;
- route parameters;
- typed navigation;
- validated search parameters;
- route-level access checks;
- route loaders;
- route preloading;
- route error boundaries;
- not-found pages;
- page-level code splitting;
- navigation blocking for unsaved work.

Examples of state that belongs in the URL include:

- page number;
- page size;
- search value;
- selected status;
- selected branch;
- selected division;
- selected owner;
- sort column;
- sort direction;
- date range;
- selected tab where it should be shareable;
- board or table view mode.

A user should be able to copy a filtered request-register URL and open the same view later.

## 10.2 TanStack Query

TanStack Query will own all server state.

It will be used for:

- loading services;
- loading requests;
- loading quotations;
- loading invoices and payments;
- loading service orders;
- loading tasks and deliverables;
- loading reports and audit events;
- caching results;
- background refetching;
- query cancellation;
- pagination;
- mutations;
- cache invalidation;
- selected optimistic updates;
- handling stale data;
- retry policies;
- development inspection through Query Devtools.

The Query cache must not be copied into a second global store.

## 10.3 TanStack Form

TanStack Form will own form state.

It will be used for:

- login;
- create service;
- configure service;
- service calculator configuration;
- dynamic request form configuration;
- workflow configuration;
- create service request;
- request assessment;
- quotation builder;
- invoice creation;
- payment confirmation;
- service order controls;
- task creation;
- deliverable upload;
- client approval;
- feedback;
- reports filters where a normal form is more suitable than direct URL controls.

I will create shared form hooks and shared field components so that forms are consistent and not unnecessarily verbose.

## 10.4 TanStack Table

TanStack Table will provide table behaviour without controlling the visual design.

It will be used for:

- service registers;
- calculator registers;
- branch activation matrices;
- request registers;
- quotation registers;
- invoice registers;
- approval queues;
- tasks;
- deliverables;
- property listings;
- feedback;
- reports;
- audit logs.

For backend-controlled lists, sorting, filtering, and pagination will be handled on the server. Table state will be synchronized with Router search parameters.

## 10.5 TanStack Virtual

TanStack Virtual will be added only where the amount of rendered content justifies it.

Possible uses include:

- a very large audit log;
- long activity histories;
- large notification lists;
- large estate plot inventories;
- long task boards;
- large document libraries.

Small lists should remain normal lists. Virtualization should solve a measured problem, not be added automatically.

## 10.6 TanStack Pacer

TanStack Pacer will be used carefully because its API may still change.

Suitable uses include:

- debounced global search;
- debounced register filters;
- debounced async field validation;
- throttled resize or scroll behaviour;
- queued file uploads;
- batched analytics or non-critical client events;
- controlled background operations.

Pacer is a frontend execution-control tool. It is not a replacement for backend rate limits, background workers, or durable queues.

## 10.7 TanStack Store

TanStack Store may be used only for small cross-application interface state such as:

- whether the sidebar is collapsed;
- active branch context;
- table density preference;
- command palette state;
- selected user interface preferences;
- feature flags already supplied by the backend.

The following must not be placed in it:

- server records;
- form values;
- shareable filters;
- Query cache data;
- route parameters.

## 10.8 TanStack Devtools

Development tools will be enabled only in development builds.

They will help inspect:

- Query caches;
- Query mutations;
- route matches;
- route parameters;
- search parameters;
- pending navigation.

## 10.9 TanStack DB

TanStack DB will be deferred.

It may become useful later for:

- real-time task boards;
- normalized client-side collections;
- offline field work;
- reactive cross-record views;
- instant optimistic updates across several collections.

It should not be added before the normal backend API, Query patterns, and data contracts are stable.

## 10.10 TanStack Start

The project will remain a Vite single-page application for now.

TanStack Start should be considered only if the product later needs:

- server rendering;
- server functions;
- streaming;
- public search-engine-visible service pages;
- a frontend backend-for-frontend layer.

---

# 11. Supporting Libraries and Tools

## 11.1 Validation

A schema validation library such as Zod will be used for:

- form validation;
- Router search-parameter validation;
- runtime validation at uncertain external boundaries;
- shared frontend contracts where appropriate.

## 11.2 Icons

The React version of Tabler Icons should be used so that the production application keeps the visual direction of the prototype without depending on an icon webfont.

## 11.3 Class composition

Utilities such as `clsx`, `tailwind-merge`, and `class-variance-authority` may be used to create predictable component variants.

## 11.4 Dates

A focused date utility such as `date-fns` may be used for formatting and date calculations.

All server dates should use an agreed format, normally ISO 8601, and be converted for display at the edge of the interface.

## 11.5 API type generation

Where the backend publishes an OpenAPI schema, generated TypeScript API types should be considered.

Generated files must be placed in a clearly marked generated directory and must never be edited manually.

## 11.6 Mock Service Worker

Mock Service Worker will be used to simulate backend APIs during early frontend work and automated tests.

The interface should call normal API functions. Mock Service Worker should intercept those requests in development and tests.

The page should not know whether the response comes from a mock server or the real backend.

## 11.7 Testing tools

The testing stack should include:

- Vitest;
- React Testing Library;
- `user-event`;
- DOM matchers;
- Mock Service Worker;
- Playwright for full browser journeys.

Storybook may be added during the design-system phase to document reusable interface states.

## 11.8 Formatting and Git quality tools

The project should use:

- Prettier;
- ESLint;
- TanStack Query ESLint rules;
- `lint-staged`;
- Husky or another simple Git-hook solution where useful;
- GitHub Actions.

---

# 12. High-Level Application Architecture

The application will use the following dependency direction:

```text
Application setup and routes
            ↓
Business modules
            ↓
Shared interface and infrastructure
```

The import rules are:

```text
app may import modules and shared
routes may import modules and shared
modules may import shared
shared must not import modules
shared must not import app
one module must not deep-import another module's private files
```

The application should contain these major layers:

## 12.1 Application layer

Responsible for:

- providers;
- Router creation;
- Query client creation;
- layouts;
- authentication context;
- global error boundaries;
- global interface state;
- application configuration.

## 12.2 Route layer

Responsible for:

- URL structure;
- route loaders;
- route permissions;
- search-parameter schemas;
- route-level errors;
- code splitting;
- connecting a route to a module page.

Route files should remain thin.

## 12.3 Business module layer

Responsible for:

- pages;
- business-specific components;
- module APIs;
- Query options;
- mutations;
- form schemas;
- module types;
- business utilities;
- tests.

## 12.4 Shared layer

Responsible for:

- design-system components;
- generic data tables;
- common form fields;
- API client;
- standard errors;
- formatting utilities;
- shared hooks;
- shared constants;
- generic loading and empty states.

## 12.5 Mock and test layer

Responsible for:

- API handlers;
- realistic development records;
- data factories;
- test setup;
- end-to-end tests.

---

# 13. Proposed Repository Structure

```text
bomach_os_frontend-services/
├── public/
│   ├── favicon.svg
│   └── static-assets/
│
├── src/
│   ├── app/
│   │   ├── App.tsx
│   │   ├── config/
│   │   ├── errors/
│   │   ├── layouts/
│   │   ├── permissions/
│   │   ├── providers/
│   │   ├── query/
│   │   ├── router/
│   │   └── stores/
│   │
│   ├── routes/
│   │   ├── __root.tsx
│   │   ├── login.tsx
│   │   ├── _operations.tsx
│   │   ├── _operations/
│   │   ├── _portal.tsx
│   │   └── _portal/
│   │
│   ├── modules/
│   │   ├── auth/
│   │   ├── dashboard/
│   │   ├── service-administration/
│   │   ├── commercial/
│   │   ├── finance/
│   │   ├── fulfillment/
│   │   ├── specialized-services/
│   │   └── experience-intelligence/
│   │
│   ├── processes/
│   │   └── service-lifecycle/
│   │
│   ├── shared/
│   │   ├── api/
│   │   ├── components/
│   │   ├── constants/
│   │   ├── data-table/
│   │   ├── forms/
│   │   ├── hooks/
│   │   ├── lib/
│   │   ├── types/
│   │   ├── ui/
│   │   ├── validation/
│   │   └── virtual/
│   │
│   ├── mocks/
│   │   ├── data/
│   │   ├── factories/
│   │   └── handlers/
│   │
│   ├── assets/
│   ├── main.tsx
│   └── routeTree.gen.ts
│
├── tests/
│   └── e2e/
│
├── docs/
│   ├── architecture/
│   ├── standards/
│   ├── product/
│   └── adr/
│
├── .github/
│   ├── workflows/
│   └── pull_request_template.md
│
├── .env.example
├── eslint.config.js
├── package.json
├── tsconfig.json
└── vite.config.ts
```

---

# 14. Structure Inside a Business Module

Each important leaf module should follow a familiar pattern.

Example for service requests:

```text
modules/commercial/requests/
├── api/
│   ├── requests.api.ts
│   ├── requests.keys.ts
│   ├── requests.mutations.ts
│   └── requests.queries.ts
│
├── components/
│   ├── RequestActivityTimeline.tsx
│   ├── RequestDetailsPanel.tsx
│   ├── RequestFilters.tsx
│   ├── RequestStatusBadge.tsx
│   └── RequestTable.tsx
│
├── forms/
│   └── RequestForm.tsx
│
├── pages/
│   ├── CreateRequestPage.tsx
│   ├── RequestDetailsPage.tsx
│   └── RequestsPage.tsx
│
├── schemas/
│   └── request.schema.ts
│
├── types/
│   └── request.types.ts
│
├── utils/
│   └── request.utils.ts
│
├── constants/
│   └── request.constants.ts
│
├── tests/
└── index.ts
```

Not every module needs every folder. Empty folders should not be created only to satisfy a template.

The pattern is a guide, not a reason to create unnecessary files.

---

# 15. Public Module Boundaries

Each module should expose a small public interface through `index.ts`.

External code should import from the module root:

```ts
import {
  RequestsPage,
  requestQueries,
  type ServiceRequest,
} from '@/modules/commercial/requests'
```

External code should not import a private deep path:

```ts
// Avoid this
import { RequestTable } from '@/modules/commercial/requests/components/RequestTable'
```

This rule makes refactoring safer and reduces hidden dependency chains.

---

# 16. Design System Plan

The prototype already provides the main visual direction:

- navy as the main brand colour;
- dark navy for depth and hover states;
- red for strong brand emphasis and destructive actions;
- green for success;
- amber for warnings;
- light grey surfaces and borders;
- compact operational layouts;
- cards, tables, pills, progress indicators, timelines, and kanban boards.

## 16.1 Design tokens

The production design system should use semantic names such as:

```text
brand
brand-strong
surface
surface-muted
background
text
text-muted
text-subtle
border
success
warning
danger
information
```

It should not use unclear names such as `n`, `n2`, `r`, or `t3`.

## 16.2 Shared interface primitives

The first reusable components should include:

- Button;
- IconButton;
- Input;
- Textarea;
- Select;
- Checkbox;
- Radio;
- Switch;
- Label;
- FieldError;
- Badge;
- Card;
- Dialog;
- Drawer;
- Popover;
- Dropdown Menu;
- Tooltip;
- Tabs;
- Avatar;
- Progress Bar;
- Skeleton;
- Pagination.

## 16.3 Shared composed components

The next level should include:

- AppShell;
- Header;
- Sidebar;
- PageHeader;
- Breadcrumbs;
- FilterBar;
- SearchInput;
- DataTable;
- StatCard;
- StatusBadge;
- EmptyState;
- LoadingState;
- ErrorState;
- ConfirmDialog;
- FormSection;
- LifecycleStepper;
- Timeline;
- KanbanBoard;
- NotificationPanel;
- FileUploader;
- MoneyDisplay;
- DateDisplay.

## 16.4 Domain-specific components

Components such as these should remain inside their modules:

- ServiceCard;
- CalculatorPreview;
- RequestActivityTimeline;
- QuotationTotals;
- InvoicePaymentSummary;
- OrderMilestoneBoard;
- DeliverableVersionHistory;
- EstatePlotGrid.

## 16.5 Responsive design

Every page must be designed for:

- desktop;
- smaller laptop;
- tablet;
- mobile.

A responsive page should not merely shrink. It may need to change behaviour.

Examples:

- wide tables may become cards or use controlled horizontal scrolling;
- the sidebar should become a drawer on small screens;
- large forms should become one column;
- dense action groups may move into menus;
- kanban boards may scroll horizontally;
- modals may become full-screen sheets on mobile.

---

# 17. Routing and Navigation Plan

The proposed route groups are:

```text
/login

/operations
├── /dashboard
├── /services
│   ├── /catalogue
│   ├── /calculators
│   ├── /request-forms
│   ├── /workflows
│   └── /branches
├── /commercial
│   ├── /requests
│   ├── /requests/:requestId
│   ├── /quotations
│   ├── /quotations/:quotationId
│   ├── /invoices
│   └── /approvals
├── /fulfillment
│   ├── /orders
│   ├── /orders/:orderId
│   ├── /tasks
│   └── /deliverables
├── /specialized
│   ├── /real-estate
│   ├── /surveying
│   ├── /engineering
│   ├── /logistics
│   └── /technology
└── /intelligence
    ├── /feedback
    ├── /reports
    └── /audit

/portal
├── /dashboard
├── /requests
├── /quotations
├── /orders
├── /payments
├── /documents
└── /approvals
```

## 17.1 Navigation configuration

The sidebar, breadcrumbs, route titles, and permission requirements should come from controlled configuration where practical.

I should not independently hard-code the same page name and path in several places.

## 17.2 Route loaders

Route loaders should ensure important page data is available before the route is shown.

TanStack Router should coordinate with TanStack Query instead of creating a second cache.

## 17.3 Route-level permissions

Protected routes should verify that the user is authenticated and has the required permission.

The route check improves navigation and user experience. The backend still performs the final authorization check.

---

# 18. Authentication and Permission Model

The final system needs real authentication, not the prototype's role switcher.

## 18.1 Authentication requirements

The frontend should support:

- secure login;
- current-user loading;
- session restoration;
- session expiry handling;
- logout;
- disabled-account handling;
- password reset flow where required;
- optional multi-factor authentication;
- clear unauthorized and forbidden states.

## 18.2 Roles and permissions

Roles provide a convenient starting point, but actions should be based on permissions.

Possible permissions include:

```text
service.read
service.create
service.update
service.publish
request.read
request.create
request.assign
request.update
quotation.create
quotation.approve
invoice.create
payment.confirm
order.create
order.update
order.complete
task.assign
deliverable.approve
report.financial.read
audit.read
```

A role may contain several permissions.

## 18.3 Frontend permission rules

Permissions may control:

- visible navigation;
- route access;
- visible actions;
- editable fields;
- report access;
- financial visibility;
- file downloads;
- approval actions.

## 18.4 Client visibility

Client portal permissions must be handled separately from staff permissions.

A client should see only records that belong to the client and are marked as client-visible.

---

# 19. State Ownership Standard

## 19.1 Server state

Examples:

- service list;
- request details;
- quotations;
- invoice balances;
- order progress;
- tasks;
- deliverables;
- reports.

Owner: TanStack Query.

## 19.2 URL state

Examples:

- filters;
- search;
- page number;
- sorting;
- selected view;
- selected tab when shareable.

Owner: TanStack Router.

## 19.3 Form state

Examples:

- create request values;
- service wizard draft;
- quotation values;
- assessment fields.

Owner: TanStack Form.

## 19.4 Local interface state

Examples:

- dialog open state;
- selected row for a temporary action;
- locally expanded section;
- one-page toggle that should not survive navigation.

Owner: React state.

## 19.5 Small global interface state

Examples:

- sidebar collapse preference;
- active branch context;
- table density.

Owner: TanStack Store or a focused Context.

---

# 20. API Integration Standard

## 20.1 API client

The shared API client should handle:

- base URL;
- authentication headers or secure credential mode;
- request IDs where required;
- JSON parsing;
- standard error conversion;
- request cancellation;
- timeout behaviour;
- safe logging in development;
- session-expiry handling.

## 20.2 Module-owned API functions

Each module owns its endpoint functions.

Example:

```text
requests.api.ts        raw HTTP requests
requests.queries.ts    Query options and read operations
requests.mutations.ts  create and update operations
requests.keys.ts       stable Query key definitions
```

## 20.3 API contracts

Every endpoint should have a clear contract defining:

- method;
- path;
- authentication requirement;
- permission requirement;
- request body;
- response body;
- validation errors;
- business errors;
- pagination format;
- filtering options;
- sorting options;
- date format;
- money format;
- file behaviour.

## 20.4 Domain model versus API model

A backend response does not always need to become the exact object used in every component.

Where useful, the frontend can map an API data-transfer object into a domain-friendly display model.

The mapping should be explicit and tested.

## 20.5 Pagination standard

All large register endpoints should follow one pagination style.

A possible response is:

```json
{
  "items": [],
  "page": 1,
  "pageSize": 20,
  "totalItems": 0,
  "totalPages": 0
}
```

The exact format should be agreed with the backend and reused across modules.

## 20.6 Money standard

Money should never be handled carelessly with floating-point calculations.

The API contract should agree on one safe representation, such as:

- minor units as integers; or
- decimal strings with a clear currency.

The frontend should format money for display but should not silently change the financial value.

---

# 21. TanStack Query Standards

## 21.1 Query key factories

Every domain should own a consistent Query key factory.

Example:

```ts
export const requestKeys = {
  all: ['service-requests'] as const,
  lists: () => [...requestKeys.all, 'list'] as const,
  list: (filters: RequestFilters) =>
    [...requestKeys.lists(), filters] as const,
  details: () => [...requestKeys.all, 'detail'] as const,
  detail: (requestId: string) =>
    [...requestKeys.details(), requestId] as const,
}
```

## 21.2 Query options

Reusable query configuration should use a consistent `queryOptions` pattern.

This keeps the key, function, stale policy, and type inference together.

## 21.3 Query cancellation

Query functions should pass the supplied abort signal into the HTTP client.

This prevents outdated requests from continuing after the user changes filters or leaves the page.

## 21.4 Stale-time policy

Stale times should be based on how quickly data changes.

Examples:

- static reference data can remain fresh longer;
- active tasks and notifications should refresh more often;
- audit logs may use manual or paginated loading;
- financial information should refresh after related actions.

There should not be one random stale time for the entire application.

## 21.5 Mutation policy

Low-risk actions may use optimistic updates.

Examples:

- marking a notification as read;
- moving a simple task;
- changing a local preference.

Sensitive actions should wait for server confirmation.

Examples:

- approving a quotation;
- confirming a payment;
- selling or reserving a plot;
- completing an order;
- publishing a service;
- approving a deliverable.

## 21.6 Invalidation policy

A mutation should invalidate only the Query groups affected by the change.

Example: confirming a payment may affect:

- invoice detail;
- invoice list;
- payment list;
- dashboard finance metrics;
- request or order eligibility.

This relationship should be written clearly in the mutation rather than relying on a full application refresh.

## 21.7 Error handling

Query errors should be converted into standard application errors.

The interface should distinguish:

- network errors;
- unauthorized errors;
- forbidden errors;
- not-found errors;
- validation errors;
- conflict errors;
- business-rule errors;
- unexpected server errors.

---

# 22. TanStack Form Standards

## 22.1 Shared form hook

The application should define one approved application form hook with shared Bomach field components.

This keeps forms consistent and reduces repeated setup.

## 22.2 Validation timing

Validation should be chosen intentionally.

Examples:

- required field errors may appear on blur or submit;
- format guidance may appear while typing where it helps;
- expensive async checks should be debounced;
- final business validation happens on the server.

## 22.3 Form schemas

Each important form should have a schema and a named TypeScript type.

The schema should define:

- required values;
- field formats;
- minimum and maximum values;
- related-field rules;
- step-level validation where needed.

## 22.4 Multi-step forms

The Create Service wizard should be one composed form, not six unrelated forms.

Suggested groups are:

```text
basic
subServices
pricing
requestForm
workflow
publication
```

Each step can validate its section, while final submission validates the full object.

## 22.5 Unsaved work

Long forms should warn the user before navigation when there are unsaved changes.

Draft saving may be added for:

- service configuration;
- complex quotations;
- long assessments;
- workflow design.

## 22.6 Submission handling

A form submission should:

1. prevent duplicate submission;
2. show a clear pending state;
3. submit through a Query mutation;
4. display field errors returned by the backend;
5. display a form-level business error where needed;
6. redirect or update the page only after success;
7. preserve user input after recoverable failures.

---

# 23. TanStack Table Standards

## 23.1 Shared table component

The shared DataTable should handle:

- visual structure;
- loading state;
- empty state;
- error state;
- pagination controls;
- column headers;
- sorting controls;
- selection controls;
- responsive behaviour;
- accessibility labels.

Each module should own its columns and business-specific cell rendering.

## 23.2 Server-side registers

Large registers should use backend filtering, sorting, and pagination.

The flow should be:

```text
Router search parameters
        ↓
Query key and API request
        ↓
Backend result
        ↓
TanStack Table display
```

## 23.3 Column rules

Columns should use stable IDs.

Business formatting should use approved components such as:

- MoneyDisplay;
- DateDisplay;
- StatusBadge;
- UserDisplay;
- BranchDisplay.

## 23.4 Row actions

A table should not become overcrowded with many buttons.

Use:

- one primary action where appropriate;
- an action menu for secondary actions;
- permission checks;
- confirmations for destructive or irreversible actions.

## 23.5 Export

CSV or report export should normally be produced by the backend for large or permission-sensitive datasets.

The export must respect the same filters and permissions as the screen.

---

# 24. File and Document Handling

The prototype simulates file uploads. The production system needs secure file handling.

The frontend should support:

- file type validation;
- size validation;
- upload progress;
- cancellation;
- retry;
- queued uploads where appropriate;
- version information;
- client visibility;
- approval state;
- preview where safe;
- secure download links;
- clear failed-upload recovery.

The backend or file service should control:

- storage;
- virus or malware scanning where required;
- authorization;
- signed access links;
- retention;
- version history;
- audit events;
- deletion rules.

Files should not be stored as uncontrolled base64 values inside normal API records.

---

# 25. Notifications and Background Work

The system will need notifications for events such as:

- request assignment;
- overdue request;
- quotation approval;
- payment confirmation;
- new task;
- overdue task;
- milestone review;
- deliverable approval;
- client action required;
- order completion.

The frontend notification centre should support:

- unread count;
- read and unread state;
- links to the affected record;
- category;
- created time;
- safe pagination;
- mark-as-read actions.

Long-running work should be handled by backend jobs where needed.

Examples:

- PDF quotation generation;
- report generation;
- large CSV export;
- bulk notifications;
- email delivery;
- document processing.

The frontend should show job state rather than keeping one browser request open indefinitely.

---

# 26. Error-Handling Standard

The application should handle errors at four levels.

## 26.1 Field-level errors

Shown beside a specific field.

Example:

```text
Phone number is required.
```

## 26.2 Form-level errors

Shown when the entire form cannot be submitted.

Example:

```text
The quotation could not be submitted because the approval route is missing.
```

## 26.3 Page-level errors

Shown when a page cannot load its main data.

The user should be able to retry where appropriate.

## 26.4 Application-level errors

Unexpected rendering failures should be caught by an application or route error boundary.

Each asynchronous page should deliberately support:

```text
loading
success
empty
error
unauthorized
forbidden
not found
```

---

# 27. Backend Capabilities Required

The frontend roadmap depends on backend capabilities. The backend does not have to be completed before all frontend work, but its contracts must be planned early.

Required backend areas include:

## 27.1 Identity and access

- authentication;
- current user;
- roles;
- permissions;
- sessions;
- password management;
- account status.

## 27.2 Service administration

- services;
- sub-services;
- calculators;
- request field definitions;
- workflows;
- workflow stages;
- branch activation;
- service publication.

## 27.3 Commercial operations

- clients;
- requests;
- request activities;
- assessments;
- quotations;
- quotation versions;
- approvals.

## 27.4 Finance

- invoices;
- payment schedules;
- payments;
- receipts;
- reconciliation states;
- payment provider integrations.

## 27.5 Fulfilment

- service orders;
- stages;
- milestones;
- tasks;
- task evidence;
- deliverables;
- deliverable versions;
- client approvals;
- completion rules.

## 27.6 Specialized services

- estates;
- plots;
- plot reservations;
- plot sales;
- property listings;
- survey records;
- engineering project records;
- delivery tracking;
- technology project details.

## 27.7 Experience and intelligence

- client portal records;
- feedback;
- complaints;
- reports;
- notifications;
- audit events.

## 27.8 Platform capabilities

- file storage;
- email and message delivery;
- background jobs;
- webhooks;
- rate limiting;
- audit integrity;
- data backups;
- monitoring.

---

# 28. Phased Delivery Roadmap

The roadmap is arranged so that every phase builds on a tested foundation.

The phase numbers describe order and dependency. The exact calendar duration can change based on team size, backend readiness, and scope changes.

A normal sprint may last two weeks. A very small team may treat some phases as several sprints.

---

# Phase 0 — Product Discovery, Scope, and Contract Planning

## Goal

Turn the prototype and business discussion into approved requirements before production feature work begins.

## Main work

- review every prototype page;
- create a complete screen inventory;
- create a role and permission matrix;
- define the shared service lifecycle;
- define specialized-service differences;
- document status values and allowed transitions;
- identify required backend endpoints;
- identify required reports;
- identify file types and document rules;
- identify notification triggers;
- identify financial approval thresholds;
- identify client-visible and internal-only information;
- create a first data dictionary;
- decide which prototype behaviour is real and which is only demonstration data;
- create architecture decision records.

## Product deliverables

- approved Service Operations overview;
- screen inventory;
- module inventory;
- role and permission matrix;
- lifecycle map;
- status glossary;
- API contract backlog;
- first release scope;
- deferred-feature list;
- risk register.

## Engineering deliverables

- frontend architecture document;
- repository structure decision;
- TanStack responsibility map;
- testing strategy;
- design-system plan;
- branch and pull-request workflow;
- Definition of Ready;
- Definition of Done.

## Exit criteria

This phase is complete when:

- the team can explain the complete service journey;
- every first-release page belongs to a module;
- each important action has an expected permission;
- major statuses and transitions are agreed;
- frontend and backend teams know the first API contracts to build;
- no one needs to guess where production code should be placed.

---

# Phase 1 — Repository and Engineering Foundation

## Goal

Create a stable frontend foundation before business pages are added.

## Main work

- remove the default Vite demonstration page;
- create the agreed directory structure;
- configure path aliases;
- configure strict TypeScript settings;
- configure Prettier;
- improve ESLint rules;
- add TanStack Query ESLint rules;
- configure TanStack Router and its Vite plugin;
- configure the Query client;
- add Router and Query development tools;
- add standard environment configuration;
- create the shared API client;
- create the standard application error model;
- set up Vitest and Testing Library;
- set up Mock Service Worker;
- set up Playwright;
- set up CI;
- create development documentation.

## Important technical decisions

- file-based routing;
- generated route tree is not edited manually;
- strict module boundaries;
- one standard API client;
- one standard Query client;
- no feature data in a global store;
- no direct raw fetch calls inside page components.

## Deliverables

- application starts successfully;
- production build succeeds;
- lint command succeeds;
- type-check command succeeds;
- test command succeeds;
- CI runs on pull requests;
- mock server can return one example API response;
- project README explains local setup.

## Exit criteria

The phase is complete when a new developer can clone the project, install dependencies, run it, run tests, and understand the basic structure without private instructions.

---

# Phase 2 — Design System and Application Shell

## Goal

Create the reusable visual foundation and the main operations layout.

## Main work

- define semantic design tokens;
- define typography;
- define spacing;
- define borders, shadows, and radii;
- create Button and IconButton;
- create form controls;
- create Card, Badge, Dialog, Drawer, Tabs, Progress, Skeleton, and Tooltip;
- create PageHeader and Breadcrumbs;
- create loading, empty, and error states;
- create header;
- create desktop sidebar;
- create mobile navigation drawer;
- create notifications panel shell;
- create operations layout;
- create client portal layout shell;
- create responsive breakpoints;
- create component tests;
- create Storybook stories where Storybook is adopted.

## Deliverables

- approved design-token file;
- reusable component library;
- responsive application shell;
- accessible keyboard navigation through the shell;
- visual comparison against the prototype;
- documented component variants.

## Exit criteria

The phase is complete when feature teams can build pages without creating new versions of buttons, inputs, cards, status badges, dialogs, and page headers.

---

# Phase 3 — Authentication, User Context, and Permissions

## Goal

Create the secure application entry point and permission-aware navigation.

## Main work

- build the login page;
- integrate the login API;
- load the current user;
- restore an existing session;
- handle session expiry;
- build logout;
- define role and permission types;
- create permission helpers;
- create protected routes;
- create forbidden and unauthorized pages;
- filter navigation by permission;
- protect action buttons;
- create client portal access rules;
- test permission scenarios.

## Deliverables

- real login flow;
- authenticated operations layout;
- authenticated client portal layout;
- route protection;
- permission-aware navigation;
- session-expiry handling;
- tests for at least the main roles.

## Exit criteria

The phase is complete when users enter the correct layout, cannot navigate to forbidden routes through normal navigation, and receive a clear response when the backend rejects an unauthorized action.

---

# Phase 4 — Walking Skeleton: First End-to-End Journey

## Goal

Prove the architecture with one small but complete business journey before building every module.

## Suggested journey

```text
Login
  ↓
Dashboard shell
  ↓
Request register
  ↓
Create request
  ↓
Request detail
  ↓
Create draft quotation
  ↓
Create a basic service order
  ↓
View order detail
```

This journey may use Mock Service Worker first and the real backend as soon as the API is ready.

## Main work

- build one request list;
- put filters in Router search parameters;
- load list data through Query;
- render it with Table;
- build a request form with Form;
- create a request mutation;
- open a request detail route;
- create a simple quotation form;
- create a simple service order;
- connect success navigation and cache invalidation;
- add component and end-to-end tests.

## What this phase proves

- routing;
- route parameters;
- search parameters;
- Query keys;
- mutations;
- forms;
- tables;
- API errors;
- permission checks;
- cache invalidation;
- shared components;
- end-to-end test setup.

## Exit criteria

The phase is complete when one realistic business journey works across several pages without bypassing the agreed architecture.

---

# Phase 5 — Service Administration

## Goal

Allow administrators to define how each Bomach service behaves.

## Features

### Service catalogue

- service list;
- search and filters;
- draft, active, paused, and archived states;
- service details;
- duplicate service;
- publish and pause controls;
- branch availability summary.

### Create Service wizard

- basic information;
- sub-services;
- pricing configuration;
- request fields;
- workflow stages;
- branch publication;
- step validation;
- draft support;
- final review;
- transactional submission.

### Calculator library

- calculator list;
- calculator detail;
- safe formula model;
- test values;
- tax settings;
- deposit settings;
- approval thresholds;
- service assignment.

### Request Form Builder

- available field types;
- field labels;
- required state;
- choices;
- help text;
- ordering;
- conditional rules where confirmed;
- preview;
- save draft;
- publish.

### Workflow Designer

- stages;
- stage owners;
- service-level targets;
- approvals;
- evidence requirements;
- client checkpoints;
- stage ordering;
- safe transition rules;
- workflow validation.

### Branch Activation

- active branches;
- branch owner;
- capacity;
- branch service-level target;
- branch status;
- future support for branch pricing.

## Backend requirements

- service configuration APIs;
- calculator APIs;
- form-definition APIs;
- workflow APIs;
- branch APIs;
- publication validation;
- versioning or history where required.

## Tests

- service creation wizard;
- required-field validation;
- permission restrictions;
- safe calculator tests;
- workflow stage ordering;
- branch activation;
- publish rules.

## Exit criteria

The phase is complete when an authorized administrator can define a usable service without a developer adding a special hard-coded page for that service.

---

# Phase 6 — Commercial Operations

## Goal

Build the complete request and quotation process.

## Features

### Service Request Register

- server-side pagination;
- search;
- branch filters;
- division filters;
- service filters;
- owner filters;
- status filters;
- due-date filters;
- sort options;
- saved or shareable URLs.

### Request creation

- service-driven dynamic fields;
- client information;
- source information;
- budget;
- scope;
- files;
- consent;
- basic estimate;
- backend validation.

### Request 360

- client summary;
- service summary;
- status;
- owner;
- due date;
- next action;
- activity journal;
- assessment history;
- quotations;
- related approvals;
- files;
- audit summary.

### Communication journal

- phone call;
- WhatsApp;
- email;
- meeting;
- site visit;
- internal note;
- document received;
- outcome;
- next follow-up.

### Assessments

- assessment type;
- professional assignment;
- schedule;
- status;
- findings;
- evidence;
- recommendation;
- approval where required.

### Quotations

- quote list;
- quote builder;
- line items;
- scope;
- taxes;
- discounts;
- deposit;
- validity;
- terms;
- version history;
- PDF generation job;
- client delivery;
- acceptance state.

## Exit criteria

The phase is complete when a request can move from initial capture through review, assessment, a controlled quotation, and client acceptance with full history.

---

# Phase 7 — Approvals, Invoices, and Payments

## Goal

Complete the governance and financial part of the commercial flow.

## Features

### Approval Queue

- pending approvals;
- approval detail;
- approve;
- reject;
- request changes;
- comments;
- due date;
- escalation;
- approval history;
- permission checks.

### Approval routes

- amount-based approval;
- discount-based approval;
- service-based approval;
- sequential approvals where required;
- client approval separated from internal approval.

### Invoices

- create from accepted quotation;
- payment schedule;
- due date;
- invoice line items;
- balance;
- status;
- PDF generation;
- client visibility.

### Payments

- payment list;
- confirm payment;
- payment channel;
- transaction reference;
- receipt;
- reconciliation status;
- reversals where supported;
- payment-provider callbacks where used.

### Order eligibility

- check required payment threshold;
- show why an order cannot yet activate;
- create or activate order after server confirmation;
- record audit event.

## Security standard

Payment confirmation and approval decisions must not use unconfirmed optimistic updates.

## Exit criteria

The phase is complete when accepted work can be invoiced, paid, approved, and made eligible for service-order execution using backend-confirmed rules.

---

# Phase 8 — Fulfilment and Service Orders

## Goal

Build the operational system that delivers approved and paid work.

## Features

### Service Order board

- status columns;
- search;
- owner filter;
- branch filter;
- service filter;
- due-date filter;
- progress summary;
- responsive board and table alternatives.

### Order Control Room

- order summary;
- current stage;
- progress;
- owner;
- due date;
- value summary;
- next action;
- activity history;
- related tasks;
- milestones;
- deliverables;
- approvals;
- client checkpoints.

### Milestones

- milestone list;
- stage transitions;
- active stage;
- blocked stage;
- evidence requirements;
- approval requirements;
- completion rules;
- stage history.

### Tasks

- create;
- assign;
- reassign;
- priority;
- due date;
- status;
- checklist;
- comments;
- evidence;
- dependencies where confirmed;
- overdue indicators.

### Deliverables

- upload;
- version history;
- reviewer;
- comments;
- client visibility;
- approval;
- rejection and revision;
- secure download;
- audit history.

### Quality and acceptance

- supervisor review;
- professional review;
- client approval;
- handover;
- completion checks;
- completion reason;
- cancellation and hold handling.

## Exit criteria

The phase is complete when an authorized team can execute an order from mobilisation through controlled stages, tasks, documents, review, and completion.

---

# Phase 9 — Specialized Service Areas

## Goal

Add division-specific behaviour without duplicating the shared commercial and fulfilment system.

## 9.1 Real Estate

- estates;
- plot layout;
- plot status;
- reservations;
- holds;
- sales;
- client allocation;
- agreed price;
- property brokerage;
- conflict-safe reservation and sale actions.

## 9.2 Land Surveying

- title-document checklist;
- field schedule;
- survey team;
- coordinates and beacon records;
- processing stage;
- professional review;
- plan version;
- lodgement;
- final delivery.

## 9.3 Engineering and Construction

- site assessment;
- drawings and bill of quantities;
- project setup;
- site milestones;
- inspections;
- progress reports;
- variations;
- handover records.

## 9.4 Courier and Logistics

- pickup details;
- rider assignment;
- tracking states;
- delivery event history;
- proof of delivery;
- failed delivery handling;
- client notification.

## 9.5 Information Technology

- discovery;
- requirements;
- design;
- development;
- testing;
- deployment;
- support;
- specifications and release deliverables.

## Standard

Every specialized module should reuse the existing:

- request;
- quotation;
- approval;
- invoice;
- payment;
- order;
- task;
- deliverable;
- audit infrastructure.

## Exit criteria

The phase is complete when specialized divisions gain useful domain features without creating separate, disconnected copies of the core service lifecycle.

---

# Phase 10 — Client Portal

## Goal

Give clients controlled access to their own service records.

## Features

- client login;
- client dashboard;
- service requests;
- request status;
- quotations;
- quotation acceptance;
- invoices;
- payment history;
- outstanding balance;
- active service orders;
- progress;
- client-visible updates;
- documents;
- document approval;
- milestone approval;
- action-required list;
- feedback;
- complaint submission;
- notification preferences where required.

## Privacy standard

The portal must never depend only on hidden buttons. The backend must ensure that a client can access only allowed records.

## Exit criteria

The phase is complete when a client can follow a service and complete required actions without seeing internal-only information.

---

# Phase 11 — Reports, Audit, Notifications, and Management Intelligence

## Goal

Give management reliable visibility and preserve accountability.

## Features

### Dashboard

- role-specific cards;
- alerts;
- approval counts;
- overdue records;
- confirmed revenue;
- outstanding balance;
- active orders;
- service-level compliance;
- recent activity.

### Reports

- request volume;
- response time;
- quotation conversion;
- invoice and payment summary;
- active order value;
- on-time delivery;
- service performance;
- branch performance;
- owner workload;
- client satisfaction;
- complaint and rework rate.

### Audit

- paginated audit register;
- filters by actor, action, area, record, and date;
- record-specific audit timeline;
- export where permitted;
- immutable backend records.

### Notifications

- notification centre;
- unread count;
- mark as read;
- action links;
- categories;
- pagination;
- email or message integration through backend jobs.

## Exit criteria

The phase is complete when management can understand system health from trusted backend data and investigate important actions through an audit trail.

---

# Phase 12 — Production Hardening and Release

## Goal

Prepare the system for safe production use.

## Main work

- complete responsive review;
- complete accessibility review;
- complete security review;
- test permission boundaries;
- test session expiry;
- test large datasets;
- add virtualization where proven necessary;
- review Query stale and invalidation rules;
- review bundle size;
- add route-level code splitting;
- optimize images and assets;
- test file uploads;
- test slow networks;
- test failed requests;
- test browser back and forward behaviour;
- complete end-to-end tests;
- complete cross-browser testing;
- configure error monitoring;
- configure application logging policy;
- configure production environment variables;
- configure deployment pipeline;
- create rollback plan;
- create support and incident documentation;
- complete user acceptance testing;
- train internal users;
- release to a pilot group;
- monitor pilot use;
- fix critical issues;
- release more widely.

## Exit criteria

The phase is complete when the release gates are passed, critical user journeys are tested, monitoring is active, and the team can support and roll back the application.

---

# Phase 13 — Post-Release Improvement

## Goal

Improve the platform using real usage data instead of assumptions.

## Possible work

- performance tuning based on real traces;
- workflow improvements;
- stronger report filters;
- real-time updates where useful;
- offline field work;
- advanced notification preferences;
- TanStack DB experiment;
- mobile application assessment;
- advanced automation;
- deeper integrations;
- client self-service improvements;
- predictive alerts;
- AI-assisted summaries where approved.

No advanced feature should weaken the core audit, permission, and data-consistency rules.

---

# 29. Sprint and Delivery Model

A suggested sprint length is two weeks.

Each sprint should include:

1. planning;
2. implementation;
3. tests;
4. review;
5. demonstration;
6. retrospective;
7. documentation updates.

## 29.1 Sprint planning

Every story should have:

- a clear user or business outcome;
- acceptance criteria;
- permission rules;
- API dependency;
- design reference;
- loading, empty, and error expectations;
- test expectations;
- known risks.

## 29.2 Daily work

Daily coordination should identify:

- completed work;
- current work;
- blockers;
- backend dependencies;
- design questions;
- risks to the sprint goal.

## 29.3 Sprint review

A sprint review should demonstrate working behaviour, not only screenshots or code.

## 29.4 Retrospective

The team should review:

- what worked;
- what slowed the work;
- what pattern should become a standard;
- what technical debt was created;
- what should change in the next sprint.

---

# 30. Backlog and Story Standards

A good story should describe the user outcome.

Example:

```text
As a Service Manager,
I want to assign a new service request to an owner,
so that responsibility and the next action are clear.
```

Acceptance criteria may include:

```text
Given I have request-assignment permission,
when I choose an active staff member and save,
then the backend updates the request owner,
the request activity timeline records the change,
and the request list and request detail show the new owner.
```

A story should not be written only as:

```text
Build assignment dropdown.
```

The dropdown is an implementation detail. The real outcome is controlled ownership.

---

# 31. Definition of Ready

A story is ready for implementation when:

- the business purpose is clear;
- the main acceptance criteria are written;
- the responsible roles and permissions are known;
- the design or layout expectation is available;
- required API contracts are available or mocked;
- important statuses and transitions are known;
- error behaviour is understood;
- dependencies are identified;
- major open questions are resolved.

A story should not enter active development when the developer must invent the business rule alone.

---

# 32. Definition of Done

A story is complete only when all relevant items below are satisfied:

- the approved behaviour works;
- TypeScript types are complete;
- no unnecessary `any` was introduced;
- loading state is present;
- empty state is present where relevant;
- error state is present;
- permission behaviour is implemented;
- form validation is implemented;
- backend errors are handled;
- responsive behaviour is checked;
- keyboard behaviour is checked;
- accessible names are present;
- tests are added or updated;
- mocks are updated where required;
- lint passes;
- type check passes;
- tests pass;
- production build passes;
- review comments are resolved;
- documentation is updated;
- the story is demonstrated against its acceptance criteria.

---

# 33. TypeScript Standards

## 33.1 Strictness

TypeScript strict mode should remain enabled.

The project should also consider strict options such as:

- `noUncheckedIndexedAccess`;
- `exactOptionalPropertyTypes`;
- `noImplicitOverride`;
- unused variable checks where they fit the tooling.

## 33.2 Avoid `any`

Use `unknown` at uncertain boundaries and validate it.

`any` should require a clear reason and should not be the normal solution to a type error.

## 33.3 Domain statuses

Use specific unions or generated enum types.

Example:

```ts
type OrderStatus =
  | 'pending-mobilisation'
  | 'active'
  | 'quality-review'
  | 'awaiting-client'
  | 'completed'
  | 'on-hold'
  | 'cancelled'
```

Do not use `string` where the allowed values are known.

## 33.4 DTOs, domain models, and form values

These may be different types.

- API DTO: shape received from backend;
- domain model: shape convenient for application logic;
- form values: editable form shape;
- table row: display shape where needed.

They should not be mixed silently.

## 33.5 Type assertions

Avoid forceful assertions such as `as SomeType` when validation or proper inference can solve the problem.

---

# 34. File and Naming Standards

```text
Directories             kebab-case
React components        PascalCase.tsx
Hooks                   useSomething.ts
Types                   something.types.ts
Schemas                 something.schema.ts
Queries                 something.queries.ts
Mutations               something.mutations.ts
Query keys              something.keys.ts
API functions           something.api.ts
Utilities               something.utils.ts
Constants               something.constants.ts
Tests                   Something.test.tsx
Stories                 Something.stories.tsx
```

Names should describe the business meaning.

Prefer:

```text
RequestStatusBadge
QuotationApprovalPanel
OrderMilestoneBoard
```

Avoid vague names such as:

```text
InfoBox
DataThing
MainComponent
Helper2
```

---

# 35. React Component Standards

- A component should have one clear responsibility.
- Pages coordinate data and major page sections.
- Shared presentational components should not unexpectedly fetch business data.
- API calls should not be placed directly in table cells or basic buttons.
- Large calculations should not be hidden inside JSX.
- Components should use composition rather than very large prop configurations where possible.
- A component should not become reusable until a real repeated pattern exists.
- Effects should not be used to copy derived values from one state owner into another.
- Derived data should be calculated from the source or memoized only when measurement shows it helps.
- Business rules should not be buried in colour or label components.

---

# 36. Import Standards

Use path aliases:

```ts
import { Button } from '@/shared/ui'
```

Avoid long relative paths:

```ts
import { Button } from '../../../../shared/ui/button'
```

Do not import private files from another module.

Circular dependencies should be treated as architectural errors, not ignored warnings.

---

# 37. Tailwind and Styling Standards

- Use semantic design tokens.
- Use shared components for repeated controls.
- Avoid unexplained arbitrary values when a token is suitable.
- Keep class names readable.
- Use component variants for approved states.
- Do not use colour alone to communicate status.
- Preserve visible focus styles.
- Respect reduced-motion preferences.
- Avoid global CSS rules that unexpectedly affect module components.
- Do not copy the prototype's compressed class naming into production.

---

# 38. Accessibility Standards

The application should target WCAG 2.2 AA as the working accessibility standard.

Required practices include:

- semantic HTML;
- keyboard access;
- visible focus;
- labelled inputs;
- clear error messages;
- accessible dialog focus management;
- correct heading order;
- adequate colour contrast;
- non-colour status indicators;
- accessible table headers;
- accessible names for icon-only buttons;
- screen-reader announcements for important async changes where needed;
- reduced-motion support;
- sufficient touch-target size.

Accessibility should be tested during each feature, not only before release.

---

# 39. Security Standards

## 39.1 Frontend security rules

- never store secrets in frontend source code;
- never put private credentials in Vite environment variables exposed to the browser;
- do not trust route protection as backend security;
- escape or safely render user-controlled text;
- sanitize rich text where rich text is supported;
- avoid unsafe HTML rendering;
- do not evaluate user formulas with `Function` or `eval`;
- validate files before upload, while remembering that backend validation is still required;
- handle session expiry safely;
- do not expose internal errors to users;
- avoid logging tokens, passwords, payment references, or private client data;
- use secure transport in deployed environments;
- use dependency scanning and updates.

## 39.2 Financial safety

The following must wait for backend confirmation:

- payment confirmation;
- invoice cancellation;
- discount approval;
- quotation approval;
- plot sale;
- order completion where contractual effects exist.

## 39.3 Concurrency safety

The backend must prevent conflicts such as:

- two people reserving the same plot;
- duplicate approval submission;
- duplicate payment confirmation;
- two users advancing the same order stage incorrectly;
- lost updates to service configuration.

The frontend should display conflict errors clearly and reload the latest record.

---

# 40. Testing Strategy

## 40.1 Unit tests

Use for:

- formatters;
- calculation helpers;
- permission helpers;
- status mapping;
- transition rules represented in frontend helpers;
- schema behaviour;
- data mapping.

## 40.2 Component tests

Use for:

- forms;
- validation;
- tables;
- filters;
- dialogs;
- permission visibility;
- loading and error states;
- important user interaction.

## 40.3 Integration tests

Use with Mock Service Worker for:

- request list and filters;
- request creation;
- mutation success and failure;
- cache invalidation;
- quotation workflow;
- order updates;
- file-upload states.

## 40.4 End-to-end tests

Use Playwright for critical journeys:

- login;
- create request;
- assess request;
- create quotation;
- approve quotation;
- issue invoice;
- confirm payment;
- create or activate order;
- complete a task;
- upload and approve deliverable;
- client approval;
- complete order.

## 40.5 What not to test

Avoid tests that only confirm internal implementation details, such as private state variable names.

Tests should focus on user-visible behaviour, business outcomes, and public module behaviour.

---

# 41. Performance Standards

Performance should be measured, not guessed.

The main practices will include:

- route-level code splitting;
- Query caching;
- cancellation of outdated requests;
- server-side pagination;
- debounced search;
- virtualization only for large lists;
- lazy loading of secondary panels;
- image optimization;
- avoiding unnecessary large dependencies;
- avoiding repeated data copies;
- profiling slow interactions;
- controlling expensive calculations;
- limiting unnecessary background refresh.

The application should remain useful on slower networks and normal office hardware.

Important pages should provide skeletons or useful pending states rather than showing an empty screen.

---

# 42. Observability and Support Standards

The production application should support investigation when something fails.

## 42.1 Error monitoring

Unexpected frontend errors should be reported to an approved monitoring service with:

- environment;
- application version;
- route;
- safe error details;
- safe user or organization reference where approved;
- request correlation ID where available.

## 42.2 Logging

Frontend logs must not include sensitive information.

Important business audit events belong on the backend, not only in browser logs.

## 42.3 Release identification

Each deployed release should have a version or commit identifier so that an error can be connected to the exact code release.

## 42.4 Support documentation

Support staff should have guides for:

- login problems;
- permission problems;
- stale data or conflict messages;
- failed uploads;
- payment display issues;
- failed background exports;
- browser requirements;
- escalation paths.

---

# 43. Environment and Configuration Standards

Recommended environments:

```text
local
review or preview
staging
production
```

## 43.1 Environment rules

- each environment has its own API base configuration;
- production secrets must not be in the repository;
- `.env.example` documents required non-secret variables;
- local mocks can be enabled explicitly;
- production must not accidentally use mock handlers;
- environment checks should fail clearly when required configuration is missing.

## 43.2 Feature flags

Feature flags may be used for:

- controlled pilot releases;
- unfinished modules;
- branch-specific rollouts;
- testing a new workflow;
- disabling a risky feature without redeploying where backend flags support it.

Flags must not become permanent substitutes for cleaning up old code.

---

# 44. Git and Pull-Request Workflow

## 44.1 Branch naming

Examples:

```text
feat/service-catalogue
feat/request-creation
feat/order-control-room
fix/request-filter-reset
refactor/query-key-factory
docs/frontend-architecture
```

## 44.2 Commit style

Use focused commit messages:

```text
feat(requests): add request creation form
fix(orders): preserve status filter in the URL
refactor(ui): extract shared status badge
test(quotes): cover discount approval threshold
docs(architecture): document module boundaries
```

## 44.3 Pull-request requirements

A pull request should explain:

- what changed;
- why it changed;
- screenshots or recordings for interface changes;
- how it was tested;
- permissions affected;
- API contracts affected;
- known follow-up work;
- checklist results.

## 44.4 Review standard

Reviewers should check:

- business correctness;
- module boundaries;
- state ownership;
- Query invalidation;
- permission handling;
- error handling;
- accessibility;
- tests;
- documentation;
- unnecessary complexity.

---

# 45. Continuous Integration and Deployment

Every pull request should run at least:

```bash
npm ci
npm run typecheck
npm run lint
npm run test:run
npm run build
```

Later stages may include:

```bash
npm run test:e2e
npm run storybook:build
```

## 45.1 Merge gates

Do not merge when there are:

- TypeScript errors;
- ESLint errors;
- failing tests;
- failed production builds;
- unresolved required review comments;
- known critical security issues.

## 45.2 Deployment flow

A normal release flow should be:

```text
Pull request
    ↓
Automated checks
    ↓
Review environment
    ↓
Merge
    ↓
Staging deployment
    ↓
Smoke tests and user acceptance
    ↓
Production approval
    ↓
Production deployment
    ↓
Monitoring
```

## 45.3 Rollback

Every production release should have a clear rollback method.

The team should know:

- which previous frontend version is stable;
- how to restore it;
- how backend compatibility will be handled;
- how feature flags can reduce risk.

---

# 46. Documentation Standards

The codebase should contain focused documentation.

Suggested structure:

```text
docs/
├── product/
│   ├── service-operations-overview.md
│   ├── lifecycle-and-statuses.md
│   └── role-permission-matrix.md
├── architecture/
│   ├── frontend-architecture.md
│   ├── module-boundaries.md
│   ├── routing-and-permissions.md
│   ├── state-ownership.md
│   └── data-flow.md
├── standards/
│   ├── query-conventions.md
│   ├── router-conventions.md
│   ├── form-conventions.md
│   ├── table-conventions.md
│   ├── testing-strategy.md
│   ├── naming-and-imports.md
│   └── accessibility.md
└── adr/
    ├── 001-use-tanstack-router.md
    ├── 002-use-query-for-server-state.md
    ├── 003-use-tanstack-form.md
    ├── 004-use-table-and-virtual.md
    ├── 005-limit-global-store.md
    ├── 006-defer-tanstack-db.md
    └── 007-remain-on-vite-spa.md
```

Documentation should explain decisions and examples. It should not only repeat library documentation.

---

# 47. Architecture Decision Records

Important technical decisions should be documented as short Architecture Decision Records.

Each record should contain:

- context;
- decision;
- alternatives considered;
- consequences;
- date;
- status.

Initial decisions should include:

1. use TanStack Router;
2. use TanStack Query as the only server-state owner;
3. use TanStack Form;
4. use TanStack Table for registers;
5. use TanStack Virtual only when needed;
6. use Pacer carefully because it may change;
7. limit global Store usage;
8. defer TanStack DB;
9. remain on Vite SPA;
10. treat the HTML prototype as product reference, not production source.

---

# 48. Migration Plan From the Prototype

The prototype should be converted feature by feature.

## 48.1 Do not copy these prototype patterns

- one global data object;
- one file containing all pages;
- inline click handlers;
- HTML strings inserted into the page;
- `localStorage` as the business database;
- role switching as authorization;
- raw formula execution;
- frontend-only audit records;
- hard-coded report values;
- direct global DOM element access.

## 48.2 Reuse these prototype strengths

- the business lifecycle;
- the visual direction;
- navigation grouping;
- page inventory;
- sample status ideas;
- sample service types;
- sample role ideas;
- service configuration concept;
- request, quote, payment, and order relationships;
- specialized service examples;
- client portal concept;
- reporting and audit expectations.

## 48.3 Conversion method

For every prototype section:

1. describe the business purpose;
2. confirm the data required;
3. confirm roles and permissions;
4. confirm backend contract;
5. identify shared components;
6. build the route;
7. build Query options;
8. build the page;
9. build forms and tables;
10. add tests;
11. compare with the prototype;
12. document deliberate differences.

---

# 49. Main Risks and Mitigation

## Risk 1: Building too many screens before completing a workflow

**Mitigation:** Build the walking skeleton early.

## Risk 2: Copying the prototype into large React components

**Mitigation:** Enforce module boundaries and review file responsibility.

## Risk 3: Confusing Router, Query, Form, and Store state

**Mitigation:** Follow the state-ownership map and document exceptions.

## Risk 4: Backend contracts arriving late

**Mitigation:** Define contracts during Phase 0 and use Mock Service Worker.

## Risk 5: Permission rules being added after pages are built

**Mitigation:** Define permission requirements in stories and routes from the beginning.

## Risk 6: Financial and approval actions becoming unsafe optimistic updates

**Mitigation:** Require server confirmation for sensitive operations.

## Risk 7: Specialized modules duplicating the full core system

**Mitigation:** Specialized modules must extend shared request and order records.

## Risk 8: Pacer API changes

**Mitigation:** Use it only behind small wrappers, pin versions, and avoid making it core business infrastructure.

## Risk 9: Forms becoming inconsistent

**Mitigation:** Create shared TanStack Form hooks and field components early.

## Risk 10: Tables becoming difficult to maintain

**Mitigation:** Use one shared DataTable presentation and module-owned column definitions.

## Risk 11: The frontend becoming the source of truth for business rules

**Mitigation:** Keep final validation, authorization, transitions, and audit on the backend.

## Risk 12: Large datasets causing poor performance

**Mitigation:** Use server pagination, measured caching, and virtualization where needed.

## Risk 13: Documentation becoming outdated

**Mitigation:** Include documentation updates in the Definition of Done.

---

# 50. Success Measures

The platform should eventually be measured by both business and engineering results.

## 50.1 Business measures

- fewer unassigned requests;
- shorter request-response time;
- shorter quotation turnaround;
- clearer approval times;
- fewer overdue orders;
- improved on-time delivery;
- improved payment visibility;
- reduced lost client communication;
- improved client satisfaction;
- lower rework rate;
- complete audit history;
- better branch and service reporting.

## 50.2 Engineering measures

- production build reliability;
- low escaped-defect rate;
- stable critical end-to-end tests;
- consistent module structure;
- low number of permission regressions;
- clear API contracts;
- acceptable page performance;
- accessible critical journeys;
- short recovery time after frontend incidents;
- predictable delivery across sprints.

---

# 51. Recommended First Implementation Sequence

The first practical sequence should be:

```text
1. Approve this roadmap and architecture.
2. Create the docs and ADR structure.
3. Clean the Vite starter.
4. Configure Router, Query, strict TypeScript, linting, formatting, and tests.
5. Create design tokens and the application shell.
6. Create authentication and permissions.
7. Add Mock Service Worker and realistic typed mock records.
8. Build the request register.
9. Build request creation.
10. Build request details.
11. Build a basic quotation.
12. Build a basic order.
13. Test the full thin journey.
14. Expand into Service Administration.
15. Continue through the remaining phases.
```

This order gives the project a stable base and proves the important architecture before the codebase becomes large.

---

# 52. Final Project Statement

I am not rebuilding the prototype by copying its HTML into React.

I am using the prototype to understand the product, the business records, the user journeys, and the design direction.

The production application will be a modular, typed, tested, permission-aware, API-driven system.

TanStack will provide clear ownership for routing, backend state, forms, tables, large rendering workloads, and selected execution timing.

The work will be delivered in phases. Each phase will have a clear goal, deliverables, tests, and exit criteria. Shared standards will be established before several different implementations appear.

The main outcome is a system that can take a service from configuration to client request, commercial approval, payment, execution, delivery, acceptance, feedback, reporting, and audit in one connected and understandable process.

That is what I am building.

---

# 53. Reference Notes

This plan is based on:

- the Bomach Service Operations HTML prototype;
- the Service Operations functional overview already prepared;
- the current React, TypeScript, Vite, Tailwind CSS, TanStack Query, and ESLint project foundation;
- the agreed TanStack-first architecture discussion;
- official TanStack guidance for Router, Query, Form, Table, Virtual, Pacer, Store, and DB.

Library APIs and package maturity can change. Before implementation begins for a new TanStack package, its current official documentation and migration notes should be checked, and versions should be pinned through the project lockfile.

## Official Technical References

- [TanStack Router — File-Based Routing](https://tanstack.com/router/latest/docs/routing/file-based-routing)
- [TanStack Router — Type Safety](https://tanstack.com/router/latest/docs/guide/type-safety)
- [TanStack Router — Search Parameters](https://tanstack.com/router/latest/docs/guide/search-params)
- [TanStack Router — Installation with Vite](https://tanstack.com/router/latest/docs/installation/with-vite)
- [TanStack Query — React Documentation](https://tanstack.com/query/latest/docs/framework/react/overview)
- [TanStack Query — Devtools](https://tanstack.com/query/latest/docs/react/devtools)
- [TanStack Form — React Quick Start](https://tanstack.com/form/latest/docs/framework/react/quick-start)
- [TanStack Form — Form Composition](https://tanstack.com/form/latest/docs/framework/react/guides/form-composition)
- [TanStack Table — Overview](https://tanstack.com/table/latest/docs/overview)
- [TanStack Table — Pagination](https://tanstack.com/table/latest/docs/guide/pagination)
- [TanStack Virtual — Virtualizer](https://tanstack.com/virtual/latest/docs/api/virtualizer)
- [TanStack Pacer — Overview](https://tanstack.com/pacer/latest/docs/overview)
- [TanStack Store — Overview](https://tanstack.com/store/latest/docs/overview)
- [TanStack DB — Overview](https://tanstack.com/db/latest/docs/overview)
