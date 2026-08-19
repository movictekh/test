# FIN-AT-2 + FIN-AT-3 — Chart of Accounts, Journals & General Ledger

## Why these passes are combined

A General Ledger cannot work without a Chart of Accounts. This implementation therefore adds the COA and journal engine together so the complete chain can be tested in one pass:

`FinanceAccount -> LedgerAccount -> JournalEntry -> JournalLine`

The table rule remains strict: a table must own independent durable business truth.

## New business tables — exactly three

### 1. LedgerAccount

This is the Chart of Accounts. It is not a replacement for `FinanceAccount`.

- `FinanceAccount` means a real bank/cash location.
- `LedgerAccount` means an accounting classification such as Revenue, Payroll Expense or Statutory Payable.

`normal_balance` is stored because future contra accounts (for example accumulated depreciation) can have a normal balance opposite to their broad account type.

`system_role` is stored directly on the LedgerAccount. We deliberately do not add an `AccountingControlAccount` table. A separate mapping table would only be justified later if control roles genuinely vary by branch, currency or another business dimension.

Parent accounts are non-postable. Hierarchy cycles are blocked. Structural accounting fields become immutable after posted activity exists in the account or its descendants. `system_role` is deliberately movable because it controls future automatic posting and does not rewrite historical journal lines.

### 2. JournalEntry

Owns the accounting event/header: date, currency, type, status, branch, reference, source identity and posting audit fields.

Automatic source identity is `source_type + source_id + source_event`. A database uniqueness rule makes retries idempotent.

Each journal has one currency. Trial balance requires a currency, so NGN/USD/etc are never silently added together.

### 3. JournalLine

Owns each debit/credit allocation.

A line must contain exactly one positive debit or one positive credit. The database enforces that rule. Posting service enforces that the complete journal balances.

This supports N-line journals such as payroll and WHT. We do not store lines in JSON and do not force every journal into one debit/one credit.

## Additional accounting controls from the clean-rebuild audit

The post-implementation audit tightened controls that are necessary for accounting integrity:

- FinanceAccount mappings must stay inside the canonical `1100 Cash & Bank` tree and must be active, postable, debit-normal Asset accounts.
- A system role can only sit on its compatible account type and normal balance; for example `service_revenue` must be credit-normal Revenue.
- A parent that owns child accounts cannot be made postable, and structural fields of any tree containing a mapped Finance account are locked.
- A reversal cannot be dated before the journal it reverses.
- Partial-payment tax uses cumulative invoice-level rounding so the fully-paid invoice reconciles exactly to its stored tax amount.

## Posted journal control

Manual journals begin as draft.

Posting is only allowed through the accounting posting service. The service checks:

- at least two lines;
- active postable accounts;
- cash-ledger branch/currency compatibility;
- total debits equal total credits.

After posting, JournalEntry and JournalLine are immutable. Corrections use a reversal journal.

## FinanceAccount mapping

`FinanceAccount` gets one required relationship: an optional one-to-one `ledger_account`.

Migration 0013 maps existing Finance accounts to dedicated Asset ledger accounts under `1100 Cash & Bank`.

New Finance accounts created through the existing API receive their dedicated ledger account atomically.

A Finance account with a non-zero dated opening balance also posts an opening journal immediately:

- DR mapped Cash/Bank ledger
- CR Opening Balance Equity

Once posted cash-ledger activity exists, the Pass-1 historical identity/opening-balance lock recognizes it. The ledger mapping itself also cannot be switched after posted activity.

## Canonical COA seed

The seed is intentionally small rather than a giant ERP chart. It creates only the accounts required now:

- Assets / Cash & Bank
- Accounts Receivable
- Employee Receivables
- Petty Cash Advances
- Capital Expenditure Clearing
- Fixed Assets parent (for Pass 5)
- Liabilities
- Accounts Payable
- Payroll Deductions Payable
- Statutory Payable
- Equity / Opening Balance Equity
- Revenue / Service Revenue
- Direct Costs / Service Cost Expense
- Operating Expenses / Operating Expense / Payroll Expense

Finance can add normal LedgerAccount rows through the API.

## Automatic GL posting policy

No Django signals are added. Posting stays explicit inside the repository's existing atomic state-change services.

### Confirmed client payment

- DR mapped bank/cash ledger
- CR Service Revenue
- CR Statutory Payable for the deterministic cumulative invoice-tax component

This follows the repository's existing settled-payment semantics. The system does not invent an invoice-accrual transition that the current application does not yet own.

### Paid expense

- DR Service Cost Expense for service/direct costs, or
- DR Operating Expense for ordinary operating costs, or
- DR Capital Expenditure Clearing for capital expenditure
- CR mapped bank/cash ledger

