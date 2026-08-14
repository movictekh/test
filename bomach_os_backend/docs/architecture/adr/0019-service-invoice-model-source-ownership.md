# ADR 0019: Service Operations Owns Invoice and InvoiceItem Model Source

- Status: Accepted
- Date: 2026-08-14

## Decision

The mixed legacy `services/models/payment.py` contains two ownership concerns:

- `Invoice` / `InvoiceItem` -> Service Operations
- `Payment` -> Finance

`Invoice` and `InvoiceItem` move to `domains/service_operations/models.py` and retain `app_label = "services"` so Django labels, tables and migrations remain unchanged.

`Payment` remains physically in `services/models/payment.py` for now. That file imports and re-exports the domain-owned invoice classes so legacy imports continue to work.

## Finance boundary

This step does not move or rewrite `Payment`, Finance endpoints, Finance services, or payment confirmation rules. `Payment.save()` continues to update the linked Invoice exactly as before.

## Canonical Service Operations imports

Service Operations code imports `Invoice` and `InvoiceItem` directly from `domains.service_operations.models`.

## Compatibility

ARCH-5M preserves `services.Invoice`, `services.InvoiceItem`, `services.Payment`, database tables, fields, relationships, indexes, ordering, migrations and the HTTP/OpenAPI contract.
