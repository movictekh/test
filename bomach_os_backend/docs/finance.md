# Finance

The Finance module is the finance-facing workspace for service-backed invoices,
receiving accounts, payment submissions, confirmed receipts, and client/project
wallets.

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

Each Finance account may also carry an account-scoped opening balance:

- `opening_balance`
- `opening_balance_date`

Cashbook endpoints use these values as the starting point for account and
branch-scoped running balances. Existing accounts default to `0.00`.

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

## Client And Project Wallets

Finance wallets are optional fund-control containers for clients and service
orders. A wallet is not a stored balance; balances are computed from posted
`FinanceWalletEntry` ledger rows.

```http
GET  /api/v1/finance/wallets
POST /api/v1/finance/wallets
GET  /api/v1/finance/wallets/{wallet_id}
PATCH /api/v1/finance/wallets/{wallet_id}
GET  /api/v1/finance/wallets/{wallet_id}/entries
POST /api/v1/finance/wallets/{wallet_id}/entries
POST /api/v1/finance/wallets/{wallet_id}/entries/{entry_id}/void
```

Wallet types:

- `client`
- `project`
- `property`
- `restricted_project`

Client wallets require a client and may exist without a service order. Project,
property, and restricted project wallets require a linked `ServiceOrder` at API
validation time. Existing service orders are not required to have wallets.

Wallet entry types:

- `funding`
- `spend`
- `commitment`
- `commitment_release`
- `adjustment`

Only posted entries affect balances. Pending and void entries are ignored.
Balances are derived as:

- `funded = posted funding + posted positive adjustments`
- `spent = posted spend`
- `committed = posted commitments - posted commitment releases`
- `available = funded - spent - committed`

Wallet balances are read-only API fields. The create/update endpoints do not
accept direct `funded`, `spent`, `committed`, or `available` values.

When a payment submission is approved, Finance still creates the confirmed
`services.Payment` and recalculates the invoice balance as before. If the
payment invoice is linked to a service order that has a Finance wallet, approval
also creates a posted `funding` wallet entry linked to the wallet, invoice,
payment, and service order. If no wallet exists, payment approval skips wallet
posting.

Manual wallet entries can still record adjustments and exceptional wallet
activity. Expense approval/payment now posts standard project wallet movements
automatically when the expense is linked to a service order with a wallet.

## Budgets And Controls

Finance budgets are represented by `FinanceBudget`. This replaces the legacy
`services.Budget` model, which only supported branch/department fiscal
allocations and stored spend directly.

There are no Finance budget endpoints in this slice. The model is in place for
the later Budgets & Controls API.

`FinanceBudget` supports:

- generated `budget_number`
- budget name
- owner
- optional branch
- optional department
- optional service order
- budget type
- period label, start date, and end date
- approved amount
- warning and block thresholds
- status
- notes and audit timestamps

Budget types:

- `operating`
- `department`
- `service_order`
- `project`
- `capital`
- `marketing`
- `other`

Budget statuses:

- `draft`
- `active`
- `watch`
- `exceeded`
- `closed`
- `cancelled`

`spent`, `committed`, `available`, and `utilization_pct` are model properties.
For now, spent and committed return `0.00` until the next slice defines how
expenses, vendor bills, petty cash, and wallet entries are mapped into budget
control calculations.

Compatibility note: the legacy `/api/v1/budgets` services route and the
`services.Budget` code surface have been removed. Historical migrations still
contain the old model history, and the new services migration drops the legacy
budget table.

## Expenses And Service Costs

Finance expense endpoints use the existing `services.Expense` model with
additional Finance fields for order costing and cashbook classification.

```http
GET    /api/v1/finance/expenses
POST   /api/v1/finance/expenses
GET    /api/v1/finance/expenses/{expense_id}
PATCH  /api/v1/finance/expenses/{expense_id}
DELETE /api/v1/finance/expenses/{expense_id}
POST   /api/v1/finance/expenses/{expense_id}/approve
POST   /api/v1/finance/expenses/{expense_id}/reject
POST   /api/v1/finance/expenses/{expense_id}/pay
```

