# ADR 0001: Modular Monolith First, Selective Services Later



## Context

The Bomach backend is a Django/Django Ninja application containing multiple substantial
business domains. The current codebase has grown organically, and Python/Django app
boundaries no longer consistently match business-domain ownership.

The team has discussed microservices and gRPC. At the same time, existing features and API
contracts are in active use and must not be rewritten merely to reorganize the codebase.

The current problems include:

- the `user` app owning many unrelated business concerns;
- root API composition living under `user.api`;
- direct cross-domain model access;
- ambiguous ownership of financial and CRM concepts;
- duplicate/overlapping legacy and modern concepts;
- large Swagger/API composition;
- potential circular package dependencies created by composition placement.

## Decision

Reorganize the backend as a **modular monolith first**.

The source tree will be organized around explicit business domains and platform capabilities.
Cross-domain writes should move toward explicit owner-controlled services/public interfaces.
Application composition will live outside business domains.

The reorganization may physically move Python implementations while preserving existing
Django app labels, database tables, migration history, permissions and public API behavior
during the transition.

Microservices will not be introduced merely to improve folder organization.

A bounded context may later be extracted into a service only when there is concrete evidence
for independent deployment, scaling, team ownership, security/fault isolation, technology
requirements, or another material operational benefit.

gRPC is considered a possible future synchronous service-to-service transport after a
component is genuinely deployed separately. It is not an internal replacement for normal
same-process Python calls.

## Consequences

### Benefits

- clearer business ownership;
- reduced cognitive load;
- safer incremental migration;
- easier testing and onboarding;
- smaller API composition units;
- explicit seams for future service extraction;
- no immediate distributed-system operational burden.

### Costs

- temporary compatibility imports may exist;
- Django model source ownership and app-label ownership may differ during transition;
- documentation and architecture enforcement are required;
- some duplicate concepts must remain until their consumers/data are fully understood.

## Non-goals

This initiative does not:

- rewrite working legacy features;
- change public endpoint paths by default;
- rename permission keys by default;
- split the database by default;
- introduce gRPC between modules in the same process;
- force every Django model into a new app immediately;
- delete legacy models without usage/data analysis.

## Validation

Each migration step must preserve runtime behavior and pass appropriate Django checks,
migration-state checks, tests, and API contract verification.
