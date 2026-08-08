# API-0 — Auth Landing and Dashboard Contract Notes

## 1. Staff role bootstrap

The frontend staff bootstrap is:

```text
POST /auth/login
    ↓
tokens
    ↓
GET /auth/me
    ↓
GET /roles/employees/{user.id}
    ↓
map role permissions into AuthUser
```

The backend protects:

```text
GET /roles/employees/{user_id}
```

with:

```python
@require_permission("roles", "view", owner_lookup="user")
```

This means a caller needs either:

```text
roles.view
```

or, for their own employee record:

```text
roles.view_own
```

plus the backend ownership check.

`employees.view_own` is a valid backend self-profile permission, but it is **not**
checked by this particular role-bootstrap endpoint.

### Missing role bootstrap permission

If a staff user has neither `roles.view` nor `roles.view_own`:

```text
login credentials accepted
    ↓
tokens issued
    ↓
/auth/me succeeds
    ↓
/roles/employees/{own id} returns 403
    ↓
frontend converts 403 to AuthAccessError(role-access-denied)
    ↓
login bootstrap fails
    ↓
AuthProvider clears the half-created session
    ↓
LoginForm shows an Access denied message
```

This behavior is intentional for the current backend contract.

Longer term, an authenticated session endpoint that returns the user's own role
and permissions directly could remove the need for a normal role permission just
to discover authorization context. That is a backend design improvement, not an
API-0 frontend requirement.

## 2. `dashboard.view`

`dashboard.view` is a real backend permission in `PERMISSIONS_MAP`.

It is verified on the Operations dashboard statistics endpoint.

For the current frontend:

```text
Command Center navigation -> dashboard.view
Command Center route      -> dashboard.view
```

This remains the intended gate.

`dashboard.view` is **not** a mandatory login permission. A staff user without it
must simply land on the first workspace they are actually allowed to open.

The Service Operations Command Center live data contract is not wired yet. This
document does not attempt to choose or integrate a Command Center backend
endpoint.

## 3. Backend `/dashboard` routing ambiguity

The API registry mounts multiple routers under `/dashboard`.

In particular, both HR and Operations define:

```text
GET /dashboard/stats
```

The authorization is inconsistent:

```text
HR /dashboard/stats
    -> no explicit require_permission decorator

Operations /dashboard/stats
    -> require_permission("dashboard", "view")
```

This is a backend route/contract ambiguity and should be resolved by giving the
domains unambiguous routes, for example:

```text
/hr/dashboard/...
/operations/dashboard/...
```

The frontend must not guess which duplicate route owns the Service Operations
Command Center contract.

## 4. Backend `/stats` concepts

There are also multiple stats concepts.

The Service stats endpoint is verified as:

```text
GET /stats
requires stats.view
```

and returns Service aggregate totals such as services, orders, quotes and
invoices.

A separate user stats router exposes:

```text
GET /stats/dashboard
```

without the same explicit `stats.view` decorator.

Therefore:

```text
stats.view
```

is a real backend permission, but it must not be treated as a universal
permission for every endpoint whose path or payload contains "stats".

## 5. Authenticated landing rule

The frontend no longer assumes every staff user can open Command Center.

Landing is derived from the same permission-aware navigation contract used by
the sidebar and route guards:

```text
dashboard.view?
    yes -> /app/dashboard

otherwise first permitted navigation item
```

Example Service Administrator:

```text
roles.view_own
services.create
services.view
services.list
services.update
services.delete
```

without `dashboard.view`:

```text
login succeeds
    ↓
role bootstrap succeeds
    ↓
Command Center skipped
    ↓
Service Catalogue is first permitted workspace
    ↓
/app/service-catalogue
```

A requested login redirect is also permission-checked. An unauthorized
`/app/dashboard` redirect cannot force the user into a Forbidden loop.

## 6. Forbidden and browser-back behavior

The Forbidden page now returns the user to the first workspace they can actually
open instead of hard-coding `/app/dashboard`.

If an authenticated user navigates back to `/login`, the login route redirects
them to a permitted workspace instead of displaying a second login form.

If an authenticated user has no visible workspace permission at all, the
Forbidden page offers sign-out rather than looping to another forbidden route.
