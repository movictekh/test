# ADR 0013: Service Operations Owns Feedback API Source

- Status: Accepted
- Date: 2026-08-14

## Decision

Feedback attached to completed or active Service Orders belongs to Service Operations.

The router and dedicated schema move to:

```text
domains/service_operations/api/v1/
├── routers/
│   └── feedback.py
└── schemas/
    └── feedback.py
```

Legacy paths are removed:

```text
services/api/v1/feedback.py
services/api/schema/feedback_schemas.py
```

## Why Service Operations

Client Feedback is explicitly tied to `ServiceOrder` and measures delivered-service outcomes
such as rating, satisfaction and rework. It is therefore part of the Service fulfilment
lifecycle rather than a generic CRM object.

## Model source

This ADR does not yet move `ClientFeedback` model source. Model-source ownership is handled in
the later guarded Service Operations model migration so Django app labels and migrations remain
stable.

## Compatibility

ARCH-5G preserves:

- Feedback paths and methods;
- request/response schemas;
- tags and security;
- permission behavior;
- database model identity and migration state.

Generated OpenAPI operation IDs are not a hard compatibility boundary because no SDK is generated
from Swagger/OpenAPI.
