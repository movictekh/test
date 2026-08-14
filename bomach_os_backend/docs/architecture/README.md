# Bomach Backend Architecture Reorganization

## Status

Architecture assessment and source-organization initiative.


## Why this work exists

The backend is a Django/Django Ninja monolith containing several legitimate business domains,
but the current Python/Django package boundaries no longer match those domains consistently.

The largest example is the `user` Django app, which currently contains or exports identity,
organization, employees, CRM, real estate, legal/compliance, governance, approvals,
notifications, workflow, audit, and legacy client-service concerns.

The goal is therefore **not microservices first**. The goal is:

1. restore clear domain ownership;
2. make dependencies directional and explicit;
3. move source implementation into coherent domain packages;
4. preserve all existing runtime contracts during migration;
5. create clean seams that can support selective service extraction later if justified.

## Architectural direction

The recommended target is a **modular monolith with microservice extraction seams**.

```text
bomach_os_backend/
├── bomach_backend/              # application composition/configuration
├── domains/
│   ├── identity/
│   ├── organization/
│   ├── people/
│   ├── crm/
│   ├── service_operations/
│   ├── project_operations/
│   ├── real_estate/
│   ├── finance/
│   ├── legal_compliance/
│   └── governance/
├── platform/
│   ├── approvals/
│   ├── workflow/
│   ├── notifications/
│   ├── audit/
│   └── files/
├── shared/                      # domain-neutral infrastructure only
├── user/                        # transitional Django compatibility app
├── services/                    # transitional Django compatibility app
├── operations/                  # transitional Django compatibility app
├── finance/                     # transitional Django compatibility app
└── hr/                          # transitional Django compatibility app
```

The exact physical layout may evolve during implementation, but the domain ownership rules
should remain stable.

## Source ownership vs Django identity

A central migration rule is that these are separate concerns:

1. **Python source location** — where implementation lives.
2. **Django app/model identity** — e.g. `user.Estate`.
3. **Database table identity** — e.g. the existing table name.

The first phase may move the Python implementation into a target domain package while
preserving the existing Django app label and database table identity.

Example transition:

```text
Before
  source: user/models/estate.py
  Django identity: user.Estate
  table: existing Estate table

Transition
  source of truth: domains/real_estate/models/estate.py
  compatibility import: user/models/estate.py
  Django identity: user.Estate
  table: unchanged

Later, optional
  Django identity: real_estate.Estate
  table: preserved or deliberately migrated
```

This allows genuine source separation without forcing a destructive or unnecessary database
migration at the same time.

## Compatibility rules

During source reorganization:

- existing API URLs must not change;
- HTTP methods, request bodies, response bodies and status codes must remain compatible;
- permission keys must remain compatible;
- existing Django app labels remain unchanged unless a dedicated migration explicitly changes them;
- existing database table names remain unchanged during pure source moves;
- historical migration imports must remain replayable;
- old Python import paths may temporarily re-export moved implementations;
- new code should import from the target domain package rather than the compatibility path;
- pure source moves must pass `python manage.py makemigrations --check --dry-run` with no unintended model-state changes.

## Dependency rules

### Within a domain

```text
API
 ↓
services / selectors
 ↓
domain models
```

- `services` contain state-changing business operations.
- `selectors` contain complex/reusable read logic.
- API handlers should remain transport-oriented.

### Across domains

- the owning domain controls writes to its business records;
- cross-domain writes should use an owner-provided service/public interface;
- simple direct cross-domain reads may remain temporarily where pragmatic;
- no domain should import another domain's HTTP/router implementation;
- the application composition root may depend on all domains;
- domains must not depend on the application composition root;
- `shared` must not become a home for business logic.

## Business domains

Current target bounded contexts:

- Identity
- Organization
- People / HR
- CRM / Customer
- Service Operations
- Project Operations
- Real Estate
- Finance & Accounting
- Legal & Compliance
- Corporate Governance

Cross-domain platform capabilities:

- Approvals
- Workflow / automation
- Notifications
- Audit trail
- Files / document infrastructure

## Microservices and gRPC

Microservices are **not the immediate reorganization target**.

A domain should be considered for extraction only where there is evidence such as:

- independent team ownership;
- independent deployment requirements;
- materially different scaling requirements;
- clear data ownership;
- a stable domain contract;
- security/fault-isolation requirements;
- operational infrastructure capable of supporting distributed systems;
- benefits that exceed the cost of network failures, observability, consistency and deployment complexity.

gRPC is a possible future synchronous service-to-service transport after a domain is actually
deployed separately. It should not replace normal Python calls between modules that run in
the same Django process.

Domain events and background workers should be considered separately for asynchronous
workflows.

## Reorganization stages

```text
ARCH-0   Architecture inventory
ARCH-0B  Dependency and coupling map
ARCH-1   Formal domain/model ownership
ARCH-2   Architecture and compatibility standards
ARCH-3   Move API composition out of user.api
ARCH-4   Pilot source reorganization on a low-risk domain
ARCH-5   Enforce dependency rules
ARCH-6   Continue logical/source domain migrations
ARCH-7   Structured Service Operations cleanup
ARCH-8   Decompose user god-app source ownership
ARCH-9   Events / async foundation
ARCH-10  Evaluate true Django app moves and selective microservices
```

See `MODEL_OWNERSHIP.md` for the evolving ownership matrix and `adr/` for recorded
architecture decisions.
