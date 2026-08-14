# ADR 0020: Service Operations Models Are Grouped by Lifecycle Responsibility

- Status: Accepted
- Date: 2026-08-14

## Context

After consolidating Service Operations ownership, `domains/service_operations/models.py`
became too large. Correct ownership is not enough if a single file becomes difficult to
navigate, review and maintain.

The project therefore treats **file responsibility and growth** as an architecture concern.

## Decision

Service Operations models are organized as a Python package:

```text
domains/service_operations/models/
├── __init__.py
├── catalogue.py
├── requests.py
├── delivery.py
└── feedback.py
```

### `catalogue.py`

Owns service definition/configuration:

- ServiceFieldType
- ServiceCategory
- Service
- ServiceSubService
- ServiceRequestForm
- ServiceRequestField
- ServicePricingConfig
- ServicePricingField
- ServiceWorkflow
- ServiceWorkflowStage
- ServiceBranchActivation

### `requests.py`

Owns intake/case initiation:

- ServiceLead
- ServiceRequest
- ServiceRequestAnswer
- ServiceRequestAttachment
- ServiceRequestActivity

### `delivery.py`

Owns the tightly connected commercial-to-fulfilment lifecycle:

- Quote
- Invoice
- InvoiceItem
- ServiceOrder
- ServiceOrderMilestone
- ServiceOrderActivity
- ServiceExecutionTask
- ServiceDeliverable

These stay together because they have dense model-level dependencies and splitting them
further would create circular imports or artificial indirection.

### `feedback.py`

Owns:

- ClientFeedback

## File-size rule

We do not split files simply because they cross an arbitrary line count.

A file should be split when it contains multiple independently understandable
responsibilities or has become difficult to review safely.

Conversely, we do not create one file per model or one package per architectural noun.

The preferred hierarchy is:

1. one coherent responsibility per file;
2. split when responsibilities diverge or change independently;
3. keep tightly coupled model clusters together;
4. avoid forwarding/re-export layers except where Django migration compatibility requires them.

## Django compatibility

All models retain their existing `services` app label, database tables and migration state.

`services.models.service`, `services.models.feedback` and transitional payment imports continue
to resolve through their compatibility shells.

## Future guidance

The same rule applies beyond models:

- oversized router -> split by endpoint responsibility;
- oversized service module -> split by use-case family;
- oversized selector module -> split by query family;
- oversized schema module -> split by API contract responsibility.

Do not wait for files to become unmanageable before applying this rule.
