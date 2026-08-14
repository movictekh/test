# ADR 0006: Project Operations Uses Services and Selectors Only Where They Add Value

- Status: Accepted
- Date: 2026-08-14

## Decision

Project Operations introduces two domain-level modules:

```text
domains/project_operations/services.py
domains/project_operations/selectors.py
```

They are deliberately singular modules rather than directories because the current amount of
logic does not justify a deeper package hierarchy.

## Services

`services.py` owns state-changing use cases with meaningful business behavior, currently:

- project creation and employee assignment;
- project update and employee reassignment;
- task creation, milestone resolution, assignment and post-commit assignment email delivery;
- task update and assignment changes;
- owned-task status changes and validation.

## Selectors

`selectors.py` owns reusable/non-trivial reads, currently:

- filtered project queries;
- filtered task queries;
- employee-owned task queries;
- task ownership checks;
- Project Operations dashboard aggregation.

## What stays in routers

Routers continue to own:

- HTTP route declarations;
- request/response schemas;
- permission decorators;
- transport-level status/error mapping;
- simple object lookup/delete behavior where extracting another function would add no useful
  abstraction.

Straightforward CRUD in Milestones, Worksites, Contracts, Timelines and Site Equipment remains
in the routers until there is actual domain logic worth extracting.

## Principle

We do not create services/selectors merely to satisfy a folder pattern. A layer is introduced
when it owns meaningful reusable business or query logic.

## Compatibility

The refactor preserves:

- all public paths and methods;
- OpenAPI operation IDs and tags;
- permission decorators and owner-only permission behavior;
- request/response schemas;
- Django model identity;
- migration state.
