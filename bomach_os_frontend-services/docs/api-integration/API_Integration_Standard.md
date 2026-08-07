# Bomach Service Operations — API Integration Standard

## Purpose

This document defines the permanent frontend pattern for integrating Service Operations with backend APIs.

The goal is to make every module follow the same architecture, naming, data-flow, error-handling, permission, testing, and rollout rules.

This is the source of truth for new API work. Historical UI-rebuild documents remain useful for product intent and implementation history, but they do not define runtime API architecture.

---

## 1. Integration principles

### 1.1 Backend owns business truth

The backend owns:

- persistence;
- authorization enforcement;
- business rules;
- workflow state transitions;
- identifiers;
- audit generation where applicable;
- notification generation and recipient decisions;
- validation that protects business invariants.

The frontend may guide the user, disable unavailable controls, validate form usability, and present errors, but it must not become the authoritative business-rule engine.

### 1.2 Frontend owns presentation and interaction

The frontend owns:

- screen composition;
- form state;
- loading, empty, success and error states;
- navigation;
- optimistic or transitional UI where explicitly safe;
- formatting;
- client-side usability validation;
- TanStack Query cache orchestration.

### 1.3 Do not expose backend DTOs directly to UI components

Use this flow:

```text
Backend DTO
    ↓
mapper
    ↓
frontend domain model
    ↓
TanStack Query / mutation
    ↓
screen / workspace
```

Components should consume frontend domain models, not raw backend response objects.

---

## 2. Standard module structure

Use this shape where the module needs all layers:

```text
src/modules/<module>/
├── api/
│   ├── <module>.contracts.ts
│   ├── <module>.api.ts
│   ├── <module>.keys.ts
│   ├── <module>.queries.ts
│   └── <module>.mutations.ts
├── mappers/
│   ├── <module>.mapper.ts
│   └── <module>.mapper.test.ts
├── types/
│   └── <module>.types.ts
├── screens/
├── workspaces/
├── pages/
└── mocks/
```

Not every module needs every file. Do not create empty layers only to match the tree.

### Responsibilities

#### `*.contracts.ts`

Contains backend DTOs and request/response contracts.

Use backend naming here if that is what the API returns, including snake_case.

#### `*.types.ts`

Contains frontend domain types.

Use frontend naming conventions and shapes optimized for application use.

#### `*.mapper.ts`

Converts backend DTOs into frontend domain models.

Mapping is the correct place for:

- snake_case → camelCase;
- backend enum normalization;
- defensive null handling;
- permission-resource aliases;
- date normalization;
- compatibility handling between backend versions.

#### `*.api.ts`

Contains HTTP transport only.

It should:

- call `apiClient`;
- use real backend paths after contract verification;
- accept request types;
- return DTOs or mapped values according to the module pattern;
- avoid React-specific behavior.

It should not:

- show toasts;
- navigate;
- mutate React state;
- contain screen logic.

#### `*.keys.ts`

Owns TanStack Query keys.

Keys must be stable and hierarchical.

Example:

```ts
export const serviceKeys = {
  all: ['services'] as const,
  lists: () => [...serviceKeys.all, 'list'] as const,
  list: (filters: ServiceFilters) => [...serviceKeys.lists(), filters] as const,
  details: () => [...serviceKeys.all, 'detail'] as const,
  detail: (id: string) => [...serviceKeys.details(), id] as const,
}
```

#### `*.queries.ts`

Owns reusable `queryOptions(...)`.

Screens should prefer query definitions rather than rebuilding query configuration repeatedly.

#### `*.mutations.ts`

Use when mutation configuration is reusable or complex.

Simple page-local mutations may remain near their owning page if that keeps the code clearer.

---

## 3. TanStack ownership rules

### TanStack Query

Use TanStack Query for canonical server/async state:

- lists;
- details;
- current authenticated user;
- server-backed configuration;
- mutations;
- refetching;
- loading;
- errors;
- invalidation.