Finance expenses may link to a branch, Finance account, and service order. They
also include project/cost-centre label, stage, cost type, beneficiary,
billability, client visibility, attachment, approval/rejection audit fields,
payment reference, and payment audit fields.

Cost types:

- `direct_cost`
- `operating_expense`
- `overhead_allocation`
- `capital_expenditure`

Expense statuses:

- `pending`
- `approved`
- `rejected`
- `paid`

Finance expense status changes are controlled workflow actions. Create defaults
to `pending`, and `PATCH /api/v1/finance/expenses/{expense_id}` must not be used
to move an expense to `approved`, `rejected`, or `paid`.

Workflow rules:

- approve: pending only; requester cannot approve their own expense; records
  approver and timestamp
- reject: pending only; requester cannot reject their own expense; records
  reviewer, timestamp, and optional reason
- pay: approved only; requires a Finance account; records payer, `paid_at`, and
  optional `payment_reference`

Pay payload:

```json
{
  "finance_account_id": 1,
  "paid_at": "2026-08-17T10:30:00+01:00",
  "payment_reference": "BANK-TXN-12345"
}
```

`paid_at` and `payment_reference` are optional. If `paid_at` is omitted, the
current timestamp is used.

Project wallet posting:

- approved expense: creates a posted `commitment` entry
- rejected expense: no wallet entry
- paid expense: creates a posted `commitment_release` entry when a commitment
  exists, and creates a posted `spend` entry

These automatic wallet entries are linked to the `services.Expense` record for
traceability and duplicate prevention. If the expense has no service order
wallet, the workflow status change succeeds and wallet posting is skipped.

Compatibility note: legacy service expense approve/reject URLs remain available
for existing clients. Finance clients should use the Finance approve/reject/pay
endpoints because generic status edits no longer represent the supported Finance
workflow path.

## Vendor Bills And Accounts Payable

Vendor bills represent external supplier obligations. They are separate from
staff expenses because they need vendor filtering, due-date/payable reporting,
withholding tax fields, and supplier payment tracking.

```http
GET  /api/v1/finance/vendors
POST /api/v1/finance/vendors
GET  /api/v1/finance/vendors/{vendor_id}
PATCH /api/v1/finance/vendors/{vendor_id}
POST /api/v1/finance/vendors/{vendor_id}/deactivate

GET   /api/v1/finance/vendor-bills
POST  /api/v1/finance/vendor-bills
GET   /api/v1/finance/vendor-bills/summary
GET   /api/v1/finance/vendor-bills/{bill_id}
PATCH /api/v1/finance/vendor-bills/{bill_id}
POST  /api/v1/finance/vendor-bills/{bill_id}/approve
POST  /api/v1/finance/vendor-bills/{bill_id}/reject
POST  /api/v1/finance/vendor-bills/{bill_id}/pay
POST  /api/v1/finance/vendor-bills/{bill_id}/void
```

`FinanceVendor` is the slim supplier record used for filtering payable bills. It
stores vendor number, name, contact fields, tax ID/TIN, default category, status,
and an optional compatibility link to `Partner`.

Vendor bills link to `ServiceOrder` when the obligation belongs to a specific
order. There is no Finance project FK in this slice; project/cost-centre labels
are display values derived from the linked service order where available.
Unlinked vendor bills remain valid for general operating obligations.

Vendor bill statuses:

- `draft`
- `awaiting_approval`
- `approved`
- `scheduled`
- `paid`
- `rejected`
- `void`

Workflow rules:

- create: defaults to `awaiting_approval` and calculates
  `net_amount = gross_amount - withholding_tax`
- approve: awaiting approval only; records approver and timestamp
- reject: awaiting approval only; records reviewer, timestamp, and reason
- pay: approved or scheduled only; requires a Finance account and records
  `paid_at`, payer, and optional payment reference
- void: allowed only before payment

Project wallet posting:

- approved service-order bill: creates a posted `commitment` using gross amount
- rejected bill: no wallet entry
- paid service-order bill: creates posted `commitment_release` and `spend` rows
  using gross amount
- void unpaid bill: voids the posted commitment if one exists

