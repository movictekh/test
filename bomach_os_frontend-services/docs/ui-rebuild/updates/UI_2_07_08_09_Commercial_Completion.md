# UI-2.07, UI-2.08 and UI-2.09 — Commercial Completion

## UI-2.07 — Invoices & Payments

Implemented:

- invoice KPI strip and register;
- accepted-quotation eligibility;
- duplicate-invoice prevention;
- invoice builder with due date and issue state;
- invoice detail file;
- payment allocation;
- payment method, reference, date and note;
- overpayment prevention;
- automatic Issued, Part Paid and Paid state;
- payment history;
- TanStack Query, API and MSW persistence.

## UI-2.08 — Commercial Approval Queue

Implemented:

- pending approval KPIs;
- quotation approval queue;
- high-value visibility;
- accountable requester and approver;
- approval detail;
- mandatory decision note;
- approve and reject actions;
- quotation lifecycle synchronization;
- TanStack Query, API and MSW persistence.

## UI-2.09 — States, Tests and Stage 2 Sign-off

Implemented:

- empty invoice eligibility state;
- empty approval state;
- commercial loading and shared error states;
- accepted/uninvoiced quotation rule;
- payment over-allocation validation;
- invoice status derivation tests;
- quotation lifecycle tests retained;
- dynamic request validation tests retained;
- Stage 2 sign-off documentation.

## Final commercial lifecycle

```text
Service Request
→ Quotation
→ Approval
→ Client Acceptance
→ Invoice
→ Payment
→ Converted request ready for service order
```

## State ownership

- TanStack Query owns the saved commercial workspace.
- TanStack Form owns unsaved request, quotation, invoice and payment values.
- TanStack Router owns section URLs.
- React state owns modal visibility and selected record IDs only.
- MSW simulates backend persistence and transitions.

## Verification

```text
npm run format
npm run check
npm run test -- --run
npm run build:storybook
```

Manual paths:

```text
/app/service-requests
/app/quotations
/app/invoices-payments
/app/approvals
```

## Final governance correction

The Commercial Approval Queue is now the single UI authority for approval decisions.

- creating a quotation directly as `Awaiting Approval` creates a pending approval record;
- submitting a saved Draft for approval creates a pending approval record;
- a pending record is reused instead of duplicated;
- `QuotationDetailWorkspace` no longer exposes a direct Approve action;
- the quotation remains `Awaiting Approval` until `/app/approvals` records the decision;
- approval decisions synchronize the quotation status and audit trail.

## Final Stage 2 acceptance journey

```text
Create Request
→ Prepare Quotation
→ Submit for Approval
→ Approval appears in /app/approvals
→ Approve from Approval Queue
→ Send quotation to client
→ Record client acceptance
→ Create invoice
→ Record partial or full payment
```