Do not copy canonical server data into long-lived local component state unless there is a specific editing/draft reason.

### TanStack Form

Use TanStack Form for:

- complex forms;
- validation;
- field state;
- dirty state;
- submission lifecycle;
- form reset.

Form values are drafts until the mutation succeeds.

### TanStack Router

Use TanStack Router for:

- route access;
- URL search state;
- record deep links;
- route parameters;
- redirects;
- route-level authorization.

### Local React state

Use local state only for transient UI state such as:

- open/closed modal;
- selected tab when it does not belong in URL state;
- temporary local draft state;
- expanded/collapsed panels.

---

## 4. Canonical mutation flow

All normal server mutations should follow:

```text
TanStack Form / local draft
        ↓
mutation
        ↓
backend
        ↓
success response
        ↓
invalidate or update TanStack Query cache
        ↓
UI re-renders from canonical query state
```

Do not create a second permanent frontend database after the real backend is connected.

---

## 5. Authentication and session integration

Authentication is API-0 because every protected API depends on it.

### API-0.01 — Permission bootstrap race

Status after this change: complete.

Rule:

```text
auth loading
→ do not make a permission decision

auth resolved + authenticated + missing permission
→ forbidden
```

The `/forbidden` route must only represent a real authorization denial, never an unresolved session.

### API-0.02 — Refresh-token-only bootstrap

Status: complete after this change.

Current storage strategy:

```text
access token  → sessionStorage
refresh token → localStorage
```

Required startup behavior:

```text
access token exists
→ load current user

access token missing + refresh token exists
→ refresh access token
→ load current user

neither exists
→ unauthenticated
```

The refresh mechanism belongs in the shared API client so individual feature modules do not implement their own token-refresh logic.

### API-0.03 — Auth contract and hydration

Status: complete against the live-tested backend auth catalog.

Canonical auth paths live in `src/shared/auth/auth-endpoints.ts`.

#### Auth hydration

Canonical authenticated staff hydration:

```text
/auth/me
    ↓
/roles/employees/{user.id}
    ↓
permission mapper
    ↓
AuthUser
    ↓
React Query current-user cache
    ↓
AuthProvider
```

Do not duplicate authenticated user state in Redux or a second global store.

### API-0.04 — Permission contract verification

Status: complete as an extensible, fail-closed backend-to-frontend permission bridge.

Mappings are added only from verified backend module contracts or live role payloads. The initial verified mappings cover `orders` and `service_requests`; other Service Operations mappings are added during their owning API integration.

Frontend permissions are only valid after the backend resource/action vocabulary is verified.

If backend names differ from frontend names, create one explicit mapper.

Do not scatter aliases throughout components.

---

## 6. Permission rules

Frontend permissions control UX only.

Examples:

- navigation visibility;
- action-button availability;
- route access;
- workspace controls.

The backend must independently enforce the same authorization.

Never trust a hidden button as security.

### Loading is not denial

Use this distinction everywhere:

```text
loading / unresolved
≠
forbidden
```

Forbidden means:

```text
authenticated identity resolved
+
permissions resolved
+
required permission absent
```

---

## 7. Mock API vs real API

MSW remains useful for development, tests, disconnected backend work, and deterministic scenarios.

Development mock routes use:

```text
/__mock-api__/*
```

through:

```text
src/mocks/mock-api.ts
```

Real backend integration must not reuse the mock prefix.

When a module is migrated:

1. verify the backend contract;
2. add/update DTO contracts;
3. add/update mapper;
4. point the API adapter at the real backend endpoint;
5. keep MSW handlers only where they remain useful for local development/testing;
6. test both success and failure states.

Do not replace mock paths by guessing real backend URLs.

---

## 8. Error handling

All transport errors should flow through the shared API/error layer.

Use:

```text
apiClient
    ↓
ApiError
    ↓
error presentation helpers
    ↓
screen/workspace state
```

