# Authentication Implementation

## Backend contract used

The frontend currently integrates these BOMACH endpoints:

- `POST /auth/login`
- `POST /auth/verify-2fa`
- `POST /auth/refresh`
- `POST /auth/logout`
- `GET /auth/me`
- `GET /roles/employees/{user_id}`
- `GET /clients/clients/profile`

The API uses HTTP Bearer JWT authentication.

## Automatic mock and real switching

The same API functions are used in both modes.

### Mock

```env
VITE_API_BASE_URL=/api/v1
VITE_ENABLE_MOCKS=true
```

MSW intercepts the normal HTTP requests and returns responses matching the backend contract.
The mock login handler only accepts the known demo credentials in the repository and returns
`401` for anything else.

### Real

```env
VITE_API_BASE_URL=https://bomachauthtest.bgbot.app/api/v1
VITE_ENABLE_MOCKS=false
```

The same requests reach the deployed backend without changing the UI or feature code.

## Token handling

The backend returns an access token and refresh token. The current frontend stores both in localStorage because the API does not expose an HttpOnly-cookie session contract.

This keeps refresh and browser-reload restoration working, but it also means XSS prevention is important. A future backend improvement should prefer secure HttpOnly refresh cookies where possible.

## User context

`GET /auth/me` returns identity fields but does not include the assigned role or permissions. The frontend therefore loads:

1. the current user;
2. the employee role through `/roles/employees/{user_id}`;
3. or, when no employee role exists, probes `/clients/clients/profile` and treats the account as a client.

The role response contains a permission map. Known frontend permissions are used directly. Existing role defaults remain as a temporary compatibility fallback until the backend permission names and service-module permission names are fully aligned.

## Two-factor authentication

Login can return either tokens or a two-factor challenge. The login card switches to a six-digit verification-code form while keeping the same visual frame.

## Logout

Logout calls the backend, clears tokens, clears TanStack Query data, invalidates Router authentication context, and returns the user to login.
