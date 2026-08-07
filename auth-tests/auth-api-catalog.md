# Auth API catalog & live test results

Generated: **2026-08-07 15:09:25 UTC**  
Base URL: `http://127.0.0.1:8000`  
Live cases: **70 matched expected status**, **0 mismatched** (of 70).

## How to re-run

```bash
cd bomach_os_backend
# server must already be running on :8000
.venv/bin/python scripts/test_auth_endpoints.py
```

## Demo users (seeded/reset by the script)

| Key | Email | Password | Flags |
|-----|-------|----------|-------|
| `active` | `auth.demo.active@bomach.test` | `AuthTestPass123!` | employee+role (id=1) |
| `inactive` | `auth.demo.inactive@bomach.test` | `AuthTestPass123!` | inactive (id=2) |
| `twofa` | `auth.demo.2fa@bomach.test` | `AuthTestPass123!` | 2FA, no employee profile (id=3) |
| `peer` | `auth.demo.peer@bomach.test` | `AuthTestPass123!` | employee+role (peer) (id=4) |
| `norole` | `auth.demo.norole@bomach.test` | `AuthTestPass123!` | employee, no role (id=5) |

Demo role name: `Auth Demo Staff` with permissions: `{"roles": ["view_own"], "employees": ["view_own", "update_own"], "employee_documents": ["view_own", "list_own", "upload_own"], "orders": ["view", "list"], "service_requests": ["view", "list", "create"]}`.

## Shared auth / JWT errors (`JWTAuthenticator`)

Header: `Authorization: Bearer <access_token>`

| Condition | Status | Body |
|-----------|--------|------|
| Missing `Authorization` header | 401 | `{"detail":"Unauthorized"}` |
| Blacklisted (logged out) | 401 | `{"detail":"You are logged out. Try to login again."}` |
| User id missing in DB | 401 | `{"detail":"Invalid or expired session"}` |
| User `is_active=false` | 401 | `{"detail":"User account is inactive"}` |
| JWT expired | 401 | `{"detail":"Token has expired. Try to login again."}` |
| JWT invalid/malformed | 401 | `{"detail":"Invalid token. Try to login again."}` |
| `on_auth_fail` (legacy path) | 403 | plain text: `Failed to authenticate! or maybe you requested for a password change.` |

Error schema used by handlers: `{"detail": "<string>"}`.

Quirks worth handling in the client:
- Missing Bearer → **401 JSON** `Unauthorized` in practice (not always the 403 plain-text `on_auth_fail` path).
- Authenticator does **not** require `token_type == "access"` — a refresh JWT may work on protected routes.
- Logout blacklists **access** only; refresh is client-managed.
- There is **no public register** endpoint — users are provisioned via employees/clients/shareholders APIs.

## Staff post-auth bootstrap

After a successful login (tokens issued):

1. `GET /api/v1/auth/me` → user profile (`id`, email, names, …)
2. `GET /api/v1/roles/employees/{user.id}` → assigned **Role** including full `permissions` map
3. (optional) `GET /api/v1/roles/me/authority-limits` → same grants, flattened with labels
4. (optional) `GET /api/v1/roles/permissions-map` → all possible resources/actions (not user-specific)

Role-guard errors from `@require_permission` (JSON `{"detail": "..."}`):

| Condition | Status | detail |
|-----------|--------|--------|
| No `employee_profile` on user | 403 | `Employee profile not found.` |
| Employee has `role=null` | 403 | `No role assigned.` |
| Missing resource/action on role | 403 | `You do not have permission to perform this action.` |
| `view_own` but object owned by someone else | 403 | `You do not have permission to access this resource.` |


---

## Endpoints

### `POST /api/v1/auth/login`

**Auth:** None  
**Purpose:** Authenticate with email + password. Issues JWTs, or a 2FA session if enabled.

#### Request

```json
{
  "email": "string (must match ^[^@]+@[^@]+\.[^@]+$, lowercased)",
  "password": "string (min_length=1)"
}
```

#### Possible success responses

```json
200 — no 2FA
{
  "success": true,
  "access_token": "<jwt>",
  "refresh_token": "<jwt>",
  "user_id": 1,
  "detail": "Login successful"
}
```

```json
200 — 2FA required
{
  "success": true,
  "requires_2fa": true,
  "session_token": "<2fa_session jwt, ~10 min>",
  "detail": "A verification code has been sent to your email"
}
```

#### Possible error responses

- `401 {"detail": "Invalid credentials"}`
- `401 {"detail": "User account is inactive"}  // rare on login; Django usually returns Invalid credentials`
- `500 {"detail": "Failed to send verification email"}  // 2FA email exception`
- `500 {"detail": "Error creating verification code: …"}`
- `422 {"detail": "<validation message>"}  // bad email / missing fields / empty password`

#### Frontend handling notes

Branch on `requires_2fa === true` before storing tokens. On 401 show a generic invalid-credentials message (do not reveal whether email exists). On 422 show field validation. Persist nothing until tokens are issued.

#### Live observations from this run

##### login success (no 2FA) — `200` [PASS]

_Returns access + refresh JWTs when two_factor_enabled=false._

Request:

```http
POST /api/v1/auth/login
Content-Type: application/json
```

```json
{
  "email": "auth.demo.active@bomach.test",
  "password": "AuthTestPass123!"
}
```

Response `200`:

```json
{
  "success": true,
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2l…[truncated]",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2l…[truncated]",
  "user_id": 1,
  "detail": "Login successful"
}
```

##### login wrong password — `401` [PASS]

Request:

```http
POST /api/v1/auth/login
Content-Type: application/json
```

```json
{
  "email": "auth.demo.active@bomach.test",
  "password": "wrong-password"
}
```

Response `401`:

```json
{
  "detail": "Invalid credentials"
}
```

##### login unknown email — `401` [PASS]

Request:

```http
POST /api/v1/auth/login
Content-Type: application/json
```

```json
{
  "email": "nobody@bomach.test",
  "password": "AuthTestPass123!"
}
```

Response `401`:

```json
{
  "detail": "Invalid credentials"
}
```

##### login invalid email format — `422` [PASS]

_Pydantic validation — middleware usually flattens to {detail: str}._

Request:

```http
POST /api/v1/auth/login
Content-Type: application/json
```