Accounts payable summary returns open payable total, overdue payable, due-soon
payable, approved unpaid, scheduled unpaid, paid total, bill count, overdue
count, due-soon count, and status counts. Payable totals use `net_amount`; order
cost/profitability totals use `gross_amount`.

## Petty Cash

Petty cash is modeled as cash-account-backed advances and retirement lines. It
does not create a separate wallet type. A petty cash advance must use an active
`FinanceAccount` with `account_type=cash`.

```http
GET  /api/v1/finance/petty-cash/advances
POST /api/v1/finance/petty-cash/advances
GET  /api/v1/finance/petty-cash/advances/{advance_id}
PATCH /api/v1/finance/petty-cash/advances/{advance_id}
POST /api/v1/finance/petty-cash/advances/{advance_id}/approve
POST /api/v1/finance/petty-cash/advances/{advance_id}/reject
POST /api/v1/finance/petty-cash/advances/{advance_id}/issue
POST /api/v1/finance/petty-cash/advances/{advance_id}/retire
POST /api/v1/finance/petty-cash/advances/{advance_id}/cancel
GET  /api/v1/finance/petty-cash/advances/{advance_id}/retirement-lines
GET  /api/v1/finance/petty-cash/summary
```

Advance statuses:

- `requested`
- `approved`
- `rejected`
- `issued`
- `partially_retired`
- `retired`
- `cancelled`

Workflow rules:

- create: records requester, cash account, purpose, requested amount, due date,
  optional branch, optional service order, attachment, and notes
- approve: requested only; records approver and timestamp
- reject: requested only; records reviewer, timestamp, and optional reason
- issue: approved only; records issued amount, custodian, issuer, and timestamp
- retire: issued or partially retired only; records spent lines and/or returned
  cash lines
- cancel: requested or approved only

Issue is blocked when the requester has another overdue unretired advance.
Unretired balance is derived as `amount_issued - amount_retired -
amount_returned`.

Retirement lines support category, cost type, stage, description, receipt URL,
billable flag, client visibility flag, spent amount, and returned amount. A
single line may record spend or returned cash, not both. Spend lines require a
category.

Cashbook treatment:

- issuing petty cash is a `petty_cash_advance` outflow from the cash account
- returned unused cash is a `petty_cash_return` inflow to the same cash account
- spent retirement lines do not create another cashbook outflow, because the
  cash already left the account at issue time

Service-order treatment:

- retirement spend lines linked to a service order count as `petty_cash` costs
  in service order cost ledger and transaction views
- service-order profitability includes retirement spend in paid costs
- when the linked service order has a Finance wallet, retirement spend posts a
  wallet `spend` entry

The petty cash summary returns issued, retired, returned, unretired, overdue,
status counts, and one row per cash account. Account calculated balance is
derived as `opening_balance - issued_total + returned_total`. Replenishment is
flagged when the calculated balance is at or below 25% of the opening balance.

## Cashbook And Transaction Ledger

Cashbook is read-only and derived. There is no manual cashbook posting endpoint
in this slice.

```http
GET /api/v1/finance/cashbook
GET /api/v1/finance/cashbook/summary
```

Cashbook rows are derived from:

- account opening balances on `FinanceAccount`
- confirmed `services.Payment` rows as inflows
- paid `services.Expense` rows as outflows
- paid `VendorBill` rows as outflows
- issued `PettyCashAdvance` rows as cash outflows
- `PettyCashRetirementLine` returned-cash rows as cash inflows

Cashbook source rules:

- confirmed payment: `client_payment`
- paid expense with a service order: `service_cost`
- paid expense without a service order and `cost_type=operating_expense`:
  `operating_expense`
- paid expense without a service order and another cost type: `expense`
- paid vendor bill: `vendor_bill`
- issued petty cash: `petty_cash_advance`
- returned unused petty cash: `petty_cash_return`

Filters:

- `date_from`
- `date_to`
- `finance_account_id`
- `branch_id`
- `service_order_id`
- `client_id`
- `source`
- `status`
- `search`

Rows include date, reference, source, description, service/order/project labels,
Finance account, branch, money in, money out, running balance, and status.