Capital expenditure stays in an Asset clearing account until Pass 5 determines the fixed-asset capitalization details.

### Paid vendor bill

- DR appropriate expense for gross cost
- CR mapped bank/cash for net cash paid
- CR Statutory Payable for WHT retained

### Petty cash issue

- DR Petty Cash Advances
- CR mapped cash ledger

### Petty cash retirement

Spend:
- DR appropriate expense
- CR Petty Cash Advances

Returned cash:
- DR mapped cash ledger
- CR Petty Cash Advances

### Paid payroll

- DR Payroll Expense for gross payroll
- CR bank/cash for net pay
- CR Statutory Payable for PAYE/pension/statutory deductions
- CR Employee Receivables for loan/advance recoveries
- CR Payroll Expense for absence deductions (contra payroll cost)
- CR Payroll Deductions Payable only for remaining unclassified deductions

This avoids incorrectly treating employee loan recoveries as liabilities.

### Paid statutory obligation

- DR Statutory Payable
- CR mapped bank/cash

Generated WHT/payroll liabilities are already recognized by their underlying cash/payroll postings. A manually-created statutory obligation may require a separate manual/accrual journal before payment; this pass does not guess the correct expense/revenue side for every statutory assessment.

## Direct Services payment path

The repository also has a direct `/payments` endpoint outside the Finance router. It is a real cash-creation path, so this pass brings it under the same controls:

- branch-scoped invoice/account selection;
- active Finance account;
- no overpayment beyond invoice balance;
- Payment + GL journal in one atomic transaction.

Recorded Payments are no longer deleted through the ordinary delete endpoint because deleting a settled cash source would break audit history. Corrections require a controlled reversal/correction workflow.

Invoices that already have recorded Payments also cannot be deleted through the invoice endpoint, preventing Django's existing cascade relationship from deleting settled Payment source rows.

## Expense source integrity

The older Services expense API could create a non-pending expense, update an already settled expense, or delete approved/paid records. That would allow source data to diverge from the new GL.

This pass narrows that API to the same workflow rules already used by the Finance expense API:

- new expenses start pending;
- only pending expenses can be edited;
- workflow status changes use approve/reject/pay actions;
- only pending/rejected expenses can be deleted.

## Cashbook alignment

Cashbook remains the operational actual-cash view; General Ledger becomes durable double-entry truth.

One concrete Cashbook defect is corrected: paid expenses now use `paid_at.date()` for cash movement when available, falling back to `Expense.date` only for legacy rows without a payment timestamp. This prevents as-of Cashbook and GL balances disagreeing merely because one used the expense date and the other used the payment date.

## Historical GL backfill

Command:

`python manage.py backfill_finance_gl --dry-run --strict`

It uses the same idempotent posting functions for existing settled records and opening balances. It never changes the source operational records.

`--dry-run` rolls all accounting writes back after validation.

`--strict` refuses to guess a historical date for a non-zero opening balance that has no `opening_balance_date`.

After deployment review, the real backfill can be run with:

`python manage.py backfill_finance_gl --strict`

The installer itself does **not** run the backfill and does **not** run `migrate` against the developer's local database.

## APIs added

Chart of Accounts:

- GET/POST `/api/v1/finance/ledger-accounts`
- GET/PATCH `/api/v1/finance/ledger-accounts/{account_id}`
- POST `/api/v1/finance/ledger-accounts/{account_id}/deactivate`
- POST `/api/v1/finance/accounts/{account_id}/ledger-account`

Journals:

- GET/POST `/api/v1/finance/journals`
- GET/PATCH `/api/v1/finance/journals/{journal_id}`
- POST `/api/v1/finance/journals/{journal_id}/post`
- POST `/api/v1/finance/journals/{journal_id}/reverse`

Ledger reporting:

- GET `/api/v1/finance/general-ledger` — posted lines with per-account running balance in one requested currency
- GET `/api/v1/finance/trial-balance`

Permissions added:

- `chart_of_accounts`
- `journals`
- `general_ledger`

## What is deliberately not added

- AccountingControlAccount
- AccountingPeriod
- BankReconciliation
- BankStatementLine
- BankReconciliationMatch
- FixedAssetCategory
- FixedAsset
- DepreciationRun
- DepreciationLine

After this pass the Accounting & Treasury roadmap remains eight new business tables total:

1. LedgerAccount
2. JournalEntry
3. JournalLine
4. BankReconciliation
5. BankStatementLine
6. BankReconciliationMatch
7. FixedAssetCategory
8. FixedAsset

Finance model count moves from 15 to exactly 18 in this combined pass.
