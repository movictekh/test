# Authentication API Contract Verification

## Source

Verified against the backend auth API catalog and live test results generated on 2026-08-07.

The catalog reports 70 expected-status matches and 0 mismatches across 70 live auth/role cases.

## API-0.03 — Auth contract and staff-session bootstrap

Status: complete for the documented auth contract.

Canonical frontend paths are defined in:

```text
src/shared/auth/auth-endpoints.ts
```

Verified endpoints include:

- POST `/auth/login`
- POST `/auth/verify-2fa`
- GET `/auth/2fa/status`
- POST `/auth/2fa/enable`
- POST `/auth/2fa/disable`
- POST `/auth/logout`
- POST `/auth/refresh`
- POST `/auth/forgot-password`
- POST `/auth/reset-password`
- GET `/auth/me`
- GET `/auth/verify-token`
- GET `/roles/employees/{user_id}`
- GET `/roles/permissions-map`
- GET `/roles/me/authority-limits`

`env.apiBaseUrl` remains responsible for the `/api/v1` prefix.

### Staff bootstrap

```text
login / restored token
→ GET /auth/me
→ GET /roles/employees/{user.id}
→ map role + permissions
→ AuthUser
```

The role endpoint path parameter is `User.id`, not `Employee.id`.

### Valid login but unusable staff workspace

The backend explicitly allows login to succeed before staff-role bootstrap succeeds.

The frontend now distinguishes:

- employee profile missing;
- employee role missing;
- role access denied.

These are authorization/bootstrap issues and redirect to the forbidden surface instead of being misclassified as an unauthenticated login state.

### DTO corrections

Role branch items use:

```json
{ "id": 1, "branch_name": "..." }
```

not `name`.

### Refresh behavior

The backend does not rotate refresh tokens. Logout blacklists the access token only; the frontend therefore still clears both local tokens on logout.

The backend currently accepts refresh JWTs as Bearer tokens on protected routes because it does not enforce token_type. The frontend intentionally does not rely on that quirk and continues to exchange refresh tokens only through `/auth/refresh`.

## API-0.04 — Permission contract bridge

Status: complete as an extensible, fail-closed translation layer.

The backend permission model is:

```text
resource -> [actions]
```

and uses backend-specific names such as:

```text
orders.view
orders.list
service_requests.view
service_requests.list
service_requests.create
```

The frontend uses product capabilities such as:

```text
order.read
request.read
request.create
```

### Verified mappings

| Backend capability        | Frontend capability |
| ------------------------- | ------------------- |
| `orders.view`             | `order.read`        |
| `orders.list`             | `order.read`        |
| `service_requests.view`   | `request.read`      |
| `service_requests.list`   | `request.read`      |
| `service_requests.create` | `request.create`    |

The bridge deduplicates mappings, so both `orders.view` and `orders.list` grant only one `order.read`.

### Fail-closed rule

Unknown or currently irrelevant backend capabilities remain visible in `backendPermissions` but do not grant frontend access.

No resource/action aliases should be invented.

The supplied permissions-map output intentionally omits 96 additional resources. Therefore mappings for quotations, invoices, payments, approvals, tasks, deliverables, reports, and other modules must be added only when their backend module contract or real role payload is reviewed during that module's API integration.

### MSW compatibility

Existing MSW role fixtures still use canonical frontend permission strings. The mapper temporarily accepts those exact known application permissions so local development remains functional.

MSW fixtures should be migrated toward real backend permission shapes module-by-module as their APIs are connected.
