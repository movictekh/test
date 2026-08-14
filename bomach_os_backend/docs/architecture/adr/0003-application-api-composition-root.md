# ADR 0003: Application API Composition Belongs to `bomach_backend`

- Status: Accepted
- Date: 2026-08-14

## Context

The global Django Ninja `NinjaAPI` instance previously lived in `user.api`, where it imported
and registered routes from User, HR, Operations, Services, Finance, CRM and other application
areas.

That made the User domain appear to own unrelated business domains and created an artificial
reverse dependency through application composition.

## Decision

Application-wide API composition is permanently owned by:

```text
bomach_backend.api
```

`bomach_backend.urls` imports the API from that module.

`user.api` is a User-domain package only and must not become an application composition root
again.

## Compatibility Contract

The move preserves:

- `/api/v1/`;
- existing endpoint paths and HTTP methods;
- request/response behavior;
- authentication and permission behavior;
- Django model identity;
- migration state;
- database tables.

The health endpoint explicitly preserves its pre-move OpenAPI operation ID
`user_api_health_check`. Moving a Python function must not accidentally change a public API
contract solely because its module path changed.

## Long-term Direction

Domain-level router composition may progressively reduce the number of individual router files
known by `bomach_backend.api`.

That work builds on this decision; the global application composition root remains in
`bomach_backend`.