```json
{
  "email": "not-an-email",
  "password": "AuthTestPass123!"
}
```

Response `422`:

```json
{
  "detail": "Value error, Invalid email format"
}
```

##### login missing password — `422` [PASS]

Request:

```http
POST /api/v1/auth/login
Content-Type: application/json
```

```json
{
  "email": "auth.demo.active@bomach.test"
}
```

Response `422`:

```json
{
  "detail": "Field required"
}
```

##### login empty password — `422` [PASS]

_password min_length=1_

Request:

```http
POST /api/v1/auth/login
Content-Type: application/json
```

```json
{
  "email": "auth.demo.active@bomach.test",
  "password": ""
}
```

Response `422`:

```json
{
  "detail": "String should have at least 1 character"
}
```

##### login email case normalization — `200` [PASS]

_Email is lowercased by LoginRequest validator._

Request:

```http
POST /api/v1/auth/login
Content-Type: application/json
```

```json
{
  "email": "AUTH.DEMO.ACTIVE@BOMACH.TEST",
  "password": "AuthTestPass123!"
}
```

Response `200`:

```json
{
  "success": true,
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2l…[truncated]",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2l…[truncated]",
  "user_id": 1,
  "detail": "Login successful"
}
```

##### login inactive account — `401` [PASS]

_Observed: usually 'Invalid credentials' because authenticate() returns None for is_active=False. 'User account is inactive' is returned by JWTAuthenticator on protected routes._

Request:

```http
POST /api/v1/auth/login
Content-Type: application/json
```

```json
{
  "email": "auth.demo.inactive@bomach.test",
  "password": "AuthTestPass123!"
}
```

Response `401`:

```json
{
  "detail": "Invalid credentials"
}
```

##### login requires 2FA — `200` [PASS]

_When two_factor_enabled=true: {requires_2fa, session_token}. If email send raises → 500 Failed to send verification email._

Request:

```http
POST /api/v1/auth/login
Content-Type: application/json
```

```json
{
  "email": "auth.demo.2fa@bomach.test",
  "password": "AuthTestPass123!"
}
```

Response `200`:

```json
{
  "success": true,
  "requires_2fa": true,
  "session_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2l…[truncated]",
  "detail": "A verification code has been sent to your email"
}
```

##### login (setup for refresh) — `200` [PASS]

Request:

```http
POST /api/v1/auth/login
Content-Type: application/json
```

```json
{
  "email": "auth.demo.active@bomach.test",
  "password": "AuthTestPass123!"
}
```

Response `200`:

```json
{
  "success": true,
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2l…[truncated]",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2l…[truncated]",
  "user_id": 1,
  "detail": "Login successful"
}
```

##### login (setup for role/permissions) — `200` [PASS]

Request:

```http
POST /api/v1/auth/login
Content-Type: application/json
```

```json
{
  "email": "auth.demo.active@bomach.test",
  "password": "AuthTestPass123!"
}
```

Response `200`:

```json
{
  "success": true,
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2l…[truncated]",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2l…[truncated]",
  "user_id": 1,
  "detail": "Login successful"
}
```

##### login user without employee profile — `200` [PASS]

Request:

```http
POST /api/v1/auth/login
Content-Type: application/json
```

```json
{
  "email": "auth.demo.2fa@bomach.test",
  "password": "AuthTestPass123!"
}
```

Response `200`:

```json
{
  "success": true,
  "requires_2fa": true,
  "session_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2l…[truncated]",
  "detail": "A verification code has been sent to your email"
}
```

##### login user without employee profile (2FA off) — `200` [PASS]

Request:

```http
POST /api/v1/auth/login
Content-Type: application/json
```

```json
{
  "email": "auth.demo.2fa@bomach.test",
  "password": "AuthTestPass123!"
}
```

Response `200`:

```json
{
  "success": true,
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2l…[truncated]",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2l…[truncated]",
  "user_id": 3,
  "detail": "Login successful"
}
```

##### login employee with no role — `200` [PASS]

Request:

```http
POST /api/v1/auth/login
Content-Type: application/json
```

```json
{
  "email": "auth.demo.norole@bomach.test",
  "password": "AuthTestPass123!"
}
```

Response `200`:

```json
{
  "success": true,
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2l…[truncated]",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2l…[truncated]",
  "user_id": 5,
  "detail": "Login successful"
}
```

##### login (fresh for logout) — `200` [PASS]

Request:

```http
POST /api/v1/auth/login
Content-Type: application/json
```

```json
{
  "email": "auth.demo.active@bomach.test",
  "password": "AuthTestPass123!"
}
```

Response `200`:

```json
{
  "success": true,
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2l…[truncated]",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2l…[truncated]",
  "user_id": 1,
  "detail": "Login successful"
}
```

##### login with new password after reset — `200` [PASS]

Request:

```http
POST /api/v1/auth/login
Content-Type: application/json
```

```json
{
  "email": "auth.demo.active@bomach.test",
  "password": "AuthTestPass456!"
}
```

Response `200`:

```json
{
  "success": true,
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2l…[truncated]",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2l…[truncated]",
  "user_id": 1,
  "detail": "Login successful"
}
```

##### login (setup for 2FA toggles) — `200` [PASS]

Request:

```http
POST /api/v1/auth/login
Content-Type: application/json
```

```json
{
  "email": "auth.demo.active@bomach.test",
  "password": "AuthTestPass123!"
}
```

Response `200`:

```json
{
  "success": true,
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2l…[truncated]",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2l…[truncated]",
  "user_id": 1,
  "detail": "Login successful"
}
```

##### login 2fa user → session_token — `200` [PASS]

Request:

```http
POST /api/v1/auth/login
Content-Type: application/json
```

```json
{
  "email": "auth.demo.2fa@bomach.test",
  "password": "AuthTestPass123!"
}
```

Response `200`:

```json
{
  "success": true,
  "requires_2fa": true,
  "session_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2l…[truncated]",
  "detail": "A verification code has been sent to your email"
}
```

##### login (refresh-as-bearer probe) — `200` [PASS]

Request:

```http
POST /api/v1/auth/login
Content-Type: application/json
```

```json
{
  "email": "auth.demo.active@bomach.test",
  "password": "AuthTestPass123!"
}
```

