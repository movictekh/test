# Project Operations Domain

## Purpose

Project Operations owns structured project execution:

- Project
- Milestone
- Task
- Worksite
- SiteEquipment
- Contract
- Timeline

## API versioning rule

Only the HTTP/API contract is versioned.

```text
domains/project_operations/
├── api/
│   ├── composition.py
│   └── v1/
│       ├── routers/
│       └── schemas/
├── models/       # domain source, not API-versioned
├── services/     # domain source, not API-versioned
├── selectors/    # domain source, not API-versioned
└── public/       # domain source, not API-versioned
```

`v1` represents version 1 of the external HTTP contract. It does not represent version 1 of
the business domain.

If an incompatible HTTP contract is introduced in future, `api/v2/` may be added while both
versions use the same domain services, selectors and models where appropriate.

Do not create empty future API-version directories speculatively.

## Application integration

The current application `/api/v1/` composition integrates this domain through:

```python
from domains.project_operations.api import register_project_operations_v1
```

The domain registration itself does not add another `/v1` prefix. The version URL prefix is
owned by the application URL composition layer.

Therefore the public URLs remain:

```text
/api/v1/projects
/api/v1/tasks
/api/v1/milestones
...
```

not `/api/v1/v1/...`.

## Django model identity

This source move affects the HTTP layer only.

The models continue to use the existing `operations.*` Django labels, migration history and
database tables until their dedicated model-source migration.