### Required UI states

Every server-backed screen should intentionally support:

- loading;
- empty;
- error;
- populated;
- mutation pending;
- mutation failure;
- mutation success where useful.

Avoid silent failures.

---

## 9. Cache and invalidation rules

Invalidate the narrowest stable query family that guarantees correctness.

Examples:

```text
create service
→ invalidate service lists

update service
→ invalidate service detail + affected lists

record payment
→ invalidate invoice/payment data
→ invalidate commercial lifecycle data
→ invalidate downstream order readiness if required
```

Do not globally clear the entire query cache after ordinary mutations.

Global cache clearing is reserved for events such as logout or invalid session termination.

---

## 10. Record linking

Cross-module links must use canonical record-link helpers.

Do not construct ad-hoc query-string links in every screen.

When backend identifiers replace mock identifiers, record linking must continue to use the backend's canonical IDs.

---

## 11. Notifications

The backend owns notification generation.

Frontend owns:

- notification list query;
- unread state presentation;
- mark-read mutation;
- mark-all-read mutation;
- navigation to the referenced record.

Frontend business mutations must not independently invent duplicate notification records.

Integration begins only after the backend notification contract is verified.

---

## 12. Audit

Audit work remains on hold until the product decision is confirmed.

Do not spend API-integration time expanding audit instrumentation until that decision is resolved.

Existing audit-related code may remain unless it creates a concrete integration problem.

---

## 13. Testing standard

Every API migration should test the important contract boundary.

### Mapper tests

Test:

- normal response;
- optional/null fields;
- enum normalization;
- compatibility aliases;
- unknown values where relevant.

### API tests

Test:

- correct method;
- correct path;
- correct payload;
- success mapping;
- expected error handling.

### Query/mutation tests

Test important cache behavior where it is not obvious.

### Permission tests

Test:

- loading does not redirect to forbidden;
- valid permission allows;
- missing permission denies after auth resolves.

### Integration tests

Protect important business transitions across modules.

---

## 14. Integration rollout order

Follow dependency order:

```text
API-0 — Authentication / Session / Permissions
    ↓
API-1 — Service Administration
    ↓
API-2 — Commercial
    ↓
API-3 — Fulfillment
    ↓
API-4 — Specialized Services
    ↓
API-5 — Feedback / Reports
    ↓
API-6 — Notifications
    ↓
Final end-to-end integration review
```

### Why this order

The product lifecycle is:

```text
Service definition
    ↓
Service request
    ↓
Quotation
    ↓
Approval
    ↓
Invoice
    ↓
Payment
    ↓
Service order
    ↓
Task / Deliverable
    ↓
Feedback / Reporting
```

Integrating in dependency order reduces temporary adapters and duplicate rework.

---

## 15. Per-module integration checklist

Before calling a module integrated, confirm:

- [ ] Backend endpoint documented and verified.
- [ ] Request/response DTOs represented.
- [ ] Frontend domain types remain intentional.
- [ ] Mapper exists where backend and frontend shapes differ.
- [ ] API adapter uses the real endpoint.
- [ ] TanStack Query keys are stable.
- [ ] Queries are canonical.
- [ ] Mutations invalidate/update the correct cache.
- [ ] Loading state works.
- [ ] Empty state works.
- [ ] Error state works.
- [ ] Mutation failure is visible.
- [ ] Permissions match backend vocabulary.
- [ ] Cross-record navigation still works.
- [ ] MSW behavior is retained only where useful.
- [ ] Tests pass.
- [ ] Production build passes.
- [ ] Storybook passes when shared UI is affected.

---

## 16. Definition of complete

A module is not API-complete merely because one GET request works.

API-complete means:

```text
verified contract
+
typed DTOs
+
intentional mapping
+
query/mutation ownership
+
cache correctness
+
permissions
+
states
+
tests
+
working business flow
```

This standard should be reused for every remaining Service Operations API integration.