Response `200`:

```json
{
  "success": true,
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2l…[truncated]",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2l…[truncated]",
  "user_id": 1,
  "detail": "Login successful"
}
```

### `POST /api/v1/auth/verify-2fa`

**Auth:** None  
**Purpose:** Complete login after 2FA by submitting session_token + 6-digit email OTP.

#### Request

```json
{
  "session_token": "string (from login requires_2fa response)",
  "code": "string (exactly 6 digits)"
}
```

#### Possible success responses

```json
200
{
  "success": true,
  "access_token": "<jwt>",
  "refresh_token": "<jwt>",
  "user_id": 1,
  "detail": "Two-factor authentication successful"
}
```

#### Possible error responses

- `401 {"detail": "Invalid session token"}`
- `401 {"detail": "Session expired. Please log in again."}`
- `401 {"detail": "User not found"}`
- `400 {"detail": "Verification code not found or expired"}`
- `400 {"detail": "Invalid code"}`
- `400 {"detail": "This code has already been used"}`
- `400 {"detail": "This code has expired"}`
- `400 {"detail": "Too many failed attempts (max 5)"}`
- `422 {"detail": "…"}  // non-digit or wrong length code`

#### Frontend handling notes

On 401 session errors → send user back to login. On 400 Invalid code → keep session_token, let user retry (track attempts client-side too). On too-many / expired → restart login to get a new code.

#### Live observations from this run

##### verify-2fa invalid session — `401` [PASS]

Request:

```http
POST /api/v1/auth/verify-2fa
Content-Type: application/json
```

```json
{
  "session_token": "bad.token",
  "code": "123456"
}
```

Response `401`:

```json
{
  "detail": "Invalid session token"
}
```

##### verify-2fa non-digit code — `422` [PASS]

Request:

```http
POST /api/v1/auth/verify-2fa
Content-Type: application/json
```

```json
{
  "session_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2l…[truncated]",
  "code": "abcdef"
}
```

Response `422`:

```json
{
  "detail": "Value error, Code must be a 6-digit number"
}
```

##### verify-2fa wrong length code — `422` [PASS]

Request:

```http
POST /api/v1/auth/verify-2fa
Content-Type: application/json
```

```json
{
  "session_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2l…[truncated]",
  "code": "12345"
}
```

Response `422`:

```json
{
  "detail": "String should have at least 6 characters"
}
```

##### verify-2fa wrong code — `400` [PASS]

Request:

```http
POST /api/v1/auth/verify-2fa
Content-Type: application/json
```

```json
{
  "session_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2l…[truncated]",
  "code": "000000"
}
```

Response `400`:

```json
{
  "detail": "Invalid code"
}
```

##### verify-2fa success — `200` [PASS]

_Issues normal access + refresh JWTs._

Request:

```http
POST /api/v1/auth/verify-2fa
Content-Type: application/json
```

```json
{
  "session_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2l…[truncated]",
  "code": "165631"
}
```

Response `200`:

```json
{
  "success": true,
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2l…[truncated]",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2l…[truncated]",
  "user_id": 3,
  "detail": "Two-factor authentication successful"
}
```

##### verify-2fa reuse code — `400` [PASS]

Request:

```http
POST /api/v1/auth/verify-2fa
Content-Type: application/json
```

```json
{
  "session_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2l…[truncated]",
  "code": "165631"
}
```

Response `400`:

```json
{
  "detail": "Verification code not found or expired"
}
```

##### verify-2fa expired session — `401` [PASS]

_detail: 'Session expired. Please log in again.'_

Request:

```http
POST /api/v1/auth/verify-2fa
Content-Type: application/json
```

```json
{
  "session_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2l…[truncated]",
  "code": "123456"
}
```

Response `401`:

```json
{
  "detail": "Session expired. Please log in again."
}
```

### `GET /api/v1/auth/2fa/status`

**Auth:** Bearer access  
**Purpose:** Whether the current user has 2FA enabled.

#### Request

```json
(no body)
```

#### Possible success responses

```json
200 {"success": true, "two_factor_enabled": true|false}
```

#### Possible error responses

- `401 JwtAuthenticator failures (see Auth errors)`
- `401 {"detail": "Unauthorized"} when Authorization header missing`

#### Frontend handling notes

Use for settings UI toggle state.

#### Live observations from this run

##### 2fa status (disabled) — `200` [PASS]

Request:

```http
GET /api/v1/auth/2fa/status
Content-Type: application/json
Authorization: Bearer …
```

Response `200`:

```json
{
  "success": true,
  "two_factor_enabled": false
}
```

##### 2fa status (enabled) — `200` [PASS]

Request:

```http
GET /api/v1/auth/2fa/status
Content-Type: application/json
Authorization: Bearer …
```

Response `200`:

```json
{
  "success": true,
  "two_factor_enabled": true
}
```

### `POST /api/v1/auth/2fa/enable`

**Auth:** Bearer access  
**Purpose:** Enable 2FA after confirming password.

#### Request

```json
{"password": "string"}
```

#### Possible success responses

```json
200 {"success": true, "two_factor_enabled": true}
```

#### Possible error responses

- `401 {"detail": "Invalid password"}`
- `400 {"detail": "Two-factor authentication is already enabled"}`
- `401 {"detail": "Unauthorized"} missing auth`

#### Frontend handling notes

Require password re-entry. After success, next login will require OTP.

#### Live observations from this run

##### 2fa enable wrong password — `401` [PASS]

Request:

```http
POST /api/v1/auth/2fa/enable
Content-Type: application/json
Authorization: Bearer …
```

```json
{
  "password": "nope"
}
```

Response `401`:

```json
{
  "detail": "Invalid password"
}
```

##### 2fa enable success — `200` [PASS]

Request:

```http
POST /api/v1/auth/2fa/enable
Content-Type: application/json
Authorization: Bearer …
```

```json
{
  "password": "AuthTestPass123!"
}
```

Response `200`:

```json
{
  "success": true,
  "two_factor_enabled": true
}
```

##### 2fa enable when already on — `400` [PASS]

Request:

```http
POST /api/v1/auth/2fa/enable
Content-Type: application/json
Authorization: Bearer …
```

```json
{
  "password": "AuthTestPass123!"
}
```

