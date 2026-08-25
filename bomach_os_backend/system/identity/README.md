# System Identity

`system.identity` owns authentication identity and session security:

- `User`
- `OTPCode`
- `TokenBlacklist`
- authentication HTTP API + schemas
- authentication orchestration (`AuthService`)
- JWT creation/verification (`JWTService`)
- request JWT authentication (`JWTAuthenticator`)

This is a source-ownership move only. Historical Django identities remain:

- `user.User`
- `user.OTPCode`
- `user.TokenBlacklist`

`AUTH_USER_MODEL` remains `user.User`. Existing tables, migrations, endpoint
paths, response contracts, token lifetimes, error strings, audit calls and
legacy Python import paths remain compatible.

The User model currently contains profile/biometric/balance fields in addition
to login identity. This batch does not redesign or split those persisted
fields; that would require a separate data-contract migration.
