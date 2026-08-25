# Finance transaction source ownership

This package owns monetary transaction models whose historical Django app
identity remains outside the `finance` Django app.

Canonical source ownership:

- `finance.transactions.payment.Payment`
  - Django identity remains `services.Payment`
  - commercial `Invoice` remains Service Operations-owned
- `finance.transactions.expense.Expense`
  - Django identity remains `services.Expense`
  - `Expense.date` remains the accounting/business date
  - `paid_at` remains payment/workflow timestamp metadata
- `finance.transactions.payment_submission.PaymentSubmission`
  - Django identity remains `user.PaymentSubmission`
  - represents payment evidence submitted for Finance review/confirmation

This is source convergence, not model replacement. Existing tables, migrations,
URLs, accounting behavior, workflow behavior and public legacy imports remain
compatible.

The old `services.Budget` is intentionally not moved: it was deleted by
`services.0038_delete_budget`. The live Finance planning model is
`finance.FinanceBudget`.