Response `400`:

```json
{
  "detail": "Two-factor authentication is already enabled"
}
```

### `POST /api/v1/auth/2fa/disable`

**Auth:** Bearer access  
**Purpose:** Disable 2FA after confirming password.

#### Request

```json
{"password": "string"}
```

#### Possible success responses

```json
200 {"success": true, "two_factor_enabled": false}
```

#### Possible error responses

- `401 {"detail": "Invalid password"}`
- `400 {"detail": "Two-factor authentication is not enabled"}`
- `401 {"detail": "Unauthorized"} missing auth`

#### Frontend handling notes

Same password confirmation pattern as enable.

#### Live observations from this run

##### 2fa disable when already off — `400` [PASS]

_detail: 'Two-factor authentication is not enabled'_

Request:

```http
POST /api/v1/auth/2fa/disable
Content-Type: application/json
Authorization: Bearer …
```

```json
{
  "password": "AuthTestPass123!"
}
```

Response `400`:

```json
{
  "detail": "Two-factor authentication is not enabled"
}
```

##### 2fa disable success — `200` [PASS]

Request:

```http
POST /api/v1/auth/2fa/disable
Content-Type: application/json
Authorization: Bearer …
```

```json
{
  "password": "AuthTestPass123!"
}
```

Response `200`:

```json
{
  "success": true,
  "two_factor_enabled": false
}
```

### `POST /api/v1/auth/logout`

**Auth:** Bearer access  
**Purpose:** Blacklist the current access token.

#### Request

```json
(no body — token from Authorization header)
```

#### Possible success responses

```json
200 {"success": true, "detail": "Logged out successfully"}
```

#### Possible error responses

- `500 {"detail": "Unable to extract token"}`
- `500 {"detail": "Logout failed: …"}`
- `401 auth failures (missing/invalid/blacklisted token)`

#### Frontend handling notes

Always clear local tokens even if logout fails (network). Refresh tokens are NOT blacklisted — drop them client-side.

#### Live observations from this run

##### logout success — `200` [PASS]

_Blacklists the current access token (reason=logout)._

Request:

```http
POST /api/v1/auth/logout
Content-Type: application/json
Authorization: Bearer …
```

Response `200`:

```json
{
  "success": true,
  "detail": "Logged out successfully"
}
```

##### logout without Authorization — `401` [PASS]

_401 {"detail":"Unauthorized"}_

Request:

```http
POST /api/v1/auth/logout
Content-Type: application/json
```

Response `401`:

```json
{
  "detail": "Unauthorized"
}
```

### `POST /api/v1/auth/refresh`

**Auth:** None  
**Purpose:** Exchange a refresh JWT for a new access JWT (no rotation).

#### Request

```json
{"refresh_token": "string"}
```

#### Possible success responses

```json
200
{
  "success": true,
  "access_token": "<new jwt>",
  "detail": "Token refreshed successfully"
}
```

#### Possible error responses

- `401 {"detail": "Invalid or expired refresh token"}`
- `422 validation`

#### Frontend handling notes

On 401 → force re-login. Refresh path does not check the blacklist. Access lifetime ≈ 1000 minutes; refresh ≈ 90 days.

#### Live observations from this run

##### refresh success — `200` [PASS]

_Returns a new access_token only (refresh is not rotated)._

Request:

```http
POST /api/v1/auth/refresh
Content-Type: application/json
```

```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2l…[truncated]"
}
```

Response `200`:

```json
{
  "success": true,
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2l…[truncated]",
  "detail": "Token refreshed successfully"
}
```

##### refresh with garbage token — `401` [PASS]

Request:

```http
POST /api/v1/auth/refresh
Content-Type: application/json
```

```json
{
  "refresh_token": "not.a.jwt"
}
```

Response `401`:

```json
{
  "detail": "Invalid or expired refresh token"
}
```

##### refresh with access token — `401` [PASS]

Request:

```http
POST /api/v1/auth/refresh
Content-Type: application/json
```

```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIstampered"
}
```

Response `401`:

```json
{
  "detail": "Invalid or expired refresh token"
}
```

##### refresh missing field — `422` [PASS]

Request:

```http
POST /api/v1/auth/refresh
Content-Type: application/json
```

```json
{}
```

Response `422`:

```json
{
  "detail": "Field required"
}
```

### `POST /api/v1/auth/forgot-password`

**Auth:** None  
**Purpose:** Create a password-reset OTP and email it.

#### Request

```json
{"email": "string (validated + lowercased)"}
```

#### Possible success responses

```json
200 {"success": true, "detail": "Password reset code sent to your email"}
```

#### Possible error responses

- `404 {"detail": "User with this email not found"}`
- `500 {"detail": "Error creating reset code: …"}`
- `422 invalid email`

#### Frontend handling notes

API reveals whether the email exists (404). Decide product-wise whether to show that. OTP expiry in code is 6000s (~100 min); email copy says 10 minutes.

#### Live observations from this run

##### forgot-password unknown email — `404` [PASS]

Request:

```http
POST /api/v1/auth/forgot-password
Content-Type: application/json
```

```json
{
  "email": "missing@bomach.test"
}
```

Response `404`:

```json
{
  "detail": "User with this email not found"
}
```

##### forgot-password invalid email — `422` [PASS]

Request:

```http
POST /api/v1/auth/forgot-password
Content-Type: application/json
```

```json
{
  "email": "bad"
}
```

Response `422`:

```json
{
  "detail": "Value error, Invalid email format"
}
```

##### forgot-password success — `200` [PASS]

_Email send failures are swallowed — still 200 if OTP was created._

Request:

```http
POST /api/v1/auth/forgot-password
Content-Type: application/json
```

```json
{
  "email": "auth.demo.active@bomach.test"
}
```

Response `200`:

```json
{
  "success": true,
  "detail": "Password reset code sent to your email"
}
```

### `POST /api/v1/auth/reset-password`

**Auth:** None  
**Purpose:** Verify reset OTP and set a new password.

#### Request

```json
{
  "email": "string",
  "code": "string (4–12 chars)",
  "new_password": "string (min_length=8)"
}
```

#### Possible success responses

```json
200 {"success": true, "detail": "Password reset successfully"}
```

