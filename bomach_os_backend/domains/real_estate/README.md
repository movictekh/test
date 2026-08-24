# Real Estate Domain

`domains.real_estate` is the canonical Python source owner for Bomach Real Estate.

## Transition identity

Real Estate models historically owned by the installed `user` Django app keep
their existing Django app labels, tables, migrations, permissions, content types,
and foreign-key identities during source modularization.

## Internal layers

- `models/`: persistence models
- `selectors/`: reusable read/query operations
- `services/`: write-side application operations
- `api/v1/routers/`: HTTP adapters
- `api/v1/schemas/`: transport contracts

The API may continue to depend on the existing `user.utils.perm` authorization
infrastructure until the platform/authorization extraction.

## Intentionally deferred to Phase 3

Phase 2 does not change estate-invoice approval or payment behavior. Phase 3 owns:

- multi-item invoice correctness
- approval-flow normalization
- placeholder bank/payment details
- Finance-owned settlement integration
- transactional/concurrency protection for property reservation/sale
- investigation of the separate legacy `services.Property`
