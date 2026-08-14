# ADR 0012: Service Operations Owns the Service Invoices API Source

- Status: Accepted
- Date: 2026-08-14

## Decision

The service-facing Invoice HTTP router is owned by Service Operations:

```text
domains/service_operations/api/v1/routers/invoices.py
```

The legacy router path is removed:

```text
services/api/v1/invoices.py
```

This router represents the commercial/service lifecycle attached to Service Requests and
Quotes:

```text
Service Request
  -> Quote
  -> Service Invoice
  -> payment threshold
  -> Service Order
```

## Finance boundary

This is not the same thing as transferring Finance ownership.

The Service Invoices router may expose payment-submission review as part of the service
workflow, but the payment-review business rules continue to be owned and executed by:

```text
finance.services
```

ARCH-5F does not modify `/finance/...` endpoint implementation or Finance business rules.

## Service Order boundary

When an eligible Invoice creates a Service Order, the router delegates to:

```text
domains.service_operations.services.create_order_from_invoice
```

because Service Operations owns creation of Service Orders.

## Shared schemas

`services/api/schema/schemas.py` remains temporarily in place because it still mixes Quote,
Invoice, Service Order, execution-task and deliverable transport schemas. Now that the main
adjacent routers are domain-owned, that file can be split coherently in the next architecture
step.

## Compatibility

ARCH-5F preserves:

- `/invoices` paths and HTTP methods;
- tags, parameters, request bodies, responses and security;
- RBAC and branch scoping;
- email/send/cancel behavior;
- Finance payment-review delegation;
- Invoice-to-ServiceOrder behavior;
- Django model identity and migration state.

Generated OpenAPI operation IDs are not a hard compatibility boundary because no SDK is
generated from Swagger/OpenAPI.