#### Possible error responses

- `400 {"detail": "User not found"}`
- `400 {"detail": "Reset code not found or expired"}`
- `400 {"detail": "Invalid code"}`
- `400 {"detail": "This code has already been used"}`
- `400 {"detail": "This code has expired"}`
- `400 {"detail": "Too many failed attempts (max 5)"}`
- `400 {"detail": "Error updating password: …"}`
- `422 password too short / bad email / code length`

#### Frontend handling notes

Only schema min_length=8 is enforced — not Django password validators. After success, redirect to login with the new password.

#### Live observations from this run

##### reset-password wrong code — `400` [PASS]

Request:

```http
POST /api/v1/auth/reset-password
Content-Type: application/json
```

```json
{
  "email": "auth.demo.active@bomach.test",
  "code": "0000",
  "new_password": "AuthTestPass456!"
}
```

Response `400`:

```json
{
  "detail": "Invalid code"
}
```

##### reset-password short password — `422` [PASS]

_new_password min_length=8 (Django AUTH_PASSWORD_VALIDATORS are NOT applied)._

Request:

```http
POST /api/v1/auth/reset-password
Content-Type: application/json
```

```json
{
  "email": "auth.demo.active@bomach.test",
  "code": "717963",
  "new_password": "short"
}
```

Response `422`:

```json
{
  "detail": "String should have at least 8 characters"
}
```

##### reset-password unknown user — `400` [PASS]

Request:

```http
POST /api/v1/auth/reset-password
Content-Type: application/json
```

```json
{
  "email": "ghost@bomach.test",
  "code": "123456",
  "new_password": "AuthTestPass456!"
}
```

Response `400`:

```json
{
  "detail": "User not found"
}
```

##### reset-password success — `200` [PASS]

Request:

```http
POST /api/v1/auth/reset-password
Content-Type: application/json
```

```json
{
  "email": "auth.demo.active@bomach.test",
  "code": "717963",
  "new_password": "AuthTestPass456!"
}
```

Response `200`:

```json
{
  "success": true,
  "detail": "Password reset successfully"
}
```

##### reset-password reuse same code — `400` [PASS]

_Expect 'Reset code not found or expired' or 'already been used'._

Request:

```http
POST /api/v1/auth/reset-password
Content-Type: application/json
```

```json
{
  "email": "auth.demo.active@bomach.test",
  "code": "717963",
  "new_password": "AuthTestPass123!"
}
```

Response `400`:

```json
{
  "detail": "Reset code not found or expired"
}
```

##### reset-password too many attempts — `400` [PASS]

_OTP.verify → 'Too many failed attempts (max 5)'._

Request:

```http
POST /api/v1/auth/reset-password
Content-Type: application/json
```

```json
{
  "email": "auth.demo.active@bomach.test",
  "code": "223313",
  "new_password": "AuthTestPass456!"
}
```

Response `400`:

```json
{
  "detail": "Too many failed attempts (max 5)"
}
```

##### reset-password expired code — `400` [PASS]

_get_valid_code filters expires_at__gt=now → 'Reset code not found or expired'._

Request:

```http
POST /api/v1/auth/reset-password
Content-Type: application/json
```

```json
{
  "email": "auth.demo.active@bomach.test",
  "code": "154344",
  "new_password": "AuthTestPass456!"
}
```

Response `400`:

```json
{
  "detail": "Reset code not found or expired"
}
```

### `GET /api/v1/auth/me`

**Auth:** Bearer access  
**Purpose:** Current user profile snapshot.

#### Request

```json
(no body)
```

#### Possible success responses

```json
200
{
  "id": 1,
  "email": "...",
  "username": "...",
  "first_name": null|"...",
  "last_name": null|"...",
  "phone_number": null|"...",
  "is_verified": false,
  "created_at": "ISO-8601"
}
```

#### Possible error responses

- `404 {"detail": "User not found"}`
- `401 authenticator errors`
- `401 {"detail": "Unauthorized"} missing Authorization`

#### Frontend handling notes

Call after login / on app boot to hydrate session user.

#### Live observations from this run

##### GET /me success — `200` [PASS]

Request:

```http
GET /api/v1/auth/me
Content-Type: application/json
Authorization: Bearer …
```

Response `200`:

```json
{
  "id": 1,
  "email": "auth.demo.active@bomach.test",
  "username": "auth_demo_active",
  "first_name": "Auth",
  "last_name": "Demo",
  "phone_number": null,
  "is_verified": true,
  "created_at": "2026-08-07T14:54:37.429Z"
}
```

##### GET /me missing Authorization — `401` [PASS]

_Observed: 401 {"detail":"Unauthorized"} (Ninja default when Bearer is missing)._

Request:

```http
GET /api/v1/auth/me
Content-Type: application/json
```

Response `401`:

```json
{
  "detail": "Unauthorized"
}
```

##### GET /me invalid token — `401` [PASS]

Request:

```http
GET /api/v1/auth/me
Content-Type: application/json
Authorization: Bearer …
```

Response `401`:

```json
{
  "detail": "Invalid token. Try to login again."
}
```

##### post-auth GET /me (bootstrap step 1) — `200` [PASS]

_Frontend then loads GET /roles/employees/{user.id} with this id._

Request:

```http
GET /api/v1/auth/me
Content-Type: application/json
Authorization: Bearer …
```

Response `200`:

```json
{
  "id": 1,
  "email": "auth.demo.active@bomach.test",
  "username": "auth_demo_active",
  "first_name": "Auth",
  "last_name": "Demo",
  "phone_number": null,
  "is_verified": true,
  "created_at": "2026-08-07T14:54:37.429Z"
}
```

##### use access token after logout — `401` [PASS]

_detail: 'You are logged out. Try to login again.'_

Request:

```http
GET /api/v1/auth/me
Content-Type: application/json
Authorization: Bearer …
```

Response `401`:

```json
{
  "detail": "You are logged out. Try to login again."
}
```

##### protected route with expired access token — `401` [PASS]

_detail: 'Token has expired. Try to login again.'_

Request:

```http
GET /api/v1/auth/me
Content-Type: application/json
Authorization: Bearer …
```

Response `401`:

```json
{
  "detail": "Token has expired. Try to login again."
}
```

