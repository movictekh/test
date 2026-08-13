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
attachments, quote approval, client quote response, invoice/payment handling,
and service order conversion. Operations-task conversion, deliverables, and
client acceptance workflows are handled by later fulfillment modules.

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
GET  /api/v1/service-requests/quotes
GET  /api/v1/service-requests/quotes/{quote_id}
POST /api/v1/service-requests/quotes/{quote_id}/accept
POST /api/v1/service-requests/quotes/{quote_id}/reject
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

Quote admin endpoints:

```http
GET    /api/v1/quotes
POST   /api/v1/quotes
GET    /api/v1/quotes/{quote_id}
PATCH  /api/v1/quotes/{quote_id}
POST   /api/v1/quotes/{quote_id}/approve
POST   /api/v1/quotes/{quote_id}/invoice
DELETE /api/v1/quotes/{quote_id}
```

Invoice admin endpoints:

```http
GET    /api/v1/invoices
GET    /api/v1/invoices/{invoice_id}
PATCH  /api/v1/invoices/{invoice_id}
POST   /api/v1/invoices/{invoice_id}/send
POST   /api/v1/invoices/{invoice_id}/cancel
POST   /api/v1/invoices/{invoice_id}/service-order
GET    /api/v1/invoices/payment-submissions
POST   /api/v1/invoices/payment-submissions/{submission_id}/review
```

Service order admin endpoints:

