# Finance Intelligence & Control — IC-1 + IC-2

This pass adds the Finance Settings foundation and the first four accounting
financial reports. It deliberately builds on posted General Ledger truth rather
than creating report-result tables.

## IC-1 — Finance Settings

A single company-wide `FinanceSettings` record now owns typed Finance policy:

- financial year start month;
- accounting books closed-through date;
- journal-number prefix;
- draft-journal warning age;
- optional large manual-journal review threshold.

The existing `CompanyPreferences.default_currency` remains the company default
currency. Finance does not store a duplicate currency setting.

### Accounting close

`closed_through_date` blocks posting any Journal Entry dated on or before the
configured close date. This applies through the central journal-posting service,
so manual, automatic, opening, reversal and other posting flows share the same
control.

The close date may advance, but this pass does not allow it to be cleared or
moved backward. Reopening closed accounting is intentionally deferred to a
separate controlled workflow.

### Journal numbering

Only newly created Journal Entries use the current `journal_prefix`. Historical
journal numbers are never renamed when the setting changes.

### API

- `GET /api/v1/finance/settings`
- `PATCH /api/v1/finance/settings`

Finance Settings require the new `finance_settings` permission and company-wide
role scope.

## IC-2 — Core Financial Statements

Four read-only accounting reports are added:

- Profit & Loss Statement;
- Balance Sheet;
- Revenue Report;
- Expense Report.

They read posted `JournalLine` records only. Draft Journals do not affect
financial statements.

All four support Finance permission branch scope and an optional explicit
branch. Currency defaults to `CompanyPreferences.default_currency` when the
caller does not supply one.

Profit & Loss, Revenue and Expense default to the configured financial year
through the current date.

### Balance Sheet treatment

The Balance Sheet calculates signed balances by accounting type. A credit-normal
Asset such as Accumulated Depreciation reduces total Assets instead of being
added as a positive Asset.

Because Bomach does not yet have a year-end closing process that transfers
Revenue and Expense balances into retained earnings, the report shows
`cumulative_earnings` as a calculated Equity component:

`cumulative revenue - cumulative expenses`

No synthetic Journal Entry is created for reporting.

## Permissions

This pass adds:

- `finance_settings`: `view`, `update`
- `financial_reports`: `view`

The generic Services `reports` permission is not reused for confidential
financial statements.

## Database and API shape

This pass adds exactly one Finance business model: `FinanceSettings`.

It does not add Profit & Loss, Balance Sheet, report-line, report-result or
exception tables.

The Finance model count moves from 23 to 24.

Six public API operations are added:

- Finance Settings GET;
- Finance Settings PATCH;
- Profit & Loss GET;
- Balance Sheet GET;
- Revenue Report GET;
- Expense Report GET.

## Validation

The installer runs:

- Django system check;
- migration-drift check;
- targeted Black formatting/check for only the Python files in this pass;
- focused IC-1/IC-2 tests;
- the complete Finance test suite;
- API-operation and Finance-model-count guards;
- exact changed-path guard.

The full project test suite is intentionally not run during this Finance
implementation pass.
