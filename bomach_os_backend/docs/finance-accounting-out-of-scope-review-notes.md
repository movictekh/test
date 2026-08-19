# Finance Accounting review — documented observations outside the correction scope

These notes came from the sign-off review, but they are not part of the FIN-AT correction implementation. They should be considered in the appropriate future audit rather than patched into Accounting & Treasury without a dedicated scope.

## 1. Broader legacy Services branch-access consistency

The repository has older Services payment, expense and invoice endpoints in addition to the newer Finance-facing endpoints.

The Accounting & Treasury passes touched only the portions required to protect accounting source records and real-money creation paths. A complete branch-authorization review of every older Services list/detail/update route is broader than FIN-AT and should be handled as its own access-control audit.

No broad Services authorization rewrite is included in this correction pass.

## 2. Optional direct-model opening-balance hardening

Normal Finance Account creation with a non-zero opening balance already requires a dated opening-balance journal, and the historical General Ledger backfill reports legacy accounts that have a non-zero opening balance without a date.

A future defensive-hardening pass could also require `opening_balance_date` directly in `FinanceAccount.clean()` whenever `opening_balance` is non-zero. This is not required for the current API/accounting workflow and is not changed here.

## 3. Optional Fixed Asset ledger dependency hardening

Fixed Asset categories and assets validate their accounting ledgers when they are created, and journal posting refuses inactive/non-postable Ledger Accounts.

A future administration-control pass could additionally prevent deactivation of a Ledger Account while active Fixed Asset categories/assets depend on it. The current system fails safely at posting rather than silently using an invalid ledger, so this is documented rather than added to this correction pass.

## 4. Future workflow enhancements, not current defects

The following are possible future workflow enhancements, not missing requirements in FIN-AT:

- reopening a reconciled-but-not-closed Bank Reconciliation;
- automatic multi-month catch-up depreciation that creates one journal per missed month;
- a general Accounting Period close feature across all Ledger Accounts.

They should only be added when the business workflow explicitly requires them.
