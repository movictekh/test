# Finance Postman Assets

Files in this folder:

- `finance-worked-features.postman_collection.json`
- `finance-worked-features.postman_environment.json`

What this covers:

- auth bootstrap for the dedicated Postman users
- scoped role mutation for finance permission checks
- finance settings
- financial reports
- finance audit and exceptions
- cash-flow forecast
- finance accounts
- chart of accounts
- journals, general ledger, and trial balance
- payroll lifecycle
- statutory obligation lifecycle
- bonus-based commission lifecycle
- fixed asset lifecycle

What it does not treat as a normal success path:

- bank reconciliation
  - production does not mount the reconciliation router
- commission calculation from a confirmed payment
  - the collection includes an optional request for it
  - it only succeeds when the production database already has a usable confirmed payment and service

Dedicated production users created for this collection:

- control user: `postman.finance.admin@bomach.local`
- subject user: `postman.finance.subject@bomach.local`
- password for both: `Postman123!`

Dedicated production role used by the collection:

- `Postman Finance Scoped Role`

How to regenerate the collection files:

```bash
cd /home/kachy/project/bomach/bomach_os_backend
.venv/bin/python scripts/postman/generate_finance_worked_collection.py
```

How to run in Postman:

1. Import `finance-worked-features.postman_collection.json`
2. Import `finance-worked-features.postman_environment.json`
3. Select the imported environment
4. Make sure the backend is running at the environment `base_url`
5. Run the collection from the Collection Runner in folder order

Recommended run order:

1. `00 Bootstrap`
2. `01 Permission Checks`
3. `02 Finance Settings, Reports, Exceptions, Audit, Cash Flow`
4. `03 Accounts And Chart Of Accounts`
5. `04 Journals And General Ledger`
6. `05 Payroll And Statutory`
7. `06 Commissions And Fixed Assets`
8. `99 Cleanup`

Notes:

- The collection is stateful by design. Later folders depend on IDs created by earlier folders.
- If you want a clean rerun, execute `99 Cleanup` at the end.
- If the optional commission calculation request reports missing prerequisites, that is a production data availability issue, not a collection wiring issue.
