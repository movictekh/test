# UI-2.05 and UI-2.06 — Quotation Flow

## UI-2.05 — Quotation Register and Builder

Turns eligible Service Requests into structured commercial offers.

Implemented:

- quotation KPIs and register;
- search and status filtering;
- eligible request selection;
- request-prefilled line items;
- multiple line items;
- quantity, unit and unit price;
- live subtotal, discount, tax and total;
- deposit, validity, payment terms, delivery terms and exclusions;
- TanStack Form draft state;
- Query mutation/cache update;
- MSW persistence;
- originating request status and estimated-value synchronization.

## UI-2.06 — Quotation File and Lifecycle

Manages a quotation after the draft is created.

Implemented:

- quotation detail file;
- line items and totals;
- terms and version metadata;
- lifecycle activity trail;
- submit for approval;
- approve;
- issue to client;
- record acceptance;
- record rejection;
- client decision notes;
- originating request lifecycle updates.

## Lifecycle

```text
Service Request
→ Draft Quotation
→ Pending Approval
→ Approved
→ Issued
→ Accepted / Rejected
```

Issued quotations move the request to `Client Approval`.

Accepted quotations move the request to `Converted`, ready for invoice and order
creation.

Rejected quotations move the request to `Rejected` for commercial follow-up.

## State ownership

- TanStack Query: saved requests and quotations;
- TanStack Form: unsaved quotation builder;
- React state: modal visibility and selected IDs;
- MSW: backend lifecycle simulation.

## Validation

```text
npm run format
npm run check
npm run build:storybook
```
