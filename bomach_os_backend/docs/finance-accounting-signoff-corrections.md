# Finance Accounting & Treasury — sign-off corrections

This correction pass is intentionally limited to features changed in FIN-AT-1 through FIN-AT-5. It does not refactor unrelated Finance or Services features.

## 1. Finance Account book balance now follows the General Ledger

FIN-AT-1 originally exposed the existing Cashbook balance because the General Ledger did not yet exist. FIN-AT-2/3 later made posted Journal Lines the durable accounting truth, and FIN-AT-5 introduced valid bank movements such as fixed-asset disposal proceeds that do not originate from the older Cashbook source list.

The Finance Account balance endpoint therefore now calculates book balance from the account's mapped Ledger Account:

- posted Journal Lines only;
- through the requested as-of date;
- debit movements increase a bank/cash Asset balance;
- credit movements decrease it.

The Cashbook is not rewritten. It remains the operational source view.

## 2. Branch-specific bank/cash ledgers require an exact journal branch

If a Finance Account belongs to a branch, a Journal Entry touching its mapped bank/cash Ledger Account must use that same branch. A branchless journal can no longer post into a branch-specific Finance Account.

Company-wide Finance Accounts remain compatible with company-wide journals.

## 3. Closed bank reconciliations protect historical bank accounting

Once a Bank Reconciliation is closed, a new Journal Entry cannot be posted to that bank's Ledger Account on or before the closed statement end date.

This prevents a later backdated journal or reversal from silently changing the General Ledger balance that a closed reconciliation proved.

This is a bank-specific close control; it does not add a general Accounting Period feature.

## 4. Reconciliation supports a first statement after historical activity

The first reconciliation no longer assumes that every older Journal Line without a Bomach reconciliation match is still outstanding.

Instead it:

1. calculates the posted book balance immediately before the statement start;
2. compares that balance with the external statement opening balance;
3. treats the difference as the opening reconciling position;
4. reduces that opening position when older General Ledger items clear on the current statement;
5. adds only unmatched General Ledger movements dated inside the current statement period as new closing outstanding items.

This allows reconciliation to begin at a real implementation date without recreating every historical bank statement.

## 5. Reconciliations are chronological and only one draft may exist per bank

A bank can have only one draft Bank Reconciliation at a time.

After a reconciliation exists, later reconciliations must be created after the latest statement end date. This prevents a later reconciliation from reserving General Ledger matches that an earlier reconciliation still needs.

Migration `0016_accounting_signoff_controls` adds a database uniqueness rule for one draft per Finance Account after first checking existing data.

## 6. Draft reconciliations can be discarded safely

A new explicit draft-discard endpoint is available:

`POST /api/v1/finance/bank-reconciliations/{reconciliation_id}/discard`

It uses the existing `bank_reconciliation:update` permission.

Only draft reconciliations can be discarded. Existing matches must be removed first. Statement lines without matches are deleted with the draft reconciliation.

Reconciled and closed records remain durable and cannot be discarded.

## 7. Fixed Asset depreciation cannot skip accounting months

Straight-line depreciation must now be posted for the next required month-end.

For example, if May is the first depreciation period, an August posting is rejected until May, June and July have been posted in order.

The existing cumulative-target rounding method is unchanged.

## 8. Fixed Asset residual value must be below acquisition cost

A residual value equal to acquisition cost creates a zero-depreciable asset that cannot naturally reach the fully-depreciated workflow state.

The supported straight-line model now requires:

`0 <= residual value < acquisition cost`

This matches the existing category rule that residual percentage must be below 100%.

## 9. Fixed-asset canonical ledger seed is verified without guessing

Migration `0016` verifies that the five fixed-asset ledger codes seeded by `0015` have the exact intended identity:

- code/name;
- account type;
- normal balance;
- parent;
- postable status;
- active status;
- system role.

If an existing deployment already uses one of those codes for something different, migration stops with a clear conflict instead of renaming, reactivating, or repurposing the account.

## Deliberately unchanged

This correction pass does not:

- add Accounting Period tables;
- add depreciation-run tables;
- add a reconciliation reopen workflow;
- redesign permissions;
- rewrite the Cashbook;
- change unrelated Services APIs;
- add new Finance business models.
