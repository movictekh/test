# Real Estate

The Real Estate module covers owned estates (`user.Estate`), the plots and
properties within them (`user.Property`), and third-party commission listings
(`user.BrokerageListing`). It is split across two routers under
`/api/v1/`:

- `estates` prefix -> `user/api/v1/estate.py` (tags `Real Estate`)
- `brokerage` prefix -> `user/api/v1/brokerage.py` (tags `Brokerage`)

## Data Model

### `user.Estate`

An estate developed by or managed for the company. Carries title-document
checkboxes (`has_c_of_o`, `has_deed_of_assignment`, `has_survey_plan`),
government-approval checkboxes, amenity flags, pricing fields, a `boundary`
JSON polygon, and associated `EstateDocument` files.

Estate types: `residential`, `commercial`, `industrial`, `mixed_use`, `land`.

Estate statuses: `available`, `sold_out`, `under_development`, `coming_soon`.

### `user.Property`

A property inside an estate (or standalone when `estate` is null). Two fields
were added for the grid workflow:

- `plot_number`: sequential plot number within the estate (`PositiveIntegerField`,
  nullable), indexed with `(estate, plot_number)`.
- `client_name`: free-form reservation holder / client name (`CharField`,
  blank).

Property statuses:

- `not-for-sale`
- `available`
- `reserved`
- `sold`
- `hold` (added for the estate grid; used while a plot is under inspection /
  on temporary hold)

Property types: `plot`, `residential`, `commercial`. Each type enforces its own
required fields in `Property.clean()`.

### `user.BrokerageListing`

A third-party property listing managed on a commission basis. Key fields:

- `title`, `description`, `location`, `price`, `property_type`
- `owner_name`, `owner_phone`, `owner_email` (mandate giver)
- `commission_rate` (0-100%, default 5.00)
- `verification_status`: `pending`, `verified`, `inspection_due`
- `status`: `available`, `sold`, `off_market`
- `assigned_agent` (FK to `user.User`, nullable), `estate` (FK to `user.Estate`,
  nullable)
- `tags` (JSON list), `is_active`
- Related `BrokerageListingImage` rows (PNG/JPG/JPEG, caption)

`BrokerageListing.clean()` enforces non-blank `title`/`location` and valid
status values. This model intentionally has no link to the service request /
quote / invoice lifecycle; it is a standalone module.

## Estate & Plot Endpoints

Base path:

```http
/api/v1/estates/
```

Existing CRUD (list, create, detail, update, delete) plus properties and
standalone property routes are unchanged. The following were added:

### Plot statistics

```http
GET /api/v1/estates/{estate_id}/stats
```

Permission: `estates:view`. Returns:

```json
{
  "total": 10,
  "sold": 1,
  "reserved": 1,
  "available": 7,
  "hold": 1,
  "not_for_sale": 0,
  "total_value": 45000000.00,
  "sold_value": 4800000.00
}
```

`total_value` sums all property prices; `sold_value` sums only `sold`
properties. Unknown estate returns `404`.

### Plot grid layout

```http
GET /api/v1/estates/{estate_id}/layout
```

Permission: `properties:list`. Returns the full plot grid ordered by
`plot_number` then `property_name`, optimized for grid visualization:

```json
[
  {
    "id": 41,
    "plot_number": 3,
    "property_name": "Plot 003",
    "status": "hold",
    "status_display": "Hold",
    "plot_size": 500.00,
    "price": 4500000.00,
    "client_name": "Under inspection"
  }
]
```

Unknown estate returns `404`.

### Plot quick update

```http
PATCH /api/v1/estates/{estate_id}/plots/{property_id}/quick-update
```

Permission: `properties:update`. Body accepts any subset of:

```json
{
  "status": "reserved",
  "price": 4500000.00,
  "client_name": "Chief Okafor Sunday"
}
```

- Empty body returns `400` (`No fields to update.`).
- Invalid status returns `400` listing the valid statuses.
- Non-existent property or estate returns `404`.
- Returns the updated `PlotLayoutSchema` shape (same as the layout grid).

