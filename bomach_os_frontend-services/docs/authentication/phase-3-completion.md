# Phase 3 Completion

## Completed

- API-shaped login through MSW or the deployed backend
- current-user loading with TanStack Query
- staff-role and client-profile detection
- two-factor challenge handling
- Bearer access-token support
- automatic access-token refresh
- logout and Query-cache clearing
- protected staff and client layouts
- permission-aware navigation and actions
- forbidden handling
- session-expiry propagation
- safe internal return-route validation
- visible session-expired feedback
- token-storage and authentication integration tests

## Temporary browser storage decision

Until the backend sets the refresh token as a Secure HttpOnly cookie:

- access token is stored in `sessionStorage`;
- refresh token is stored in `localStorage`.

This is temporary. Both remain readable by JavaScript and remain exposed to successful XSS.

The preferred production migration remains:

- access token in memory;
- refresh token in a Secure HttpOnly cookie;
- refresh rotation and server-side revocation or blacklisting.

## Session expiry

A failed refresh or final unauthorized response:

1. clears both tokens;
2. clears authenticated and sensitive Query state;
3. redirects to `/login`;
4. adds `reason=session-expired`;
5. preserves only a validated internal return path;
6. displays a session-expired alert.

Explicit logout does not display the expiry warning.
