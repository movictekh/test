# FIN-AT-1 — Bank & Cash Accounts completion

## What was already there

Another engineer had already built the main Bank & Cash Account foundation. We kept it.

Before this pass, Bomach already had:

- `FinanceAccount` for bank and cash accounts;
- bank details, currency, branch, opening balance and active/inactive status;
- account create, list, update and deactivate endpoints;
- FinanceAccount links from payments, expenses, vendor bills, petty cash, payroll and statutory payments;
- Cashbook logic that calculates money in, money out and book/running balance.


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


## Database change


It adds one conditional uniqueness constraint to the existing FinanceAccount table and a migration data guard.





## review

> We kept the existing Bank & Cash Accounts implementation. FIN-AT-1 only adds controls needed before the General Ledger: duplicate physical bank accounts are blocked, historical account identity/opening balances cannot be silently rewritten after money moves, existing Cashbook balance is exposed read-only, account writes obey existing branch scope, and inactive Finance accounts cannot be selected for new expenses.