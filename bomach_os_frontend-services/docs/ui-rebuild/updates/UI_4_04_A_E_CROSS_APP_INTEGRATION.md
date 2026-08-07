# UI-4.04A–E — Cross-App Integration

## A — Internal record linking

The generic `/app/$section` route now validates record search parameters for
requests, quotations, invoices, approvals, orders, tasks, deliverables and
feedback.

Examples:

```text
/app/service-orders?order=ORD-260710-002
/app/execution-tasks?task=TSK-704
/app/deliverables?deliverable=DEL-701
/app/feedback-quality?feedback=FDB-003
```

`RecordLink` keeps visible prototype columns unchanged while making referenced
records navigable. Audit and notification surfaces resolve record destinations
through the same mapping.

## B — Notification API integration

Notification business logic remains backend-owned.

The old local `mockNotifications` source has been removed. `NotificationPanel`
uses TanStack Query and an API adapter. The exact backend notification contract
was not present in the current repository at implementation time, so endpoint
paths are configuration-only and have no invented defaults:

- `VITE_NOTIFICATION_LIST_PATH`
- `VITE_NOTIFICATION_MARK_READ_PATH` (`{id}` placeholder supported)
- `VITE_NOTIFICATION_MARK_ALL_READ_PATH`

Until those values are configured from the published backend contract, the
drawer reports that backend configuration is pending rather than generating
fake notifications.

The transport mapper is deliberately isolated and should be replaced by exact
OpenAPI-generated DTO mapping when the notification schema is finalized.

## C — Full audit instrumentation

The append-only mock audit store moved to `src/shared/audit` so older business
modules do not depend on the Experience & Intelligence UI module.

Major mutations now append audit events from their mock-domain layer:

- service creation/configuration and branch activation;
- request, quotation, approval, invoice and payment mutations;
- order, milestone, task and deliverable mutations;
- estate, plot and brokerage-property mutations;
- feedback and quality follow-up.

React components do not push audit rows directly.

## D — Permission-path regression

Backend permissions remain authoritative. A shared action-permission map
separates read access from write/decision capabilities.

Key action gates now cover:

- request/quotation/invoice creation;
- payment confirmation;
- approval decisions;
- order updates;
- task updates;
- deliverable creation/update;
- deliverable approval.

Read-only users can still open permitted records but do not receive the
corresponding mutation controls.

## E — Loading / empty / error review

Existing module pages already use shared `DashboardSkeleton`, `ErrorState`,
empty-register rows/cards and mutation toasts.

This slice additionally replaces the notification panel's local always-success
state with:

- loading skeletons;
- retryable backend error;
- explicit backend-contract-not-configured state;
- empty notification state;
- mutation pending state.

Feedback, Reports and Audit already include their own empty states, while
Commercial, Fulfillment, Service Administration and Specialized Services retain
their established page loading/error handling.
