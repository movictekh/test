# ADR 0026: Service Operations Hygiene and Private Router Support

- Status: Accepted
- Date: 2026-08-15

## Decision

Do not introduce new architectural layers merely to relocate helper code.

The two private support modules under `api/v1/routers/` remain shared implementation modules.
Their leading underscore marks them private; they expose no HTTP routes.

They may contain response serialization, formatting, reusable API-oriented reads, and small
request/access helpers. They must not contain transactions, state transitions, mutation
workflows, or business orchestration.

The misplaced workflow creation transaction was moved into the existing catalogue application
service.

Unused imports are removed across non-`__init__.py` Service Operations modules without adding
new folders or abstractions.

Remaining meaningful workflow extraction is concentrated in `service_configuration.py` and
`orders.py`.