The summary endpoint returns opening balance, period inflow, period outflow, net
movement, closing balance, posted count, pending count, and source breakdowns.

## Service Order Profitability

Service order profitability is a read-only Finance view over existing
`ServiceOrder` records. Finance does not create or sync service orders from this
surface.

```http
GET /api/v1/finance/service-orders/profitability
GET /api/v1/finance/service-orders/profitability/summary
GET /api/v1/finance/service-orders/{order_id}/profitability
GET /api/v1/finance/service-orders/{order_id}/costs
GET /api/v1/finance/service-orders/{order_id}/transactions
```

The profitability list and detail endpoints expose order identity, client,
service, branch, project label, order/payment status, progress, stage, due date,
contract value, invoiced total, collected total, outstanding balance, paid
costs, committed costs, cash contribution, accrued profit, and wallet balances
where a Finance wallet exists.

Current source rules:

- contract value: `ServiceOrder.amount`
- project label: `ServiceOrder.description`
- invoiced total: invoices linked to the order
- collected total: confirmed payment rows linked through order invoices
- paid costs: paid expenses, paid vendor bills, and petty cash retirement spend
  linked to the order
- committed costs: approved expenses and approved/scheduled vendor bills linked
  to the order
- cash contribution: collected total minus paid costs
- accrued profit: invoiced total minus paid costs

The following fields are nullable until dedicated finance-control fields exist:

- `contract_type`
- `cost_budget`
- `overhead_amount`
- `expected_gross_profit`
- `expected_margin_pct`

The cost ledger endpoint returns expenses, vendor bills, and petty cash
retirement spend linked to the order. Rows include source, date, category, cost
type, stage, description, beneficiary/vendor, amount, status, billable flag,
client visibility, Finance account, attachment, and paid timestamp.

The transaction endpoint returns order-level cash/contribution movement:
confirmed payment inflows, paid expense outflows, paid vendor bill outflows, and
petty cash retirement spend. Its running contribution starts at zero for the
order and is not the same as account-level cashbook running balance.

List and summary filters include date range, branch, client, service, order
status, payment status, profitability status, service order, and search.

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

Existing user wallet routes remain available:

```http
GET  /api/v1/wallet/transactions/
GET  /api/v1/wallet/balance/{user_id}/
POST /api/v1/wallet/fund-wallet-webhook/
```

Those routes manage personal user wallet transactions. They are separate from
Finance client/project wallets and are not used for Finance project fund
availability.

Finance wallets are additive. Service requests, invoices, service orders, and
payment submissions do not require wallet fields. Existing clients and
historical orders continue to work without wallet records.

Existing `/api/v1/expenses` routes remain available for compatibility. The
Finance UI should use `/api/v1/finance/expenses` for the richer expense/cost
surface.

Petty cash is additive. It does not replace Finance expenses, vendor bills, or
legacy service expense routes. Existing clients that do not create petty cash
advances continue to use invoices, payments, expenses, vendor bills, and wallets
without supplying petty cash fields.

## Cash Flow Forecast

Cash Flow Forecast is a read-only, deterministic liquidity projection built on
existing Finance records. It does not store weekly forecast balances and does
not introduce a separate cash-flow model.

```http
GET /api/v1/finance/cash-flow/forecast
```

Query parameters:

- `as_of`: forecast start date; defaults to the current local date
- `weeks`: forecast horizon; defaults to `13` and must be between `1` and `52`
- `branch_id`: optional branch filter, still constrained by the caller's role
  branch scope

The response is shaped for the Finance Cash Flow Forecast workspace and returns:

- opening cash
- expected inflows for the next 30 days
- expected outflows for the next 30 days
- forecast 30-day closing cash
- forecast closing cash at the selected horizon
- weekly opening, inflow, outflow, net movement, and closing balances
- upcoming obligations
- the underlying forecast items used to explain the calculation

### Forecast source rules

Opening cash reuses the same actual-money sources as Cashbook:

- Finance account opening balances
- confirmed client payments
- paid expenses
- paid vendor bills
- issued petty cash
- returned petty cash

