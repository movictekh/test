# API-4.01 — Real Estate Foundations Backend Follow-ups

## Scope

API-4.01 replaces the mock Real Estate Inventory read/update foundation with the real Estate and Property APIs.

Implemented now:

- Estate list and search
- Estate detail/profile
- Estate statistics
- Estate plot layout
- Plot quick update
- permission-aware read/write states

Full Estate/Property/Brokerage management is deferred to API-4.02 because of the contract gaps below.

## 1. Estate creation does not create plot inventory

The product flow asks for estate name/location, plot count, plot size and unit price and immediately renders the generated plot grid. `POST /estates/` creates only the Estate record. Plots are separate `Property` rows with `property_type="plot"`.

The frontend must not issue N Property create requests after Estate creation because that is non-atomic, slow and difficult to recover if only part of the batch succeeds.

### Recommendation

Add an atomic backend command such as:

```http
POST /api/v1/estates/with-plots
```

or:

```http
POST /api/v1/estates/{estate_id}/plots/bulk
```

inside one database transaction.

## 2. Plot quick update is inventory metadata, not a property transaction

The current endpoint updates status, `client_name` and price. There is no Reservation, Allocation or Sale record, buyer relationship, payment/invoice link, reservation expiry, release event or transaction history.

The frontend therefore uses the wording **Save Plot Inventory**, not **Save Plot Transaction**.

### Recommendation

Introduce structured Property Reservation / Allocation / Sale records and connect them to the canonical Client and financial modules.

## 3. `client_name` is free text

The platform already has a canonical Client model, but Estate Plot allocation currently stores only a free-text holder name.

### Recommendation

Add a nullable Client relationship with an optional display-name snapshot when required.

## 4. Plot lifecycle has no explicit domain commands

Plot status can move directly between `not-for-sale`, `available`, `reserved`, `sold` and `hold` through generic update/quick-update.

When financial/allocation behavior is added, prefer explicit server-driven commands such as reserve, release, allocate, sell and hold with transition validation and audit records.

## 5. Sold Property deletion/retention policy is undefined

Property DELETE exists without a verified business-state retention restriction. Sold/allocated Property records should generally not be physically removable once connected to financial or legal records.

## 6. Two independent Property models exist

The repository has both:

1. `user.models.estate.Property`, used by `/estates/...`, Estate layout and Estate stats.
2. `services.models.property.Property`, used by `/properties`.

They have different schemas and semantics.

### Recommendation

Document canonical ownership or consolidate the domains. API-4.01 deliberately uses `user.models.estate.Property`, because it is the domain behind the product's Estate layout and plot inventory.

## 7. Asset upload ownership should be documented before API-4.02

Estate documents, Property images and Brokerage images accept URL/path strings populated through a separate upload flow. A generic `/others/upload-file` endpoint exists, but API-4.02 should not assume long-term asset behavior without documenting size limits, accepted file types, authorization, orphan cleanup, replacement cleanup and tenancy/storage rules.

## 8. Real Estate route should not require Brokerage access

The previous frontend navigation attached `estates.list`, `properties.list` and `brokerage.list` to one menu item. Route checks default to requiring all listed permissions.

API-4.01 changes the route-level requirement to `estates.list`. Inside the live page:

- Estate statistics/detail use `estates.view`.
- Plot layout uses `properties.list`.
- Plot updates use `properties.update`.
- Brokerage permissions will be applied to Brokerage UI in API-4.02.

## 9. Estate list and Estate statistics intentionally have separate permission gates

`GET /estates/` requires `estates.list`, while `/estates/{id}/stats` requires `estates.view`. The frontend does not infer view access from list access.

## 10. Estate layout is a good purpose-built read contract

`GET /estates/{estate_id}/layout` is correctly optimized for the plot-grid UI. The frontend uses it directly and does not issue N Property-detail requests.

## 11. Plot quick-update is a good purpose-built current-state command

`PATCH /estates/{estate_id}/plots/{property_id}/quick-update` fits the product's selected-plot panel for the current metadata-only phase. After success, the frontend invalidates both Estate layout and Estate stats.

## API-4.01 frontend boundary

### Implemented

1. Live Estate list/search.
2. URL-selected Estate.
3. Live Estate detail/profile.
4. Live Estate statistics.
5. Live Estate plot layout.
6. URL-selected Plot.
7. Live status/holder/price quick update.
8. Permission-aware read/write states.
9. Loading/error/empty states.
10. Mapper and validation tests.

### Deferred to API-4.02

1. Create/Edit/Delete Estate.
2. Create/Edit/Delete Property.
3. Bulk plot generation.
4. Brokerage live register.
5. Brokerage create/detail/edit/delete.
6. Brokerage verification workflow.
7. Estate/Property/Brokerage asset management.
8. Real sale/reservation/allocation transactions.
