# UI-2.05 and UI-2.06 — Completion

The quotation stage is complete after adding:

- quotation-eligible request filtering;
- builder validation and financial constraints;
- separate approval and sending states;
- client decision notes with mandatory rejection reason;
- visible activity/audit history;
- lifecycle and validation tests;
- request synchronization when a quotation is sent, accepted or rejected.

## Final lifecycle

```text
Draft
→ Awaiting Approval
→ Approved
→ Sent
→ Accepted / Rejected
```

## State ownership

- TanStack Query owns saved requests and quotations.
- TanStack Form owns unsaved quotation values.
- React state owns modal visibility and decision-note UI state.
- MSW simulates backend persistence and lifecycle transitions.

## Validation

```text
npm run format
npm run check
npm run test -- --run
npm run build:storybook
```
