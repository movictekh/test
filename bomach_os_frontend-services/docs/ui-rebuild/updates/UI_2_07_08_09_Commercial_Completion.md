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
