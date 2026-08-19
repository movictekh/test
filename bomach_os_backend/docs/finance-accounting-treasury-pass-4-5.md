# FIN-AT-4 + FIN-AT-5 — Bank Reconciliation and Fixed Assets

This pass completes the adopted Accounting & Treasury eight-table foundation.

Exactly five durable Finance models are added: `BankReconciliation`, `BankStatementLine`, `BankReconciliationMatch`, `FixedAssetCategory`, and `FixedAsset`. Finance therefore moves from 18 models to exactly 23. No BankStatement header table, AccountingPeriod, DepreciationRun, DepreciationLine, generic asset transaction, statement-import, or matching-rules table is added.

## Bank reconciliation

The reconciliation itself owns statement header/period truth and belongs to an existing BANK `FinanceAccount` with a mapped bank `LedgerAccount`. Statement lines are external bank evidence; they do not replace Payments, Expenses, VendorBills, payroll, petty cash, or journal records.

`BankReconciliationMatch` links statement evidence to posted bank-ledger `JournalLine` movements and owns `matched_amount`, so partial, many-to-one, and one-to-many matching are supported. Bank credits/money-in reconcile to debits on the debit-normal bank Asset ledger; bank debits/money-out reconcile to credits.

A reconciliation can only be marked reconciled when statement arithmetic agrees, every statement amount is fully matched, and the adjusted statement balance equals the posted GL bank balance. Unmatched posted GL debits/credits remain valid reconciling items. Closed reconciliations are immutable. Auto-match is conservative and only creates a match when exact amount/direction plus date/reference rules leave exactly one candidate.

## Fixed assets

A fixed asset originates from an existing paid `Expense(cost_type=capital_expenditure)`. The Expense payment already posts DR Capital Expenditure Clearing / CR Bank-Cash. Capitalization then posts DR Fixed Asset Cost / CR Capital Expenditure Clearing. Multiple assets can originate from one Expense, but total capitalized cost cannot exceed that Expense amount.

The category stores reusable defaults. The FixedAsset snapshots adopted useful life, residual value, depreciation method, asset-cost ledger, accumulated-depreciation ledger, and depreciation-expense ledger so later category changes do not rewrite existing asset accounting.

Straight-line depreciation starts at the first full calendar month-end after capitalization. No depreciation-run table is created. Monthly journals use source event `depreciation:YYYY-MM` and cumulative-target rounding so the final total equals the exact depreciable amount. Book value and accumulated depreciation are derived from posted GL journals, not duplicated as mutable balances.

Disposal derives accumulated depreciation and posts cash/bank proceeds, accumulated depreciation, asset cost, and gain/loss as required. Generic reversal is blocked for `source_type="fixed_asset"` journals so workflow state cannot diverge from the GL.

Migration 0015 seeds 1610 Fixed Asset Cost, 1690 Accumulated Depreciation, 4200 Asset Disposal Gain, 6300 Depreciation Expense, and 6400 Asset Disposal Loss. Only disposal gain/loss receive new stable `LedgerAccount.system_role` values.

The installer runs Django system/migration checks, the focused FIN-AT-4+5 tests, and the Finance suite only. It does not run the project-wide 300+ suite, does not run Black, does not migrate the database, and leaves changes uncommitted.
