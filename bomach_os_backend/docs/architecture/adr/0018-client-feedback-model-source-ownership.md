# ADR 0018: Service Operations Owns ClientFeedback Model Source

- Status: Accepted
- Date: 2026-08-14

## Decision

`ClientFeedback` is a Service Operations model because it is directly attached to
`ServiceOrder` and represents post-/in-delivery service quality, complaints, rework,
testimonials, referrals, ratings and satisfaction.

Its real model source moves from:

```text
services/models/feedback.py
```

into the existing coherent Service Operations model module:

```text
domains/service_operations/models.py
```

The model explicitly retains:

```python
class Meta:
    app_label = "services"
```

so its Django identity and migration ownership stay unchanged.

## Compatibility shell

`services/models/feedback.py` remains as a thin compatibility shell importing
`ClientFeedback` from the domain. This allows `services.models.__init__`, migrations and
transitional imports to continue working without duplicating model definitions.

## Canonical imports

Code inside Service Operations imports `ClientFeedback` from:

```text
domains.service_operations.models
```

rather than through the compatibility shell.

## Scope

This ADR moves only `ClientFeedback`.

It does not move:

- Invoice / InvoiceItem;
- Payment;
- generic CRM models;
- Budget / Expense;
- Real Estate models;
- other legacy `services` models.

The mixed `services/models/payment.py` requires a separate ownership split because it contains
both Service Operations invoice models and Finance-owned Payment.
