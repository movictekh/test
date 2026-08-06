# Mock API and Frontend Contract Standard

## Principle

Mock data is not page decoration. Mock APIs are a temporary frontend backend.

## Required architecture

```text
module/
├── api/
│   ├── module.api.ts
│   ├── module.contracts.ts
│   ├── module.keys.ts
│   ├── module.queries.ts
│   └── module.mutations.ts
├── mocks/
│   ├── module.mock-data.ts
│   ├── module.mock-db.ts
│   └── module.handlers.ts
├── mappers/
├── types/
├── schemas/
├── components/
└── pages/
```

Feature code must call API functions. MSW intercepts those calls in mock mode.

## Mutable mock database

Mutations must update related records. Creating a request must affect the register; creating a quotation must link it to the request; approving commercial work must affect downstream order eligibility; completing tasks must affect order progress.

## Contract classification

Every endpoint must be classified as:

- Verified backend
- Wired, unverified
- Frontend mock contract
- UI-only temporary behaviour

## Error simulation

Handlers should support success, empty, validation, unauthorized, forbidden, not found, conflict, server failure, and delayed responses through explicit development controls.

## Data quality

Use realistic Bomach divisions, services, branches, roles, statuses, dates, and connected totals. Avoid lorem ipsum and real personal data.

## No backend compromise in UI

When the backend lacks a prototype-required field:

1. keep it in the frontend product contract;
2. mock it;
3. document the gap;
4. preserve an adapter seam;
5. reconcile later.
