# ADR 0005: Project Operations Owns Its Model Source

- Status: Accepted
- Date: 2026-08-14

## Context

The Project Operations models form one coherent bounded context:

- Project
- Milestone
- Task
- Worksite
- SiteEquipment
- Contract
- Timeline

Their source historically lived in the legacy Django app at `operations/models.py`.

The application still needs the existing Django identity and migration history:

```text
operations.Project
operations.Milestone
operations.Task
operations.Worksite
operations.SiteEquipment
operations.Contract
operations.Timeline
```

## Decision

The real model implementation is owned by:

```text
domains/project_operations/models.py
```

The file remains intentionally singular while the model set is compact and cohesive. We do
not split one coherent model file into many files merely for architectural symmetry.

Each model explicitly retains:

```python
app_label = "operations"
```

so source ownership can move without changing Django app identity.

`operations/models.py` remains a minimal Django identity and import-compatibility shell that
re-exports the domain-owned model classes. It contains no model implementation or business
logic.

Project Operations API routers import their models directly from the domain-owned source.

## Compatibility contract

This move preserves:

- Django model labels;
- database table names;
- fields and relationships;
- model indexes and ordering;
- migration history and state;
- admin imports through `operations.models`;
- public HTTP/OpenAPI behavior.

## Legacy app

The `operations` Django app remains installed because it still owns the current Django app
identity and migrations. That is different from owning the business source implementation.

A future true app-label migration, if worthwhile, must be an explicit separately tested
migration rather than an incidental side effect of source cleanup.

## Empty API artifact

The empty migrated `expenses.py` file was removed. It contained no HTTP operations or business
implementation and therefore did not represent Project Operations ownership.
