# ADR 0004: Project Operations Owns a Versioned HTTP API

- Status: Accepted
- Date: 2026-08-14

## Decision

Project Operations owns its version 1 HTTP contract at:

```text
domains/project_operations/api/v1/
├── routers/
└── schemas/
```

Domain API composition is exposed through:

```python
register_project_operations_v1(api)
```

The old `operations/api/` source tree is removed.

## Versioning boundary

API versioning applies to the transport contract, not the whole business domain.

Therefore future Project Operations business code such as models, services, selectors,
permissions and public interfaces is not placed under `v1`.

A future incompatible HTTP contract may introduce:

```text
domains/project_operations/api/v2/
```

while reusing the same domain business layer where appropriate.

## URL ownership

The application URL layer owns the `/api/v1/` prefix.

The domain `v1` package therefore does not add another version prefix. Existing URLs remain
`/api/v1/projects`, `/api/v1/tasks`, and so on.

## Compatibility

The migration preserves:

- public route paths;
- HTTP methods;
- OpenAPI tags;
- existing OpenAPI operation IDs;
- request/response behavior;
- authentication and permission behavior;
- Django model identity;
- migration state;
- database tables.

Django Ninja operation IDs are explicitly preserved because moving a Python module would
otherwise change generated operation IDs even when the HTTP contract is unchanged.

## Django identity

Project Operations models remain under their existing `operations.*` Django identities until
a dedicated model-source migration is performed.