##### protected route while user inactive — `401` [PASS]

_detail: 'User account is inactive'_

Request:

```http
GET /api/v1/auth/me
Content-Type: application/json
Authorization: Bearer …
```

Response `401`:

```json
{
  "detail": "User account is inactive"
}
```

##### GET /me with refresh token as Bearer — `200` [PASS]

_Quirk: JWTAuthenticator does not require token_type==access, so a refresh JWT may authenticate successfully._

Request:

```http
GET /api/v1/auth/me
Content-Type: application/json
Authorization: Bearer …
```

Response `200`:

```json
{
  "id": 1,
  "email": "auth.demo.active@bomach.test",
  "username": "auth_demo_active",
  "first_name": "Auth",
  "last_name": "Demo",
  "phone_number": null,
  "is_verified": true,
  "created_at": "2026-08-07T14:54:37.429Z"
}
```

### `GET /api/v1/auth/verify-token`

**Auth:** Bearer (required by global auth)  
**Purpose:** Confirm the Bearer token is still valid.

#### Request

```json
(no body)
```

#### Possible success responses

```json
200 (only reached if authenticator passes)
{
  "success": true,
  "valid": true|false,
  "user_id": 1|null,
  "detail": "Token is valid" | "Token is invalid or expired" | "No token provided"
}
```

#### Possible error responses

- `401 before handler if token missing/invalid (e.g. {"detail":"Unauthorized"})`

#### Frontend handling notes

Because the route uses the global JWTAuthenticator, missing/invalid tokens usually never reach the handler — you get 401 instead of valid=false. Prefer treating any non-200 as unauthenticated.

#### Live observations from this run

##### GET /verify-token valid — `200` [PASS]

_Handler returns 200 with valid=true when JWTAuthenticator already passed._

Request:

```http
GET /api/v1/auth/verify-token
Content-Type: application/json
Authorization: Bearer …
```

Response `200`:

```json
{
  "success": true,
  "valid": true,
  "user_id": 1,
  "detail": "Token is valid"
}
```

##### GET /verify-token missing Authorization — `401` [PASS]

_Same as /me — 401 {"detail":"Unauthorized"} without Bearer._

Request:

```http
GET /api/v1/auth/verify-token
Content-Type: application/json
```

Response `401`:

```json
{
  "detail": "Unauthorized"
}
```

### `GET /api/v1/roles/employees/{user_id}`

**Auth:** Bearer access + Role permission `roles:view` or `roles:view_own`  
**Purpose:** Return the Role assigned to an employee (full permissions map). This is the post-auth call the staff frontend makes after GET /auth/me.

#### Request

```json
(no body) — path param user_id: int (User.id, not Employee.id)
```

#### Possible success responses

```json
200
{
  "id": 1,
  "name": "Auth Demo Staff",
  "branches": [{"id": 1, "branch_name": "..."}],
  "permissions": {
    "roles": ["view_own"],
    "employees": ["view_own", "update_own"],
    "orders": ["view", "list"]
  },
  "created_at": "ISO-8601",
  "updated_at": "ISO-8601"
}
```

#### Possible error responses

- `401 {"detail": "Unauthorized"} / JWT errors`
- `403 {"detail": "Employee profile not found."}`
- `403 {"detail": "No role assigned."}`
- `403 {"detail": "You do not have permission to perform this action."}`
- `403 {"detail": "You do not have permission to access this resource."}  // view_own cross-user`
- `404 {"detail": "…"}  // no Employee for user_id`
- `404 {"detail": "No role assigned to this employee."}  // rare: decorator usually 403 first`

#### Frontend handling notes

Staff session bootstrap: login → store tokens → GET /auth/me → GET /roles/employees/{user.id} → flatten permissions for the UI. Empty branches[] means company-wide scope. Note: schema field is `branch_name` (not `name`).

#### Live observations from this run

##### GET employee role + full permissions (own) — `200` [PASS]

_Primary post-auth permissions payload. Shape: id, name, branches[], permissions {resource: [actions]}, created_at, updated_at. Requires roles:view or roles:view_own._

Request:

```http
GET /api/v1/roles/employees/1
Content-Type: application/json
Authorization: Bearer …
```

Response `200`:

```json
{
  "id": 1,
  "name": "Auth Demo Staff",
  "branches": [],
  "permissions": {
    "roles": [
      "view_own"
    ],
    "employees": [
      "view_own",
      "update_own"
    ],
    "employee_documents": [
      "view_own",
      "list_own",
      "upload_own"
    ],
    "orders": [
      "view",
      "list"
    ],
    "service_requests": [
      "view",
      "list",
      "create"
    ]
  },
  "created_at": "2026-08-07T15:08:08.815Z",
  "updated_at": "2026-08-07T15:08:08.835Z"
}
```

##### GET employee role missing Authorization — `401` [PASS]

Request:

```http
GET /api/v1/roles/employees/1
Content-Type: application/json
```

Response `401`:

```json
{
  "detail": "Unauthorized"
}
```

##### GET employee role unknown user_id — `404` [PASS]

_No Employee with that user_id._

Request:

```http
GET /api/v1/roles/employees/999999
Content-Type: application/json
Authorization: Bearer …
```

Response `404`:

```json
{
  "detail": "Not Found: No Employee matches the given query."
}
```

##### GET another employee's role with only view_own — `403` [PASS]

_check_obj_permission blocks cross-user access when only roles:view_own._

Request:

```http
GET /api/v1/roles/employees/4
Content-Type: application/json
Authorization: Bearer …
```

Response `403`:

```json
{
  "detail": "You do not have permission to access this resource."
}
```

##### GET employee role without employee profile — `403` [PASS]

_require_permission → 403 "Employee profile not found."_

Request:

```http
GET /api/v1/roles/employees/3
Content-Type: application/json
Authorization: Bearer …
```

Response `403`:

```json
{
  "detail": "Employee profile not found."
}
```

##### GET own role when employee has no role assigned — `403` [PASS]

_require_permission → 403 "No role assigned." (decorator runs before view 404)._

Request:

```http
GET /api/v1/roles/employees/5
Content-Type: application/json
Authorization: Bearer …
```

Response `403`:

```json
{
  "detail": "No role assigned."
}
```

### `GET /api/v1/roles/permissions-map`

