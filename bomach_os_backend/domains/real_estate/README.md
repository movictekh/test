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

## Phase 3 correctness hardening

- Estate invoices are created as drafts and are not emailed before approval.
- Multi-property line data stays paired with the correct property.
- Submission atomically reserves invoiced properties and creates assigned Manager/Final approval steps once.
- Rejection cancels the invoice and releases the reservation created for that client.
- Final approval marks the invoice `sent`.
- Payment instructions come from an active Finance bank account; placeholder bank details are no longer generated.
- Finance owns receipt posting through an immutable journal; Real Estate owns invoice balance and property status/ownership.
- Same invoice/payment-reference retries are idempotent and overpayment is rejected.
- Properties become `sold` and gain an owner only after full payment.

### Legacy `services.Property`

`services.Property` remains a separate live legacy inventory concept and is not merged, renamed or deleted here. It has a separate `/properties` API and a different data shape from `domains.real_estate.models.Property`. Before consolidation, audit production record counts, foreign keys, frontend/API consumers and ID mapping. That is a later migration project, not part of this boundary cleanup.

## Phase 8 portal-ready purchase UX

The purchase lifecycle now exposes read surfaces designed for both staff UI and
the authenticated client portal without changing settlement ownership.

- Staff can list/filter/search property purchases through the canonical purchase API.
- Frontends can read typed purchase mode/status choices instead of hard-coding labels.
- Purchase responses expose status/mode display labels, outstanding balance,
  payment progress percentage, and whether another payment request is currently valid.
- Authenticated clients can list and read only purchases tied to
  `request.user.client_profile`.
- Client payment history is purpose-scoped through Central Payments and omits raw
  provider metadata, Finance journals, and internal settlement details.
- Clients can request the next Monnify checkout only for their own purchase; the
  existing exact-amount, expiry, idempotency, verified-receipt settlement, and
  transactional-outbox rules remain authoritative.