Expected inflows use outstanding `services.Invoice` balances. Draft, cancelled,
and fully paid invoices are excluded. Each balance is forecast on its invoice
due date. An overdue receivable is placed on the forecast `as_of` date so it
appears in week 1.

Expected outflows use `VendorBill.net_amount` for bills in
`awaiting_approval`, `approved`, or `scheduled` status. Paid, rejected, void,
and draft bills are excluded. Each open bill is forecast on its due date.
An overdue open bill is placed on the forecast `as_of` date.

The weekly formula is:

```text
closing balance =
opening balance
+ expected inflows
- expected outflows
```

Each week's closing balance becomes the next week's opening balance.

### Source coverage

This first Cash Flow slice only includes future sources that already have
reliable amount and date semantics in the backend.

Payroll is not yet included in the forecast because the current HR Payroll
model has a payroll period and an actual `disbursement_date`, but no dedicated
scheduled payment date for an unpaid payroll obligation.

Tax and statutory obligations are not yet included because there is no Finance
tax/statutory obligation source model or endpoint in this backend slice.

Those sources should be integrated when their authoritative due-date records
exist rather than hard-coding amounts or dates into Cash Flow Forecast.

## Native Finance Payroll

Finance owns a native payroll workflow. It does not import, wrap, copy, or write
the legacy `hr.Payroll` model or HR payroll API.

The only employee-side dependency is employee configuration from
`user.Employee`, including identity, branch, monthly salary, allowances, bank
details, and employment dates/status.

### Payroll data model

`PayrollRun` represents one company-wide or branch payroll period and owns the
workflow, approval and aggregate payment metadata.

`PayrollLine` represents one employee inside a payroll run. It snapshots the
employee identity, organisational context, bank details, configured base salary,
and calculated totals used for that period so historical payroll does not change
when the current employee profile changes later.

`PayrollLineItem` represents one earning or deduction that explains the
employee's gross pay, deductions, and net pay.

Employee-configured monthly salary and allowances are generated as
`source_type=employee` line items. Manual Finance adjustments use
`source_type=manual`. Future Commissions & Bonuses and Tax & Statutory work will
use the reserved `commission` and `statutory` source types rather than
overloading generic allowances/deductions.

### Payroll workflow

```text
Draft
  ↓ calculate
Calculated
  ↓ submit
Awaiting Approval
  ├─ reject → Rejected → correct/recalculate
  └─ approve
Approved
  ↓ pay from FinanceAccount
Paid
```

Unpaid runs may also be cancelled. Paid runs cannot be cancelled.

Calculation is currently monthly. Eligible employees must be active, have a
positive configured monthly `gross_salary`, and fall within the payroll
employment period. A branch payroll includes only employees assigned to that
branch.

A company-wide run and branch runs are mutually exclusive for the same payroll
month. This prevents employees from being paid twice through overlapping scopes.

Recalculation refreshes employee-sourced salary and allowance items while
preserving manual Finance adjustments already applied to employees who remain
eligible.

### API

```http
GET   /api/v1/finance/payroll
POST  /api/v1/finance/payroll
GET   /api/v1/finance/payroll/{run_id}
PATCH /api/v1/finance/payroll/{run_id}

POST  /api/v1/finance/payroll/{run_id}/calculate
PUT   /api/v1/finance/payroll/{run_id}/lines/{line_id}/manual-items
POST  /api/v1/finance/payroll/{run_id}/submit
POST  /api/v1/finance/payroll/{run_id}/approve
POST  /api/v1/finance/payroll/{run_id}/reject
POST  /api/v1/finance/payroll/{run_id}/pay
POST  /api/v1/finance/payroll/{run_id}/cancel
```

The public permission resource is `finance_payroll`, deliberately separate from
the legacy HR `payroll` permission resource.

Branch-scoped Finance Payroll roles can only access payroll runs explicitly
assigned to their permitted branches. Company-wide payroll runs remain hidden
from branch-scoped users because their detail includes employee compensation.

### Cashbook posting

An approved payroll run is paid from an active `FinanceAccount`. Payment marks
the run as paid and records the Finance account, payment timestamp, actor, and
reference.

Cashbook derives one posted payroll outflow from the paid `PayrollRun`. No
duplicate transaction table is introduced.

