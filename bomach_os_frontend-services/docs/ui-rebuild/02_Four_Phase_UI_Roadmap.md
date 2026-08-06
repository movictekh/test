# Four-Phase Prototype UI Roadmap

## Why four phases

The HTML prototype contains these navigation groups:

- Command;
- Service Administration;
- Commercial Flow;
- Fulfillment;
- Specialized Services;
- Experience & Intelligence.

For implementation, they are consolidated into four coherent delivery phases without removing any prototype feature.

```text
Phase UI-1 — Shell, Command Center, and Service Administration
Phase UI-2 — Commercial Flow
Phase UI-3 — Fulfillment and Specialized Services
Phase UI-4 — Client Experience, Quality, Intelligence, and Governance
```

# Phase UI-1 — Shell, Command Center, and Service Administration

## Prototype areas

- Command Center
- Service Catalogue
- Calculator Library
- Request Form Builder
- Workflow Designer
- Branch Activation

## Shell work

Finish the compact desktop sidebar, collapsed sidebar, mobile navigation, global header, role display, notification surface, global search visual, top page toolbar, title and breadcrumb, global modal host, toast viewport, and responsive content sizing.

## Command Center

Implement the complete prototype screen:

- compact top actions;
- KPI cards;
- service lifecycle;
- requests requiring action;
- executive alerts;
- operations health;
- service performance;
- branch performance;
- recent service activity where retained by final prototype review.

## Service Catalogue

Implement catalogue summaries, filters, service cards/table, service status, divisions, branches, create-service wizard, service detail, edit, publish, activate/deactivate, sub-services, and prototype confirmations.

## Calculator Library

Implement calculator register, service association, variables, charge rows, formulas, preview/test calculation, create, edit, duplicate, activate/deactivate, and delete confirmation.

## Request Form Builder

Implement form register, field library, builder canvas, field settings, ordering, validation, preview, draft/version state, activation, duplication, and deletion.

## Workflow Designer

Implement workflow register, visual stages, stage settings, role ownership, SLA, evidence, approvals, client visibility, ordering, preview, seeding, activation, and versions.

## Branch Activation

Implement summary, service/branch matrix, service-scoped branch view, capacity indicators, active/inactive controls, bulk update, confirmation, and filters.

## Exit criteria

Every Command and Service Administration item opens a complete prototype-matched screen, not a placeholder.

# Phase UI-2 — Commercial Flow

## Prototype areas

- Service Requests
- Quotations
- Invoices & Payments
- Approvals

## Service Requests

Implement request summaries, register, filters, search, status, priority, branch, owner, count badges, create flow, service-driven intake, Request 360, client summary, scope, activity, attachments, assessment details, assignment, status, next action, and linked records.

## Quotations

Implement register, filters, create flow, quote builder, pricing breakdown, discounts, tax, deposit, validity, terms, approval requirements, preview, issue/send, update, duplicate, decision state, and request linkage.

## Invoices & Payments

Implement summaries, invoice and payment registers, invoice detail, invoice creation, line items, payment status, evidence, verification, rejection, balances, overdue state, and receipts shown by the prototype.

## Approvals

Implement summary, pending badge, queue, filters, linked record, value, requester, age, detail surface, approve, reject, comments, confirmation, and decision history.

## Connected mock flow

```text
create request
  → see request in register
  → open Request 360
  → create quotation
  → create invoice/payment state
  → submit approval
  → approve or reject
```

## Exit criteria

The full commercial flow works against coherent mutable mock data.

# Phase UI-3 — Fulfillment and Specialized Services

## Prototype areas

- Service Orders
- Execution Tasks
- Deliverables
- Real Estate Inventory
- Survey / Engineering / Others

## Service Orders

Implement summaries, register, order detail/control room, lifecycle, client/commercial links, assignment, dates, payment readiness, milestones, workflow stages, status changes, hold, cancel, and completion interactions.

## Execution Tasks

Implement summaries, register, filters, assignment, due date, priority, detail, progress, evidence, activity, completion, blocked state, and order/stage links.

## Deliverables

Implement register, order/client links, files, versions, review state, client visibility, approve, reject/revise, completion indicators, and upload flow.

## Specialized Services

Implement estate summary, estate/property registers, plot grid, availability, filters, property details, reservation/allocation, client and document state, pricing, and the specialized survey/engineering control views shown by the prototype.

## Connected mock flow

```text
approved commercial work
  → service order
  → workflow stage
  → task
  → deliverable
  → acceptance/completion
```

## Exit criteria

The prototype’s fulfillment and specialized-service screens are complete and connected.

# Phase UI-4 — Client Experience, Quality, Intelligence, and Governance

## Prototype areas

- Client Portal
- Feedback & Quality
- Reports & Analytics
- Audit Log

## Client Portal

Implement client dashboard, profile, requests, quotations and decisions, invoices/payments, orders, progress, documents, pending actions, responsive shell, and client-safe wording/data.

## Feedback & Quality

Implement summaries, register, ratings, comments, service/client context, quality issues, complaints/corrective actions, status, follow-up, and quality indicators.

## Reports & Analytics

Implement summary, date/branch/division/service filters, prototype charts and tables, exports, drill-downs, and empty states.

## Audit Log

Implement summary, register, actor, role, area, action, timestamp, search, filters, record links, and detail where shown.

## Cross-application completion

Finish realistic notifications, unread state, record links, mark-as-read, global mock search, grouped results, keyboard use, and permission filtering.

## Exit criteria

Every prototype navigation item is implemented and the full application can be demonstrated end to end using mock-backed data.
