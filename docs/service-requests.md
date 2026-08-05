# Commercial Service Requests

Commercial service requests are the intake and case-file layer for the Service
Operations OS. They use `services.ServiceRequest` and the active configuration
on `services.Service`; the old `user.ServiceRequest` model is no longer the
request CRUD target.

## Lifecycle

Requests move through these statuses:

- `new`
- `under_review`
- `awaiting_client`
- `site_assessment`
- `quoted`
- `converted`
- `rejected`

This pass supports intake, review/control updates, activity journal entries,
attachments, and quote handoff. Order, invoice, payment, approval, and
operations-task conversion are handled by later commercial-flow modules.

## Data Model Behavior

Request creation requires an active, visible `Service` with an active
`ServiceRequestForm`. The submitted answers are validated against that active
form, then stored in two places:

- `answers_snapshot`: permanent JSON record of the submitted values.
- `ServiceRequestAnswer`: queryable rows for each form field.

The request also snapshots the active form, pricing config, and workflow IDs and
versions. Later edits to the service catalogue do not rewrite the historical
request record.

The request is anchored to `user.Client`. Client portal submissions use
`request.user.client_profile`; staff-created requests provide `client_id`.

## Endpoint Groups

Base path:

```http
/api/v1/service-requests/
```

Client portal endpoints:

```http
GET  /api/v1/service-requests/summary
GET  /api/v1/service-requests/
POST /api/v1/service-requests/
GET  /api/v1/service-requests/{id}
POST /api/v1/service-requests/{id}/activities
POST /api/v1/service-requests/{id}/attachments
```

Staff endpoints:

```http
GET   /api/v1/service-requests/admin
POST  /api/v1/service-requests/admin
GET   /api/v1/service-requests/admin/{id}
PATCH /api/v1/service-requests/admin/{id}
POST  /api/v1/service-requests/admin/{id}/activities
POST  /api/v1/service-requests/admin/{id}/attachments
POST  /api/v1/service-requests/admin/{id}/quote
```

Metadata endpoints:

```http
GET /api/v1/service-requests/choices
GET /api/v1/service-requests/services/{service_id}/intake-form
```

`choices` returns backend-controlled values for statuses, priorities, sources,
customer types, field types, activity types, and outcomes.

`intake-form` returns the selected service, active request form, fields, and
active subservices so the frontend can render dynamic service request intake.

## Client Access

Client list and detail endpoints only return requests belonging to the logged-in
client profile. If the authenticated user does not have `client_profile`, create
returns `400`.

Client activity creation is limited to client-safe activity types:

- `document_received`
- `email`
- `whatsapp`
- `internal_note`

## Staff Access

Staff endpoints use `service_requests` permissions:

- `create`
- `view`
- `list`
- `update`
- `delete`

Role branch scoping applies to staff list and detail views through
`ServiceRequest.branch`.

Staff creation accepts the same dynamic answers as client creation and adds
commercial controls such as selected client, branch, owner, service lead, CRM
lead, source fields, dates, and estimate.

Staff updates can change request control fields such as status, owner, priority,
due date, next action, estimate, source, and contact details. Updates write a
`control_update` or `status_change` activity entry.

## Quote Handoff

`POST /api/v1/service-requests/admin/{id}/quote` either creates a draft `Quote`
from the request or links an existing quote. The request is set to `quoted`, the
quote is linked to the request, and a `quote_prepared` activity is recorded.

No service order is created in this pass.

## Legacy Payment Routes

The previous service-request router also exposed client payment submission URLs.
Those URLs are retained for compatibility but are deprecated under the service
request namespace:

```http
GET  /api/v1/service-requests/payments/
GET  /api/v1/service-requests/payments/{invoice_id}
POST /api/v1/service-requests/payments/submit
GET  /api/v1/service-requests/admin/payment-submissions
POST /api/v1/service-requests/admin/payment-submissions/{submission_id}/review
```

They should move under the invoice/payment routers in a later pass.