**Auth:** Bearer access  
**Purpose:** Full catalog of valid resources and actions (PERMISSIONS_MAP) for admin UI grids.

#### Request

```json
(no body)
```

#### Possible success responses

```json
200
{
  "permissions_map": {
    "employees": ["create", "view", "view_own", "list", ...],
    "roles": ["create", "view", "list", "update", "delete", "view_own"],
    "...": ["..."]
  }
}
```

#### Possible error responses

- `401 when unauthenticated`

#### Frontend handling notes

Not the current user's grants — the universe of possible permissions. Use GET /roles/employees/{id} (or /me/authority-limits) for what the user actually has.

#### Live observations from this run

##### GET permissions-map (all valid resources/actions) — `200` [PASS]

_Catalog of every resource→actions pair (checkbox grid source of truth)._

Request:

```http
GET /api/v1/roles/permissions-map
Content-Type: application/json
Authorization: Bearer …
```

Response `200`:

```json
{
  "permissions_map": {
    "employees": [
      "create",
      "view",
      "view_own",
      "list",
      "update",
      "update_own",
      "exit"
    ],
    "employee_documents": [
      "upload",
      "upload_own",
      "view",
      "view_own",
      "list",
      "list_own",
      "delete"
    ],
    "employee_reviews": [
      "create",
      "view",
      "view_own",
      "list",
      "list_own",
      "update",
      "delete"
    ],
    "departments": [
      "create",
      "list",
      "update"
    ],
    "department_units": [
      "create",
      "list",
      "update"
    ],
    "…": "96 more resources omitted"
  }
}
```

##### GET permissions-map missing Authorization — `401` [PASS]

Request:

```http
GET /api/v1/roles/permissions-map
Content-Type: application/json
```

Response `401`:

```json
{
  "detail": "Unauthorized"
}
```

### `GET /api/v1/roles/me/authority-limits`

**Auth:** Bearer access + `roles:view` or `roles:view_own`  
**Purpose:** Current user's role permissions flattened into labeled authority-limit items.

#### Request

```json
(no body)
```

#### Possible success responses

```json
200
{
  "items": [
    {
      "resource": "orders",
      "action": "list",
      "label": "List Orders",
      "helper_text": "List orders."
    }
  ]
}
```

#### Possible error responses

- `401 unauthenticated`
- `403 {"detail": "Employee profile not found."}`
- `403 {"detail": "No role assigned."}`
- `403 {"detail": "You do not have permission to perform this action."}`
- `404 {"detail": "No role assigned to this employee."}`

#### Frontend handling notes

Same grants as the employee role endpoint, but flattened with display labels. Useful for settings / authority UIs; the staff app bootstrap uses /employees/{id}.

#### Live observations from this run

##### GET me/authority-limits (flattened role permissions + labels) — `200` [PASS]

_Same permission set as employee role, flattened with label/helper_text._

Request:

```http
GET /api/v1/roles/me/authority-limits
Content-Type: application/json
Authorization: Bearer …
```

Response `200`:

```json
{
  "items": [
    {
      "resource": "employee_documents",
      "action": "list_own",
      "label": "List Own Employee Documents",
      "helper_text": "List Own employee documents."
    },
    {
      "resource": "employee_documents",
      "action": "upload_own",
      "label": "Upload Own Employee Documents",
      "helper_text": "Upload Own employee documents."
    },
    {
      "resource": "employee_documents",
      "action": "view_own",
      "label": "View Own Employee Documents",
      "helper_text": "View Own employee documents."
    },
    {
      "resource": "employees",
      "action": "update_own",
      "label": "Update Own Employee Profile",
      "helper_text": "Update the signed-in employee profile."
    },
    {
      "resource": "employees",
      "action": "view_own",
      "label": "View Own Employee Profile",
      "helper_text": "View the signed-in employee profile."
    },
    {
      "resource": "orders",
      "action": "list",
      "label": "List Orders",
      "helper_text": "List orders."
    },
    {
      "resource": "orders",
      "action": "view",
      "label": "View Orders",
      "helper_text": "View orders."
    },
    {
      "resource": "roles",
      "action": "view_own",
      "label": "View Own Roles",
      "helper_text": "View Own roles."
    },
    {
      "resource": "service_requests",
      "action": "create",
      "label": "Create Service Requests",
      "helper_text": "Create service requests."
    },
    {
      "resource": "service_requests",
      "action": "list",
      "label": "List Service Requests",
      "helper_text": "List service requests."
    },
    {
      "resource": "service_requests",
      "action": "view",
      "label": "View Service Requests",
      "helper_text": "View service requests."
    }
  ]
}
```

##### GET me/authority-limits missing Authorization — `401` [PASS]

Request:

```http
GET /api/v1/roles/me/authority-limits
Content-Type: application/json
```

Response `401`:

```json
{
  "detail": "Unauthorized"
}
```

##### GET me/authority-limits with no role — `403` [PASS]

_403 "No role assigned."_

Request:

```http
GET /api/v1/roles/me/authority-limits
Content-Type: application/json
Authorization: Bearer …
```

Response `403`:

```json
{
  "detail": "No role assigned."
}
```

---

## Full case index

