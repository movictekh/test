# API-4.02 — Real Estate Management Backend Follow-ups

API-4.02 intentionally accepts a frontend-sequential Property batch as a product decision.

## Frontend batch semantics

The browser creates Property records one at a time through the canonical existing endpoint:

```http
POST /api/v1/estates/{estate_id}/properties
```

The UI keeps an explicit job row for every requested Property:

```text
queued -> creating -> created
                   -> failed
```

A failed item does not cancel subsequent items. Each failed item has an individual Retry command.
Created Property IDs are retained in the in-session job state. Layout, Estate stats and Property
register caches are refreshed after the job.

The batch is deliberately sequential rather than `Promise.all` to limit API pressure and make
progress/recovery deterministic.

## Remaining backend recommendation

A transactional bulk endpoint remains preferable for large permanent production imports because a
browser session can still close halfway through a sequential batch. The frontend workflow makes
partial completion visible but cannot make it atomic.

## Delete behavior

The backend exposes:

```http
DELETE /api/v1/estates/{estate_id}/properties/{property_id}
```

API-4.02 therefore exposes Property delete behind `properties.delete` and an explicit destructive
confirmation.

The backend currently has no verified restriction preventing deletion of sold/reserved property.
This remains a retention/audit risk and should be addressed server-side.

## Estate management

The current Estate create endpoint supports a rich canonical Estate record. API-4.02 creates that
record directly instead of reproducing the old five-field mock.

The frontend intentionally does not pretend Estate creation is atomic with the Property batch.

## Brokerage

API-4.02 uses the real BrokerageListing domain and keeps its two status dimensions separate:

- verification_status: pending / verified / inspection_due
- status: available / sold / off_market

Verification uses the dedicated `/verify` command.

## File assets

The generic upload endpoint exists, but this phase leaves Estate/Brokerage document replacement
out of the primary forms until orphan cleanup/storage lifecycle is defined. The backend can accept
URLs, and a later asset pass can reuse the uploader used by Service Requests/Deliverables.

## Canonical Property domain

API-4.02 continues to use `user.models.estate.Property`, not `services.models.property.Property`.
The duplicate-domain backend issue remains unresolved and should be documented centrally.
