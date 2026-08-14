# ADR 0002: Domain Ownership and Dependency Direction

- Status: Proposed
- Date: 2026-08-14

## Context

The current Django app layout no longer represents business ownership accurately.

The `user` app contains identity, organization, people, CRM, real estate, governance, legal,
approvals, notifications, workflow and audit concerns. The `services` app similarly contains
a coherent Service Operations domain plus adjacent Finance/CRM/marketing concerns.

This makes source ownership unclear and creates bidirectional package dependencies.

## Decision

Adopt explicit business-domain ownership with the following primary contexts:

- Identity
- Organization
- People / HR
- CRM
- Service Operations
- Project Operations
- Real Estate
- Finance & Accounting
- Legal & Compliance
- Governance

Adopt the following cross-domain platform capabilities:

- Approvals
- Workflow
- Notifications
- Audit
- Files

Cross-domain dependency rules:

1. the owning domain controls writes to its records;
2. cross-domain writes should use owner-provided services/public interfaces;
3. simple model reads may remain temporarily during migration;
4. domains must not import another domain's HTTP/router implementation;
5. the application composition root may import every domain;
6. no domain may depend on the application composition root;
7. `shared` contains domain-neutral infrastructure only;
8. circular domain-service dependencies are not allowed.

## Key ownership decisions

Initial ownership direction:

```text
Invoice            → Service Operations
Payment            → Finance
PaymentSubmission  → Finance
Budget             → Finance
Expense            → Finance

Project            → Project Operations
Estate/Property    → Real Estate

ApprovalFlow       → Platform / Approvals
WorkflowRule       → Platform / Workflow
Notification       → Platform / Notifications
AuditLog           → Platform / Audit
```

Ambiguous legacy models remain in investigation state until consumers and stored data are mapped.

## Migration strategy

Source code may move into its target domain package while preserving its current Django app
label and database table during the transition.

Compatibility imports may remain temporarily for:

- existing application imports;
- historical migration imports;
- third-party or management-command references.

A later dedicated migration may change true Django app ownership after the source architecture
has stabilized.

## Consequences

### Positive

- clearer ownership;
- less accidental coupling;
- easier onboarding;
- safer future microservice extraction;
- business rules become easier to locate;
- code review can enforce dependency direction.

### Negative

- source ownership and Django app identity may differ temporarily;
- compatibility modules must be maintained during transition;
- some boundaries require staged migration rather than one-time moves.

## Validation

Each structural migration must verify:

- Django checks pass;
- pure source moves do not generate unintended migrations;
- current API paths remain unchanged;
- permission behavior remains unchanged;
- tests remain green;
- historical migration imports continue to resolve.
