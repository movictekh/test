# FIN-AT-1 — Bank & Cash Accounts completion

## What was already there

Another engineer had already built the main Bank & Cash Account foundation. We kept it.

Before this pass, Bomach already had:

- `FinanceAccount` for bank and cash accounts;
- bank details, currency, branch, opening balance and active/inactive status;
- account create, list, update and deactivate endpoints;
- FinanceAccount links from payments, expenses, vendor bills, petty cash, payroll and statutory payments;
- Cashbook logic that calculates money in, money out and book/running balance.

We did not rewrite those working parts just to make them look different.

## Change 1 — stop duplicate physical bank accounts

For bank accounts, `bank_name + account_number` is now unique.

Why: one real bank account must not exist as two FinanceAccount rows. If it does, payments can be split between the rows and Bomach can show two different balances for one real bank account. Reconciliation and the future General Ledger would then have no reliable account identity.

Migration `0011_bank_cash_account_controls` checks existing data first. If duplicates already exist, it stops and lists them. It does not guess which record should be deleted or merged.

## Change 2 — protect historical account identity after money moves

After settled financial activity exists, these fields cannot be changed:

- account type;
- currency;
- branch;
- bank name;
- bank account number;
- opening balance;
- opening balance date.

Why: these fields explain where historical money was held and what the account started with. Changing them later silently changes the meaning of old transactions.

The opening balance is especially important. Changing it after transactions exist changes every later calculated balance without creating any visible correction entry.

Fields such as display name, account holder/name text, notes and active/inactive status can still be changed because they do not rewrite the historical cash calculation.

## Change 3 — expose the existing book balance

New endpoint:

`GET /api/v1/finance/accounts/{account_id}/balance`

It returns the account's current/as-of book balance.

Why: the Finance Bank & Cash Accounts screen needs a Book Balance, but the existing account endpoint only returned the stored opening balance.

We did not create a new stored balance column. The endpoint reuses the existing Cashbook calculation so there is still one current operational cash-movement calculation.

## Change 4 — enforce existing branch scope on account writes

The account list was already branch-scoped, but create/update/deactivate were not consistently using that scope.

This pass now prevents a branch-restricted user from:

- selecting another branch when creating an account;
- changing another branch's account by ID;
- deactivating another branch's account by ID;
- creating a branchless/company-wide Finance account;
- clearing the branch on an allowed account and turning it company-wide.

Why: bank and cash accounts are Treasury control records. Branch access must apply to writes as well as lists.

This reuses the existing `scope_queryset` permission mechanism. It does not introduce a new authorization framework.

## Change 5 — inactive accounts cannot be selected for new expenses

During the audit we checked the existing real-money Finance flows.

Vendor bills, petty cash, payroll, statutory payment and confirmed-payment handling already require active Finance accounts.

The expense account lookup was the exception. It checked account ID and branch scope but did not require `is_active=True`.

This pass adds that one missing active-account check.

Why: after Treasury deactivates an account, new financial activity should not keep using it.

We did not refactor the expense workflow.

## Change 6 — focused tests

A new file `finance/tests/test_bank_cash_accounts.py` checks:

- duplicate bank-account prevention;
- historical opening balance/account identity locking;
- descriptive edits still working;
- opening balance correction before any activity;
- Cashbook-backed book balance;
- branch scope for update/deactivate;
- branch scope for account creation;
- prevention of branch-scoped company-wide accounts;
- prevention of clearing branch scope;
- rejection of inactive Finance accounts for new expenses.

The existing large `finance/tests/test_core.py` is not reorganized.

## Database change

This pass creates no new business table.

It adds one conditional uniqueness constraint to the existing FinanceAccount table and a migration data guard.

## Things we intentionally did not change

### FinanceAccount was not moved or renamed

The model already works and many Finance features depend on it.

### The accounts router was not rewritten into a service layer

That would be an architecture preference, not a requirement for this pass.

### Existing `payments` permission names were not renamed

The naming may later deserve a dedicated Treasury permission design, but changing it now would alter existing role behavior and is not necessary for these controls.

### Cashbook was not rewritten

The balance endpoint deliberately reuses it.

### Statement balance and reconciliation status were not added

Those values require real imported bank statements and reconciliation records. They belong to the Bank Reconciliation pass.

### Chart of Accounts / General Ledger fields were not added

The FinanceAccount-to-LedgerAccount relation belongs in the Chart of Accounts pass when `LedgerAccount` actually exists.

## Why the first three installers stopped

### Installer 1

It assumed the local SQLite database had the FinanceAccount table and queried it directly.

The local database did not have that table, so it stopped with `no such table: finance_financeaccount`.

Rollback completed.

### Installer 2

It correctly handled the missing local table, but added `FinanceAccountBalanceOut` only in `finance/api/schemas/accounts.py`.

This repository imports Finance schemas through `finance/api/schemas/__init__.py`, so the new schema was not visible through the existing import path.

Rollback completed.

### Installer 3

It fixed the schema export but its new smoke test used plain `python` to import Django Ninja code before Django settings were configured.

That caused `ImproperlyConfigured: Requested settings, but settings are not configured`.

Rollback completed.

## What v4 changes about installer validation

v4 fixes the validation method instead of only fixing the latest error:

- it runs `python manage.py check` before editing;
- it checks migration drift before editing;
- it runs the full existing Django test suite before editing;
- local database row checks only run when the FinanceAccount table exists;
- it never runs `migrate`;
- Django-aware imports run through `manage.py` or explicitly configured Django;
- migration `0011` contains its own duplicate-data guard;
- after editing it runs import checks, Django checks, migration checks, focused tests, Finance tests and the full test suite;
- it compares the public API operation set before/after;
- it confirms no new Finance model was introduced;
- every touched existing file is included in rollback.

## Short explanation for review

> We kept the existing Bank & Cash Accounts implementation. FIN-AT-1 only adds controls needed before the General Ledger: duplicate physical bank accounts are blocked, historical account identity/opening balances cannot be silently rewritten after money moves, existing Cashbook balance is exposed read-only, account writes obey existing branch scope, and inactive Finance accounts cannot be selected for new expenses. We did not move the model, rewrite the router, rename permissions or replace Cashbook.