| Status | Expected | Case | Route |
|--------|----------|------|-------|
| ✓ 200 | 200 | login success (no 2FA) | `POST /api/v1/auth/login` |
| ✓ 401 | 401 | login wrong password | `POST /api/v1/auth/login` |
| ✓ 401 | 401 | login unknown email | `POST /api/v1/auth/login` |
| ✓ 422 | 422 | login invalid email format | `POST /api/v1/auth/login` |
| ✓ 422 | 422 | login missing password | `POST /api/v1/auth/login` |
| ✓ 422 | 422 | login empty password | `POST /api/v1/auth/login` |
| ✓ 200 | 200 | login email case normalization | `POST /api/v1/auth/login` |
| ✓ 401 | 401 | login inactive account | `POST /api/v1/auth/login` |
| ✓ 200 | — | login requires 2FA | `POST /api/v1/auth/login` |
| ✓ 200 | 200 | login (setup for refresh) | `POST /api/v1/auth/login` |
| ✓ 200 | 200 | refresh success | `POST /api/v1/auth/refresh` |
| ✓ 401 | 401 | refresh with garbage token | `POST /api/v1/auth/refresh` |
| ✓ 401 | 401 | refresh with access token | `POST /api/v1/auth/refresh` |
| ✓ 422 | 422 | refresh missing field | `POST /api/v1/auth/refresh` |
| ✓ 200 | 200 | GET /me success | `GET /api/v1/auth/me` |
| ✓ 200 | 200 | GET /verify-token valid | `GET /api/v1/auth/verify-token` |
| ✓ 401 | 401 | GET /me missing Authorization | `GET /api/v1/auth/me` |
| ✓ 401 | 401 | GET /me invalid token | `GET /api/v1/auth/me` |
| ✓ 401 | 401 | GET /verify-token missing Authorization | `GET /api/v1/auth/verify-token` |
| ✓ 200 | 200 | login (setup for role/permissions) | `POST /api/v1/auth/login` |
| ✓ 200 | 200 | post-auth GET /me (bootstrap step 1) | `GET /api/v1/auth/me` |
| ✓ 200 | 200 | GET employee role + full permissions (own) | `GET /api/v1/roles/employees/1` |
| ✓ 401 | 401 | GET employee role missing Authorization | `GET /api/v1/roles/employees/1` |
| ✓ 404 | 404 | GET employee role unknown user_id | `GET /api/v1/roles/employees/999999` |
| ✓ 403 | 403 | GET another employee's role with only view_own | `GET /api/v1/roles/employees/4` |
| ✓ 200 | 200 | login user without employee profile | `POST /api/v1/auth/login` |
| ✓ 200 | 200 | login user without employee profile (2FA off) | `POST /api/v1/auth/login` |
| ✓ 403 | 403 | GET employee role without employee profile | `GET /api/v1/roles/employees/3` |
| ✓ 200 | 200 | login employee with no role | `POST /api/v1/auth/login` |
| ✓ 403 | 403 | GET own role when employee has no role assigned | `GET /api/v1/roles/employees/5` |
| ✓ 200 | 200 | GET permissions-map (all valid resources/actions) | `GET /api/v1/roles/permissions-map` |
| ✓ 401 | 401 | GET permissions-map missing Authorization | `GET /api/v1/roles/permissions-map` |
| ✓ 200 | 200 | GET me/authority-limits (flattened role permissions + labels) | `GET /api/v1/roles/me/authority-limits` |
| ✓ 401 | 401 | GET me/authority-limits missing Authorization | `GET /api/v1/roles/me/authority-limits` |
| ✓ 403 | 403 | GET me/authority-limits with no role | `GET /api/v1/roles/me/authority-limits` |
| ✓ 200 | 200 | login (fresh for logout) | `POST /api/v1/auth/login` |
| ✓ 200 | 200 | logout success | `POST /api/v1/auth/logout` |
| ✓ 401 | 401 | use access token after logout | `GET /api/v1/auth/me` |
| ✓ 401 | 401 | logout without Authorization | `POST /api/v1/auth/logout` |
| ✓ 404 | 404 | forgot-password unknown email | `POST /api/v1/auth/forgot-password` |
| ✓ 422 | 422 | forgot-password invalid email | `POST /api/v1/auth/forgot-password` |
| ✓ 200 | 200 | forgot-password success | `POST /api/v1/auth/forgot-password` |
| ✓ 400 | 400 | reset-password wrong code | `POST /api/v1/auth/reset-password` |
| ✓ 422 | 422 | reset-password short password | `POST /api/v1/auth/reset-password` |
| ✓ 400 | 400 | reset-password unknown user | `POST /api/v1/auth/reset-password` |
| ✓ 200 | 200 | reset-password success | `POST /api/v1/auth/reset-password` |
| ✓ 200 | 200 | login with new password after reset | `POST /api/v1/auth/login` |
| ✓ 400 | 400 | reset-password reuse same code | `POST /api/v1/auth/reset-password` |
| ✓ 400 | 400 | reset-password too many attempts | `POST /api/v1/auth/reset-password` |
| ✓ 400 | 400 | reset-password expired code | `POST /api/v1/auth/reset-password` |
| ✓ 200 | 200 | login (setup for 2FA toggles) | `POST /api/v1/auth/login` |
| ✓ 200 | 200 | 2fa status (disabled) | `GET /api/v1/auth/2fa/status` |
| ✓ 401 | 401 | 2fa enable wrong password | `POST /api/v1/auth/2fa/enable` |
| ✓ 400 | 400 | 2fa disable when already off | `POST /api/v1/auth/2fa/disable` |
| ✓ 200 | 200 | 2fa enable success | `POST /api/v1/auth/2fa/enable` |
| ✓ 400 | 400 | 2fa enable when already on | `POST /api/v1/auth/2fa/enable` |
| ✓ 200 | 200 | 2fa status (enabled) | `GET /api/v1/auth/2fa/status` |
| ✓ 200 | — | login 2fa user → session_token | `POST /api/v1/auth/login` |
| ✓ 401 | 401 | verify-2fa invalid session | `POST /api/v1/auth/verify-2fa` |
| ✓ 422 | 422 | verify-2fa non-digit code | `POST /api/v1/auth/verify-2fa` |
| ✓ 422 | 422 | verify-2fa wrong length code | `POST /api/v1/auth/verify-2fa` |
| ✓ 400 | 400 | verify-2fa wrong code | `POST /api/v1/auth/verify-2fa` |
| ✓ 200 | 200 | verify-2fa success | `POST /api/v1/auth/verify-2fa` |
| ✓ 400 | 400 | verify-2fa reuse code | `POST /api/v1/auth/verify-2fa` |
| ✓ 200 | 200 | 2fa disable success | `POST /api/v1/auth/2fa/disable` |
| ✓ 401 | 401 | verify-2fa expired session | `POST /api/v1/auth/verify-2fa` |
| ✓ 401 | 401 | protected route with expired access token | `GET /api/v1/auth/me` |
| ✓ 401 | 401 | protected route while user inactive | `GET /api/v1/auth/me` |
| ✓ 200 | 200 | login (refresh-as-bearer probe) | `POST /api/v1/auth/login` |
| ✓ 200 | — | GET /me with refresh token as Bearer | `GET /api/v1/auth/me` |

