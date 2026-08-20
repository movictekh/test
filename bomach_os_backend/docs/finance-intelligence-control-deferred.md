# Finance Intelligence & Control — Deferred Scope

This document records Intelligence & Control features intentionally deferred
after IC-1 through IC-4. They are deferred because a prerequisite, policy
decision or separate workflow is still required. They are not accidental
omissions.

## Formal historical Cash Flow Statement

Deferred.

The existing Finance cash-flow module is a liquidity forecast, not an accounting
Statement of Cash Flows. A formal statement requires deterministic
classification of every relevant cash movement into operating, investing and
financing activities, including manual Journals, loans, equity transactions,
inter-account transfers and future transaction types.

A Cash Movement view may be built earlier, but it should not be labelled a
formal Cash Flow Statement until that classification policy exists.

## Budget vs Actual

Deferred until the Budgets & Controls implementation calculates real spent and
committed amounts.

The current `FinanceBudget.spent` and `FinanceBudget.committed` behavior is not
yet a reliable accounting source for a Budget vs Actual financial report.
Building the report before fixing that prerequisite would produce misleading
results.

## Scheduled report delivery

Deferred.

A real implementation requires durable schedules, recipient configuration, an
execution runner, delivery history and failure handling.

A future `FinanceReportSchedule` table is justified only when that scheduling
and delivery workflow is implemented.

## Report exports

CSV/PDF export remains deferred to the later reporting/export batch. The
financial calculations and canonical report-source catalog are established
first.

## Permanent Finance audit history

Deferred to IC-5.

The permanent history should reuse the existing `user.AuditLog` infrastructure
rather than create a duplicate Finance audit table. IC-4 introduces the shared
`finance_audit:view` permission family but does not yet instrument Finance state
changes into the permanent audit history.

## Exception workflow state

IC-4 calculates exceptions dynamically and does not store them.

Assignment, acknowledgement, resolution notes, suppression, ownership and
exception-history tracking remain deferred. A durable exception model is only
justified if those workflow requirements become real.

## Accounting-source integrity exceptions

Deferred until a deliberate historical cutover boundary is defined.

Examples include a paid source record with no expected posted accounting
Journal. Those checks are useful, but legacy records created before General
Ledger automation must not be mislabelled as current accounting failures.

## Unmatched bank items

Deferred with the Bank Reconciliation product workflow.

Bank Reconciliation backend code remains preserved, but its public API is
intentionally not exposed while external bank-transaction ingestion and the
intended user workflow are still undecided.

The Exception Centre therefore does not create an alternate unmatched-deposit
workflow.

## Multi-currency Vendor Bills

Deferred.

`VendorBill` currently has no currency field. IC-3 Payables Ageing reports the
company default currency and returns an explicit currency-basis explanation.
A future multi-currency payables design must define bill currency, settlement
currency and exchange-rate behavior before the report can claim mixed-currency
support.

## Budget blocking

Deferred until Budget actual and committed calculations are reliable.

A setting such as "block expenses above available budget" must not be exposed
until the system can correctly calculate available budget and the affected
expense workflow actually enforces the rule.

## Expense attachment requirement

Deferred.

This may become a valid Finance policy, but the setting and enforcement must be
implemented together. A checkbox that is not enforced by the Expense workflow
would be misleading.

## Two-approval monetary threshold

Deferred.

This requires a deliberate multi-step Finance approval-policy design. The
current generic workflow-rule infrastructure does not by itself implement a
financial two-approver control.

## Accounting-basis switch

Deferred.

The system does not currently contain complete parallel cash-basis and
accrual-basis posting engines. An "Accrual / Cash" dropdown would therefore
misrepresent accounting behavior.

## Invoice and Expense prefixes

Deferred from Finance Settings.

Invoices and Expenses are currently owned by the Services domain and already
have numbering behavior. Their numbering should only move into configurable
policy through a deliberate cross-domain decision.

## Reopening closed accounting

Deferred.

IC-1 introduced a safe monotonic `closed_through_date`: Finance can close more
history, but cannot silently reopen it.

If reopening is later required, it should have explicit permission, audit
history and a reason/approval workflow. A future `AccountingPeriod` model may be
appropriate if Bomach needs individual period states, soft/hard close,
reopening approvals or year-end close workflows.
