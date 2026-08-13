# Finance

The Finance module is the finance-facing workspace for service-backed invoices,
receiving accounts, payment submissions, and confirmed receipts.

Estate property invoices are legacy for this flow. Finance invoice endpoints use
`services.Invoice`, which is tied to a service, quote, request, order, or lead.

## Invoice Workspace

Base path:

```http
/api/v1/finance/
```

Invoice endpoints:

```http
GET /api/v1/finance/invoices
GET /api/v1/finance/invoices/summary
```

`GET /finance/invoices` returns rows shaped for the Finance invoice table:
invoice number, client, service, branch, linked quote/request/order, totals,
paid amount, balance, due date, status, derived display status, overdue flag,
and whether a payment can be recorded.

`GET /finance/invoices/summary` returns aggregate totals for the same filtered
invoice set: total invoiced, total paid, outstanding balance, current balance,
overdue balance, overdue count, invoice count, and status counts.

Overdue status is derived for Finance display when an invoice is unpaid, past
due, and not cancelled. Listing invoices does not mutate the stored invoice
status.

## Accounts Receivable

Accounts receivable is a derived view over unpaid service invoices. There is no
separate receivable model; the balance is always `Invoice.total_amount -
Invoice.amount_paid`.

```http
GET  /api/v1/finance/receivables
GET  /api/v1/finance/receivables/summary
POST /api/v1/finance/receivables/{invoice_id}/send-reminder
```

Receivable rows include invoice, client, service, branch, total amount, amount
paid, outstanding balance, due date, age in days, ageing bucket, invoice status,
display status, and last reminder timestamp where available.

The list and summary endpoints include only invoices with an outstanding
balance and exclude `draft` and `cancelled` invoices. Ageing buckets are derived
from due date:

- `current`: due today or future
- `1_30`: 1-30 days overdue
- `31_60`: 31-60 days overdue
- `61_90`: 61-90 days overdue
- `90_plus`: more than 90 days overdue

The reminder endpoint sends an email to the service request contact email when
available, otherwise to the invoice client's user email. It logs a
`ServiceRequestActivity` with activity type `email` when the invoice has a
service request. Sending a reminder does not change invoice status,
`amount_paid`, or balance.

## Finance Accounts

Finance receiving accounts are managed with `FinanceAccount`.

```http
GET   /api/v1/finance/accounts
POST  /api/v1/finance/accounts
PATCH /api/v1/finance/accounts/{account_id}
POST  /api/v1/finance/accounts/{account_id}/deactivate
```

Accounts may be `bank` or `cash`, may be branch-scoped, and default to `NGN`.
Bank accounts require bank name, account number, and account name. Deactivation
keeps historical payments linked while removing the account from active choices.

## Payment Submissions

Payments are submission-first. Creating a payment submission does not change
`Invoice.amount_paid` or `Invoice.balance`.

Finance endpoints:

```http
GET  /api/v1/finance/payments/submissions
GET  /api/v1/finance/payments/submissions/{submission_id}
POST /api/v1/finance/payments/submissions
POST /api/v1/finance/payments/submissions/{submission_id}/review
```

Client submissions are created through the client invoice endpoint. The client
is derived from the authenticated user. Clients provide amount, payment method,
payment date, transaction reference, proof URL, notes, and a free-text receiving
account description. Clients do not see or select internal `FinanceAccount`
records.

Staff submissions are created through `POST /finance/payments/submissions`.
Staff must provide an active `finance_account_id`, invoice, amount, payment
method, payment date, transaction reference, proof URL, and notes. The client is
derived from the selected invoice.

## Review And Posting

Approving a pending submission creates one confirmed `services.Payment` inside
a database transaction. The payment stores the finance account, proof URL, and
transaction reference. `Payment.save()` recalculates `Invoice.amount_paid` from
confirmed payment rows; `Invoice.balance` remains `total_amount - amount_paid`.

Rejecting a submission records reviewer, timestamp, and rejection reason. It
does not create a payment and does not change the invoice balance. A rejected
submission is not edited; the client or responsible staff member creates a new
submission.

Approval fails if the submitted amount exceeds the invoice balance at review
time.

## Confirmed Payments

Confirmed payments are immutable receipt records created by approving a payment
submission. They are backed by `services.Payment`.

```http
GET /api/v1/finance/payments/confirmed
GET /api/v1/finance/payments/confirmed/{payment_id}
```

The list endpoint supports filters by invoice, client, finance account, payment
date, branch, and search. The detail endpoint returns the same receipt shape for
one payment, including invoice, client, service, branch, finance account,
amount, method, transaction reference, proof URL, and creator.

Invoice balances are derived from confirmed `Payment` rows. Pending and rejected
submissions do not affect `Invoice.amount_paid` or `Invoice.balance`.

## Compatibility

Existing client invoice submission endpoints remain available:

```http
POST /api/v1/service-requests/invoices/{invoice_id}/payment-submissions
POST /api/v1/service-requests/payments/submit
```

They now write the extended submission metadata where supplied. They still
create pending `PaymentSubmission` rows and do not change invoice balances.

Existing review endpoints remain available:

```http
POST /api/v1/invoices/payment-submissions/{submission_id}/review
POST /api/v1/service-requests/admin/payment-submissions/{submission_id}/review
```

They use the same approval behavior as Finance review. Approving a client-origin
submission requires a `finance_account_id`, because client submissions only
capture free-text receiving account information.

The legacy direct payment endpoint remains for backfill/compatibility:

```http
GET  /api/v1/payments
GET  /api/v1/payments/{payment_id}
POST /api/v1/payments
```

These routes expose the older service payment API. They are not the Finance UI
path. New direct creates must include `finance_account_id` and
`proof_of_payment`; the Finance UI should use `/api/v1/finance/payments/*`
submission and review endpoints instead.
