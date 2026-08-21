# Marketing & Sales Modularization Status

## Ownership

Marketing and Sales capability code belongs in:

- domains/marketing_sales

The services package may contain compatibility exports during migration.

## Compatibility Bridges

Compatibility files are intentionally retained until imports are migrated.

Examples:

- services/models/marketing_campaign.py
- services/funnel_events.py

## Rules

New Marketing/Sales business logic must not be added to:

- services/models
- services/service
- generic services modules

New work belongs under:

- domains/marketing_sales/models
- domains/marketing_sales/services
- domains/marketing_sales/api

## Cleanup Process

1. migrate imports
2. remove compatibility usage
3. delete bridges after verification
