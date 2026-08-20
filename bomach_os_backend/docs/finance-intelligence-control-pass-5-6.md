# Finance Intelligence & Control — IC-5 + IC-6

## Scope

IC-5 completes permanent Finance audit history by reusing `user.AuditLog`.
IC-6 adds native CSV export for reports owned by the Finance Intelligence layer
and completes the report catalog integration.

No `FinanceAuditLog`, `FinanceException`, report-result or report-line table is
introduced.

## IC-5 — Permanent Finance Audit

`AuditLog.AuditType` now includes `finance_action`.

Finance audit events store structured metadata:

- area
- action
- entity type and ID
- reference
- branch ID/name when available
- amount when relevant
- event-specific details

The Finance app registers an explicit signal layer that records successful
workflow status transitions and posted Journal events. Because Django model
signals run inside the calling transaction, failed transactional Finance
workflows do not leave successful audit history behind.

The audit signal layer covers:

- manual, reversal and opening Journal posting
- confirmed client payments
- paid Expenses and Vendor Bills
- Petty Cash issue and retirement accounting events
- Payroll payment
- Statutory payment
- Fixed Asset capitalization, depreciation and disposal
- Vendor Bill approve/reject/void
- Expense approve/reject
- Petty Cash approve/reject/cancel
- Payment Submission rejection
- Payroll submit/approve/reject/cancel
- Statutory submit/approve/reject/void
- Finance Settings updates

Three workflows whose models do not store a dedicated actor field preserve the
actor on the in-memory model instance only for the duration of the save:
Vendor Bill void, Petty Cash cancel and Statutory void. No new database field is
introduced for that purpose.

API:

- `GET /api/v1/finance/audit`
- `GET /api/v1/finance/audit/export`

The existing generic Audit Log API remains unchanged.

## IC-6 — Reporting exports

Native CSV export is provided for:

- Profit & Loss
- Balance Sheet
- Revenue
- Expenses
- Payables Ageing
- Audit & Exceptions
- Permanent Finance Audit

API:

- `GET /api/v1/finance/reports/export?report_key=...`
- `GET /api/v1/finance/exceptions/export`
- `GET /api/v1/finance/audit/export`

The report catalog advertises an export endpoint only where a native export is
actually implemented. Existing Receivables, Project Profitability, Payroll,
Statutory and Wallet engines remain canonical and are not duplicated.

The catalog now contains `audit_exceptions`, which implements the prototype's
Audit & Exception Report.

## Permissions

`financial_reports`:

- view
- export

`finance_audit`:

- view
- export

Existing roles are not silently granted the new export actions.

## Migration

One `user` migration alters the `AuditLog.audit_type` choice metadata to include
`finance_action`.

No new table is created and the Finance model count does not change.

## Boundaries retained

- Bank Reconciliation API remains intentionally deferred.
- Formal historical Cash Flow Statement remains deferred.
- Budget vs Actual remains deferred until budget actual/commitment calculations
  are reliable.
- Scheduled report delivery remains deferred.
- PDF export remains deferred.
- Stored exception assignment/resolution workflow remains deferred.
