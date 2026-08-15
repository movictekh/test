# ADR 0027: Service Operations Workflow Boundaries

- Status: Accepted
- Date: 2026-08-15

Simple endpoint-local reads and straightforward single-record CRUD may remain in routers.

Application services own transactions, state transitions, multi-model writes, history/activity
creation, and workflow progression.

`services/catalogue.py` owns request-form, pricing-config and workflow lifecycle orchestration.
Individual workflow-stage CRUD remains in the router.

`services/orders.py` owns order update side effects, activities, milestone progression, task
lifecycle, deliverable lifecycle, client deliverable decisions, and manual-order creation
transaction boundaries.

No new folders or architectural layers are introduced.
