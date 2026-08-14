# ADR 0025: Extract Business Complexity, Not Trivial Persistence

- Status: Accepted
- Date: 2026-08-14

Service Operations does not ban Django ORM from routers. Simple endpoint-local reads and truly
trivial CRUD may remain local when another layer would only add ceremony.

Application services are required for meaningful business operations involving transactions,
state transitions, multi-model mutation, workflow/activity history, cross-domain coordination,
business validation, or notification/email side effects.

This batch moves Service Request, Quote and Invoice lifecycle orchestration into:

```text
services/requests.py
services/quotes.py
services/invoices.py
```

`_service_request_support.py` is reduced toward transport support; touched API modules are also
cleaned of imports made dead by the extraction.

The batch preserves routes, methods, schemas, RBAC, explicit operation IDs, OpenAPI and Django
migration/model identity. Finance endpoint implementation is not changed. PaymentSubmission
creation remains an explicit transitional integration until Finance ownership migration is
coordinated.
