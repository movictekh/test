# ADR 0014: Service Operations Owns Reports API Source

- Status: Accepted
- Date: 2026-08-14

## Decision

Service lifecycle reports and their dedicated schemas are owned by Service Operations:

```text
domains/service_operations/api/v1/
├── routers/
│   └── reports.py
└── schemas/
    └── reports.py
```

Legacy paths are removed:

```text
services/api/v1/reports.py
services/api/schema/report_schemas.py
```

## Why Service Operations

The reports measure the Service Operations lifecycle:

- quote-to-order conversion;
- request response time;
- service margin;
- on-time delivery;
- per-service completion and revenue;
- branch request/order/revenue/SLA/CSAT performance.

The gross-service-margin KPI reads Expense data. That is a cross-domain read, not a transfer of
Expense ownership. Finance remains the long-term owner of Expense.

## Compatibility

ARCH-5H preserves paths, methods, tags, parameters, request/response shapes, security, RBAC,
CSV export behavior, model identity, and migration state. Generated OpenAPI operation IDs are
not treated as a hard compatibility boundary because this project does not generate SDK clients.
