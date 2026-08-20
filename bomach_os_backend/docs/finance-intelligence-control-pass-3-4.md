# Finance Intelligence & Control — IC-3 + IC-4

This pass adds the next two Intelligence & Control capabilities on top of the
validated IC-1 + IC-2 Finance Settings and core financial statements work.

The implementation deliberately reuses existing Finance calculations instead of
creating competing report engines or storing calculated exception rows.

## IC-3 — Ageing and existing Finance report integration

### Report catalog

A new read-only report catalog exposes the canonical backend source for each
Financial Reports card.

Available report sources include:

- Profit & Loss Statement;
- Balance Sheet;
- Revenue Report;
- Expense Report;
- Trial Balance;
- General Ledger;
- Receivables Ageing;
- Payables Ageing;
- Project Profitability;
- Payroll;
- Tax & Statutory;
- Wallet Statement.

The catalog records the canonical endpoint and permission for each report.
Existing calculations remain owned by their current modules; they are not copied
into a second reporting implementation.

Formal Cash Flow Statement and Budget vs Actual remain marked as deferred with
an explanation of the missing prerequisite.

### Payables Ageing

A new Payables Ageing report calculates current open Vendor Bills using the same
age buckets already familiar from Receivables:

- current;
- 1-30 days overdue;
- 31-60 days overdue;
- 61-90 days overdue;
- 90+ days overdue.

Only open payable states are included: awaiting approval, approved and
scheduled. Paid, rejected, void and draft bills are excluded.

Branch permission scope is respected using the Vendor Bill branch, linked
Service Order branch or payment Finance Account branch.

`VendorBill` currently has no currency field. The report therefore labels its
amounts using the company default currency and explicitly returns a
`currency_basis` explanation. Multi-currency Vendor Bills are not silently
invented in this pass.

## IC-4 — Exception Centre

The Exception Centre is read-only and calculated from current Finance truth.
There is no `FinanceException` table.

The first deterministic exception rules are:

1. manual Journal remaining draft beyond `FinanceSettings.draft_journal_warning_days`;
2. draft manual Journal at or above the optional
   `large_manual_journal_review_threshold`;
3. overdue open Vendor Bill;
4. active Fixed Asset whose next required depreciation period is overdue.

The Fixed Asset rule reuses the existing depreciation schedule so it follows the
same first-full-month and continuity rules as actual depreciation posting.

### Severity

This pass intentionally uses conservative severity:

- overdue/incomplete workflow controls are `warning`;
- large draft manual Journal review is `info`;
- `critical` is reserved for future accounting-integrity mismatches where two
  sources of financial truth materially disagree.

This prevents routine operational ageing from being overstated as an accounting
failure.

### API operations

This pass adds exactly four public operations:

- `GET /api/v1/finance/reports/catalog`
- `GET /api/v1/finance/reports/payables-ageing`
- `GET /api/v1/finance/exceptions`
- `GET /api/v1/finance/exceptions/summary`

The Exception Centre uses the new `finance_audit:view` permission family. The
same family can later govern the permanent Finance audit history in IC-5.

## Database impact

No new model or migration is introduced.

IC-3 and IC-4 are calculated/read-only Intelligence features over existing
business records.

## What this pass does not do

It does not:

- duplicate Receivables or Project Profitability calculations;
- build a formal historical Cash Flow Statement;
- build Budget vs Actual before budget actual/commitment data is reliable;
- store exception rows;
- add assignment, acknowledgement or resolution workflow for exceptions;
- expose Bank Reconciliation again;
- generate unmatched-bank exceptions;
- build the permanent Finance audit history;
- add report scheduling or exports.