## Brokerage Endpoints

Base path:

```http
/api/v1/brokerage/
```

### Field choices

```http
GET /api/v1/brokerage/choices/fields
```

No permission required. Returns `verification_status`, `listing_status`, and
`property_type` as `{value, label}` lists.

### Statistics

```http
GET /api/v1/brokerage/stats
```

Permission: `brokerage:list`. Returns totals for the listing pool:

```json
{
  "total": 2,
  "verified": 1,
  "pending_verification": 1,
  "inspection_due": 0,
  "sold": 0,
  "available": 2,
  "off_market": 0,
  "total_listing_value": 19500000.00
}
```

### Listings

```http
GET  /api/v1/brokerage/
POST /api/v1/brokerage/
GET  /api/v1/brokerage/{listing_id}
PUT  /api/v1/brokerage/{listing_id}
DELETE /api/v1/brokerage/{listing_id}
```

List permissions: `brokerage:list` (create/view/update/delete for the others).

List filters (all optional):

- `status` (`available`, `sold`, `off_market`)
- `verification_status` (`pending`, `verified`, `inspection_due`)
- `property_type` (`residential`, `commercial`, `land`)
- `is_active` (bool)
- `search` (matches `title`, `location`, `owner_name`, `description`)

List is paginated with `LimitOffsetPagination` (page size 10) and ordered by
`-created_at`. `GET /stats` and `GET /choices/fields` must stay registered
before the parameterized `/{listing_id}` routes (same pattern as the estates
router).

Create body (`BrokerageListingCreateSchema`): `title`, `location`, `price`,
`property_type`, `owner_name` are required; `commission_rate` defaults to 5.00,
`verification_status` to `pending`, `status` to `available`, `is_active` to
`true`. Optional `assigned_agent_id`, `estate_id`, `tags`, and `images` (URLs).
`estate_id` must reference an existing estate; the response resolves
`estate_name` from the linked estate.

Update (`BrokerageListingUpdateSchema`): all fields optional. When `images` is
provided the existing images are deleted and replaced. `assigned_agent_id` and
`estate_id` are assigned directly; nulling them unsets the relation.

The listing response includes display fields: `property_type_display`,
`verification_status_display`, `status_display`, `assigned_agent_name`, and
`estate_name`.

### Verification transition

```http
PATCH /api/v1/brokerage/{listing_id}/verify
```

Permission: `brokerage:update`. Body:

```json
{ "verification_status": "verified" }
```

Valid values: `pending`, `verified`, `inspection_due`. Invalid values return
`400`; unknown listing returns `404`.

## Permissions

Roles are the gate for all write and list paths via `@require_permission`. The
resource keys registered in `user/models/role.py` are:

```python
"estates":    ["create", "view", "list", "update", "delete"],
"properties": ["create", "view", "list", "update", "delete"],
"brokerage":  ["create", "view", "list", "update", "delete"],
```

A role whose `permissions` dict omits the resource gets `403` on those
endpoints. The choices endpoints (`/estates/choices/fields`,
`/estates/{id}/properties/choices/fields`, `/brokerage/choices/fields`) are
unauthenticated helpers for rendering dropdowns. No seeded role currently
grants `brokerage`; granting it is a data change (role or migration), not code.

## Notes

- Trailing slashes: Django Ninja parameterized routes here match **without** a
  trailing slash (e.g. `GET /api/v1/estates/2` works, `/estates/2/` does not).
  This is pre-existing URL-matching behavior across the API, not specific to
  these endpoints.
- Migration `user/migrations/0094_brokeragelisting_brokeragelistingimage_and_more.py`
  is additive: creates the two brokerage tables, adds `plot_number` and
  `client_name` to `Property`, adds the `hold` status choice, and adds the
  `(estate, plot_number)` index. No existing field was renamed or removed.
- Real Estate tests live in `domains/real_estate/tests/`, including estate
  stats/layout/quick-update, brokerage CRUD/verify/stats/choices and permission
  enforcement, plus invoice approval/payment hardening coverage.
