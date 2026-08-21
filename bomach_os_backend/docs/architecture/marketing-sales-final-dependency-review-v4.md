# Marketing Sales Final Dependency Review

Generated review list.

## Remaining imports from legacy services

### domains/marketing_sales/api/v1/routers/campaigns.py
- `from domains.marketing_sales.services.marketing import (`

### domains/marketing_sales/api/v1/routers/content.py
- `from domains.marketing_sales.services.marketing import (`
- `from domains.marketing_sales.services.marketing import (`

### domains/marketing_sales/api/v1/routers/marketing.py
- `from domains.marketing_sales.services.marketing import (`

### domains/marketing_sales/api/v1/routers/revenue_execution.py
- `from domains.marketing_sales.services.sales import (`
- `from domains.marketing_sales.services.sales import (`
- `from domains.marketing_sales.services.sales import (`
- `from domains.marketing_sales.services.sales import (`
- `from domains.marketing_sales.services.sales import (`
- `from domains.marketing_sales.services.sales import (`
- `from domains.marketing_sales.services.sales import (`
- `from domains.marketing_sales.services.sales import _revenue_open_day as _open_day`
- `from domains.marketing_sales.services.sales import (`

### domains/marketing_sales/api/v1/routers/sales.py
- `from domains.marketing_sales.services.funnel import (`
- `from domains.marketing_sales.services.sales import (`

### domains/marketing_sales/models/content.py
- `"services.MarketingCampaign",`
- `"services.CampaignAsset",`
- `"services.MarketingCampaign",`
- `"services.CampaignAsset",`

### domains/marketing_sales/models/marketing.py
- `"services.Content",`
- `"services.MarketingMeetingContext",`
- `"services.Lead",`

### domains/marketing_sales/services/marketing.py
- `from domains.marketing_sales.services.funnel import record_initial_funnel_event`
- `"services.Lead",`

### domains/marketing_sales/services/sales.py
- `from domains.marketing_sales.services.funnel import record_status_funnel_event`
