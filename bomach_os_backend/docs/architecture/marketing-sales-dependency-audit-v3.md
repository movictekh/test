# Marketing Sales Dependency Audit v3

## Rules

- marketing_sales must not depend on legacy services ownership
- shared primitives belong in shared modules
- compatibility exports remain until migration completes

## Review Required

- domains/marketing_sales/api/v1/routers/campaigns.py
- domains/marketing_sales/api/v1/routers/content.py
- domains/marketing_sales/api/v1/routers/marketing.py
- domains/marketing_sales/api/v1/routers/revenue_execution.py
- domains/marketing_sales/api/v1/routers/sales.py
- domains/marketing_sales/models/content.py
- domains/marketing_sales/models/marketing.py
- domains/marketing_sales/services/marketing.py
- domains/marketing_sales/services/sales.py