```http
GET    /api/v1/orders
POST   /api/v1/orders
GET    /api/v1/orders/{order_id}
PATCH  /api/v1/orders/{order_id}
PUT    /api/v1/orders/{order_id}
DELETE /api/v1/orders/{order_id}
POST   /api/v1/orders/{order_id}/activities
POST   /api/v1/orders/{order_id}/milestones
POST   /api/v1/orders/{order_id}/milestones/{milestone_id}/complete
POST   /api/v1/orders/{order_id}/milestones/{milestone_id}/reopen
GET    /api/v1/orders/{order_id}/tasks
POST   /api/v1/orders/{order_id}/tasks
GET    /api/v1/orders/{order_id}/tasks/{task_id}
PATCH  /api/v1/orders/{order_id}/tasks/{task_id}
PUT    /api/v1/orders/{order_id}/tasks/{task_id}
POST   /api/v1/orders/{order_id}/tasks/{task_id}/advance
DELETE /api/v1/orders/{order_id}/tasks/{task_id}
GET    /api/v1/orders/{order_id}/deliverables
POST   /api/v1/orders/{order_id}/deliverables
GET    /api/v1/orders/{order_id}/deliverables/{deliverable_id}
PATCH  /api/v1/orders/{order_id}/deliverables/{deliverable_id}
PUT    /api/v1/orders/{order_id}/deliverables/{deliverable_id}
POST   /api/v1/orders/{order_id}/deliverables/{deliverable_id}/approve
POST   /api/v1/orders/{order_id}/deliverables/{deliverable_id}/reject
DELETE /api/v1/orders/{order_id}/deliverables/{deliverable_id}
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

## Quote Lifecycle

`POST /api/v1/service-requests/admin/{id}/quote` creates a new `Quote` for the
request. The quote starts as `awaiting_approval`; the request remains
`under_review` with next action set to quote approval. Existing active quotes
block duplicate creation. Creation requires `required_approver_role_id`, which
stores the role expected to approve the quote.

Approval requires both `quotes:approve` and an employee role matching the
quote's `required_approver_role_id`. Approval sets the quote to `sent`, records
the approver and timestamps, sets the service request to `quoted`, records a
`quote_sent` activity, emails the client, and makes the quote visible through the
client quote endpoints. This does not use the generic approval workflow engine.

Clients can accept or reject only `sent` quotes. Acceptance sets the quote to
`accepted`, records `quote_accepted`, and sets the request next action to invoice
creation. Rejection sets the quote to `rejected`, stores an optional rejection
reason, records `quote_rejected`, and returns the request to review.

Rejected quotes are immutable, including their selected required approver role.
A replacement must be created as a new quote on the same service request; it
links to the rejected quote through `previous_quote` and increments the quote
`version`.

## Invoice & Payment Lifecycle

`POST /api/v1/quotes/{quote_id}/invoice` creates a draft invoice from an
`accepted` quote. The invoice copies the quote client, service, service request,
subtotal, tax rate, total, payment terms, and deposit amount. The quote's
`deposit_amount` becomes the invoice `activation_threshold_amount`.

Only one active invoice can exist for a quote. Active statuses are `draft`,
`sent`, `viewed`, `partially_paid`, `paid`, and `overdue`.

Admins send invoices with `POST /api/v1/invoices/{invoice_id}/send`. Sending sets
the invoice to `sent`, emails the client, and records an `invoice_issued`
activity. Draft and sent invoices can be patched; invoices with confirmed
payments cannot be cancelled.

Client invoice endpoints:

```http
GET  /api/v1/service-requests/invoices
GET  /api/v1/service-requests/invoices/{invoice_id}
POST /api/v1/service-requests/invoices/{invoice_id}/payment-submissions
GET  /api/v1/service-requests/orders
GET  /api/v1/service-requests/orders/{order_id}
GET  /api/v1/service-requests/orders/{order_id}/tasks
GET  /api/v1/service-requests/orders/{order_id}/deliverables
GET  /api/v1/service-requests/orders/{order_id}/deliverables/{deliverable_id}
POST /api/v1/service-requests/orders/{order_id}/deliverables/{deliverable_id}/approve
POST /api/v1/service-requests/orders/{order_id}/deliverables/{deliverable_id}/reject
```

Clients only see their own issued invoices. Client payment submission records
proof of payment and creates a `payment_submitted` activity. Payment submissions
are pending records; they do not update `amount_paid` or invoice balance until
approved.

Finance/admin users review submissions through the invoice payment-submission
endpoints or the Finance endpoints documented in [Finance](./finance.md).
Confirmed submissions create `Payment` records, update invoice `amount_paid`,
update invoice status to `partially_paid` or `paid`, and record
`payment_confirmed`. Client-origin submissions carry free-text receiving account
information; approval requires a managed finance account. Staff-origin
submissions must be linked to an active finance account when submitted.

Rejected submissions do not change the invoice balance. The client or staff
member must create a new submission rather than editing the rejected one.

When confirmed payments reach `activation_threshold_amount`,
`activation_threshold_met_at` is set and a `payment_threshold_met` activity is
recorded. Staff can then create a service order from the invoice with
`POST /api/v1/invoices/{invoice_id}/service-order`.

## Service Order Lifecycle

Invoice-backed service orders are the operational handoff from commercial flow
to fulfillment. Order creation requires:

- `orders:create`
- a confirmed invoice payment threshold (`activation_threshold_met_at`)
- no existing order for the same invoice

The order copies the invoice client, service, quote, service request, amount,
and due date. It links back to the invoice and service request, sets the request
status to `converted`, links `Invoice.order`, records request/order activities,
and starts in `pending_mobilisation`.

Order statuses are:

- `pending_mobilisation`
- `active`
- `quality_review`
- `awaiting_client`
- `completed`
- `on_hold`
- `cancelled`

Order milestones are seeded from the service request workflow when available,
falling back to `Order Setup`, `Execution`, `Quality Review`, and
`Client Acceptance`. Staff can add activities, add milestones, complete
milestones, reopen milestones, and update order control fields such as status,
progress, stage, next action, owner, and due date.

Client order endpoints only return the authenticated client's own orders, and
only expose client-visible milestones and activities.

Manual order creation through `POST /api/v1/orders` remains available for
backfill and exception cases. Normal commercial orders should be created from
the invoice service-order endpoint.

## Execution Task Lifecycle

Execution tasks are service-order-native work items. They can be attached to an
order milestone, assigned to an owner and assignees, and advanced across:

- `to_do`
- `in_progress`
- `review`
- `done`
- `cancelled`

Task creation is manual in this pass. Completing tasks does not automatically
complete milestones yet. Staff task changes record order activity entries.
Client task endpoints expose compact task summaries for the client's own orders
and omit internal instructions and acceptance criteria.

## Deliverable Lifecycle

Deliverables are versioned files/documents attached to service orders, optional
milestones, and optional execution tasks. Supported types are reports, drawings,
survey plans, certificates, legal documents, progress evidence, handover files,
and other documents.

Deliverable statuses are:

- `draft`
- `under_review`
- `approved`
- `rejected`
- `superseded`

Approval modes are:

- `none`
- `supervisor`
- `client`

Deliverables with no approval can be created as approved. Supervisor and client
approval deliverables start under review unless explicitly set otherwise.
Client approval deliverables must be client-visible. Clients can approve or
reject only their own client-visible deliverables with `approval_mode=client`
and `status=under_review`.

Rejected deliverables are immutable for their file, version, title, visibility,
approval mode, ownership, and status. A replacement must be uploaded as a new
deliverable/version. Approval and rejection actions record service order
activity.

This pass does not create `operations.Project`, `operations.Milestone`, or
`operations.Task` records. Bridging service orders into the Operations app is a
later project/worksite fulfillment pass.

TODO: add dedicated payment history endpoints so admin/finance and clients can
audit all proof submissions and confirmed payments for an invoice:

```http
GET /api/v1/invoices/{invoice_id}/payment-history
GET /api/v1/service-requests/invoices/{invoice_id}/payment-history
```

The response should include payment submissions, proof URLs, review status,
reviewer/timestamps, rejection reasons, and confirmed `Payment` records.

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

They now follow the same submission-first design as the Finance module:
submissions remain pending until reviewed, approval creates the confirmed
`Payment`, and rejection leaves invoice balances unchanged. Review calls that
approve a client-origin submission must include `finance_account_id`.

The legacy direct `POST /api/v1/payments` endpoint remains for backfill and
compatibility only. New direct creates require `finance_account_id` and
`proof_of_payment`; the Finance UI should use payment submissions instead.
