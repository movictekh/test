# ADR 0023: Service Operations Sprint Sign-Off

- Status: Accepted
- Date: 2026-08-14

## Decision

ARCH-5 Service Operations is considered structurally complete for the current modular-monolith
architecture.

The domain now owns its HTTP source, transport schemas, application services, selectors and
business model source.

Internal large files have been split by coherent responsibility rather than by architectural
noun or arbitrary file count.

## Boundaries retained

- Payment remains Finance-owned.
- Generic CRM Lead remains CRM-owned.
- ServiceLead remains Service Operations-owned.
- ServiceOrder remains distinct from Project.
- Project Operations remains a separate bounded context.
- Django `services` app labels remain for migration compatibility.
- Legacy model modules that remain are compatibility/transitional shells, not business owners.

## Re-entry rule

Further changes to Service Operations architecture require one of:

1. a functional defect;
2. a new feature creating a real responsibility boundary;
3. a demonstrated dependency violation;
4. a planned migration of Django app identity.

No additional polishing is required merely to make the folder tree more symmetrical.