Because Cash Flow opening cash already reuses Cashbook actual-money sources, a
paid payroll automatically reduces later Cash Flow opening cash. Forecasting an
approved but not-yet-paid payroll as a future obligation is intentionally
deferred to the later People & Compliance / Cash Flow integration slice.

### Legacy HR payroll

The existing `/api/v1/payroll` HR routes remain untouched for compatibility,
but native Finance Payroll does not depend on them. No migration or data copy
from `hr.Payroll` is performed.

## Commissions & Bonuses

Finance owns employee incentive awards separately from Payroll calculation.

The frontend rule remains: commissions are calculated from **verified revenue
received**, subject to service-specific rules. The authoritative verified
revenue source in v1 is a confirmed `services.Payment`.

### Data model

`CommissionRule` defines a service-specific percentage, optional branch scope,
minimum verified revenue, effective period, and active/inactive status.

`IncentiveAward` represents either:

- a Commission calculated from one confirmed Payment and one Commission rule, or
- a manually created Bonus with an explicit reason and amount.

Commission creation is intentionally beneficiary-explicit. Current confirmed
Payment records know invoice/service/order/branch information but do not identify
which employee earned the sale. Finance therefore selects the employee, Payment,
and rule. The backend validates all three and snapshots verified revenue, rate,
service, branch, and calculated amount.

The same Payment + employee + rule cannot create the same Commission twice.

### Workflow

```text
Commission:
Confirmed Payment + Employee + Active Rule
        ↓ calculate
Pending Review
        ├─ reject → Rejected
        └─ approve
Approved
        ↓ next matching Finance Payroll calculation
Included In Payroll
        ↓ Payroll paid
Paid

Bonus:
Employee + Amount + Reason
        ↓
Pending Review
        ├─ reject → Rejected
        └─ approve
Approved
        ↓ Payroll
Included In Payroll
        ↓ Payroll paid
Paid
```

Commissions and bonuses do not post separate Cashbook outflows when paid through
Payroll. Their amounts become Payroll line items, and Cashbook records the single
Payroll outflow. This prevents double-counting cash.

If an unpaid Payroll run is cancelled, incentive awards that were included in it
return to Approved and can be picked up by a later run.

### API

```http
GET   /api/v1/finance/commission-rules
POST  /api/v1/finance/commission-rules
PATCH /api/v1/finance/commission-rules/{rule_id}
POST  /api/v1/finance/commission-rules/{rule_id}/deactivate

GET   /api/v1/finance/commissions
GET   /api/v1/finance/commissions/{award_id}
POST  /api/v1/finance/commissions/calculate
POST  /api/v1/finance/bonuses
POST  /api/v1/finance/commissions/{award_id}/approve
POST  /api/v1/finance/commissions/{award_id}/reject
```

The permission resource is:

```text
commissions:
list, view, create, update, calculate, approve, reject
```

There is deliberately no direct `pay` action in FIN-PC-2. Approved employee
incentives are paid through native Finance Payroll so employee compensation,
Cashbook, and later statutory calculations remain coherent.

Direct non-payroll incentive payment can be introduced later only if the
business requires a separate payout route.

## Tax & Statutory

Finance owns a durable statutory-obligation ledger. This slice does not hard-code tax law.

Safe automatic sources are explicit `VendorBill.withholding_tax` on paid vendor bills and explicit Payroll deduction line items categorized as `paye` or `pension`. VAT is supported as an obligation type, but `Invoice.tax_amount` is not automatically treated as final VAT payable because transaction tax is not necessarily the final remittance liability.

`StatutoryObligation` stores type, period, basis, amount, due date, branch, workflow, and remittance metadata. `StatutoryObligationItem` keeps source lineage and prevents a Vendor Bill or Payroll deduction from being imported twice.

Workflow: Draft → Pending Approval → Approved → Paid, with Reject and Void for unpaid records. Overdue is derived from due date.

Paid statutory obligations become Cashbook outflows. Vendor Bills with WHT now contribute net vendor cash paid to Cashbook; the withheld amount is paid separately when remitted, preventing double-counting.
