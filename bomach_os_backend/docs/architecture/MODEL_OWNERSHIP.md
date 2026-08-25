# Model and Domain Ownership Matrix

## Purpose

This document records **business/source ownership** separately from current Django app
identity.

`Target domain` answers: **Which business/domain package should own the implementation?**

`Transition identity` answers: **Which Django label should remain during the first source
move so migrations/tables/permissions are not accidentally changed?**

This is an architecture inventory, not permission to delete or merge legacy models.

## Decision states

- **KEEP** — current conceptual owner is already appropriate.
- **MOVE SOURCE** — implementation should move to another domain package while preserving current Django identity initially.
- **PLATFORM** — cross-domain platform capability.
- **INVESTIGATE** — overlapping/ambiguous concept; map consumers before deciding.

## Core / user-app models

| Model / group | Current Django app | Target domain | Decision | Transition identity | Notes |
|---|---|---|---|---|---|
| User | user | Identity | KEEP / reorganize source | `user.User` | Authentication identity. |
| OTPCode | user | Identity | KEEP / reorganize source | `user.OTPCode` | Verification/auth concern. |
| TokenBlacklist | user | Identity | KEEP / reorganize source | `user.TokenBlacklist` | JWT/session security. |
| Company | user | Organization | MOVE SOURCE | preserve `user.*` | Organizational structure. |
| Branch | user | Organization | MOVE SOURCE | `user.Branch` | Referenced broadly by Finance, Services, etc. |
| Department | user | Organization | MOVE SOURCE | `user.Department` | Core organizational dimension. |
| Unit | user | Organization | MOVE SOURCE | `user.Unit` | Core organizational dimension. |
| Role | user | Organization / Authorization | MOVE SOURCE | `user.Role` | Role definition and permission assignment. |
| WorkLocation | user | People / Attendance | MOVE SOURCE | `user.WorkLocation` | Employee-owned attendance whitelist; Branch remains the Organization reference. |
| RoleReportingLine | user | Organization | MOVE SOURCE | preserve `user.*` | Role structure. |
| RoleResource | user | Organization / Authorization | MOVE SOURCE | preserve `user.*` | Role resource configuration. |
| RoleDescription | user | Organization | MOVE SOURCE | preserve `user.*` | Role definition. |
| RoleCareerPath | user | People / Organization boundary | INVESTIGATE | preserve `user.*` | Role design vs employee development. |
| RoleKPIMetric | user | People | MOVE SOURCE | preserve `user.*` | Performance framework. |
| EmployeeKPIRecord | user | People | MOVE SOURCE | preserve `user.*` | Employee performance result. |
| RoleTrainingRequirement | user | People | MOVE SOURCE | preserve `user.*` | HR development concern. |
| RoleTargetTemplate | user | People | MOVE SOURCE | preserve `user.*` | Performance target definition. |
| EmployeeTarget | user | People | MOVE SOURCE | preserve `user.*` | Employee performance target. |
| EmployeeTargetReport | user | People | MOVE SOURCE | preserve `user.*` | Employee performance reporting. |
| RoleTaskTemplate / RoleDailyRoutineItem | user | People / Organization boundary | INVESTIGATE | preserve `user.*` | Inspect consumers. |
| RoleSOP | user | Organization / Platform knowledge | INVESTIGATE | preserve `user.*` | Depends on SOP ownership decision. |
| RoleSuccessPlaybookItem | user | People / Organization boundary | INVESTIGATE | preserve `user.*` | Role development/operating guidance. |
| Employee | user | People | MOVE SOURCE | `user.Employee` | Employment record is distinct from login identity. |
| EmployeeDocument | user | People | MOVE SOURCE | preserve `user.*` | HR record. |
| Review | user | People | MOVE SOURCE | preserve `user.*` | Employee review. |
| Attendance | user | People | MOVE SOURCE | `user.Attendance` | HR attendance. |
| Lead | user | CRM | MOVE SOURCE | `user.Lead` | Customer/revenue pipeline concern. |
| Client | user | CRM | MOVE SOURCE | `user.Client` | Customer relationship. |
| Partner / PartnerAgreement | user | CRM / Partnerships | MOVE SOURCE | preserve `user.*` | Commercial relationship. |
| Estate | user | Real Estate | MOVE SOURCE | `user.Estate` | Clear real-estate ownership. |
| EstateDocument | user | Real Estate | MOVE SOURCE | preserve `user.*` | Estate-specific document. |
| Property / PropertyImage | user | Real Estate | MOVE SOURCE | preserve `user.*` | Real-estate inventory/media. |
| BrokerageListing / Image | user | Real Estate | MOVE SOURCE | preserve `user.*` | Brokerage domain. |
| EstatePropertyInvoice / Item | user | Real Estate / Finance boundary | INVESTIGATE | preserve `user.*` | Keep with estate transaction initially; Finance may project over it. |
| InvoiceApproval | user | Real Estate / Platform Approvals boundary | INVESTIGATE | preserve `user.*` | Determine generic approval integration. |
| Cart / CartItem | user | Real Estate / Commerce boundary | INVESTIGATE | preserve `user.*` | Determine whether cart is estate-specific. |
| LegalCase | user | Legal & Compliance | MOVE SOURCE | `user.LegalCase` | Legal domain. |
| Compliance models | user | Legal & Compliance | MOVE SOURCE | preserve `user.*` | Expand model-by-model later. |
| Audit (compliance audit) | user | Legal & Compliance | MOVE SOURCE | `user.Audit` | Distinct from technical `AuditLog`. |
| Shareholder | user | Governance | MOVE SOURCE | `user.Shareholder` | Corporate governance. |
| Announcement | user | Governance | MOVE SOURCE | `user.Announcement` | Corporate communication/governance. |
| Policy | user | Governance | MOVE SOURCE | `user.Policy` | Corporate policy. |
| Meeting | user | Governance | MOVE SOURCE | `user.Meeting` | Governance/corporate meeting. |
| BoardResolution | user | Governance | MOVE SOURCE | `user.BoardResolution` | Board governance. |
| ApprovalFlow / ApprovalFlowStep | user | Platform / Approvals | PLATFORM | preserve `user.*` | Generic reusable approval workflow. |
| ApprovalRequest / ApprovalDecision | user | Platform / Approvals | PLATFORM | preserve `user.*` | Generic live approval process. |
| Notification | user | Platform / Notifications | PLATFORM | `user.Notification` | Generic per-user notification. |
| WorkflowRule / WorkflowRuleLog | user | Platform / Workflow | PLATFORM | preserve `user.*` | Generic trigger/condition/action automation. |
| AuditLog | user | Platform / Audit | PLATFORM | `user.AuditLog` | Technical/security/activity audit trail. |
| SOP / Responsibility | user | Organization / Platform knowledge | INVESTIGATE | preserve `user.*` | Inspect operating-knowledge semantics. |
| ClientService | user | Legacy customer/service domain | INVESTIGATE | `user.ClientService` | Older service catalogue concept overlaps modern Services domain. |
| legacy ServiceRequest | user | Legacy customer/service domain | INVESTIGATE | `user.ServiceRequest` | Do not merge/delete until consumers and data are mapped. |
| PaymentSubmission | user | Finance | MOVE SOURCE | `user.PaymentSubmission` | Finance already owns review/confirmation workflow. |
| Client inventory models | user | CRM / Commerce boundary | INVESTIGATE | preserve `user.*` | Expand after caller inventory. |
| Wallet models | user | Finance / Customer wallet boundary | INVESTIGATE | preserve `user.*` | Inspect wallet semantics first. |

## Service-app models

| Model / group | Current Django app | Target domain | Decision | Transition identity | Notes |
|---|---|---|---|---|---|
| ServiceCategory | services | Service Operations | KEEP | `services.ServiceCategory` | Core catalogue. |
| Service | services | Service Operations | KEEP | `services.Service` | Operational service template. |
| ServiceSubService | services | Service Operations | KEEP | preserve `services.*` | Catalogue. |
| ServiceRequestForm / Field | services | Service Operations | KEEP | preserve `services.*` | Versioned dynamic request configuration. |
| ServicePricingConfig | services | Service Operations | KEEP | preserve `services.*` | Pricing configuration. |
| ServiceWorkflow / Stage | services | Service Operations | KEEP | preserve `services.*` | Service-specific fulfilment workflow. |
| ServiceBranchActivation | services | Service Operations | KEEP | preserve `services.*` | Service availability per branch. |
| modern ServiceRequest | services | Service Operations | KEEP | `services.ServiceRequest` | Modern Service Operations request. |
| Quote | services | Service Operations | KEEP | `services.Quote` | Commercial quote. |
| ServiceOrder | services | Service Operations | KEEP | `services.ServiceOrder` | Fulfilment order. |
| ServiceExecutionTask | services | Service Operations | KEEP | preserve `services.*` | Fulfilment execution. |
| ServiceDeliverable | services | Service Operations | KEEP | preserve `services.*` | Fulfilment output. |
| Invoice | services | Service Operations | KEEP | `services.Invoice` | Commercial obligation; Finance handles collection/projection. |
| Payment | services | Finance | MOVE SOURCE | `services.Payment` | Actual monetary settlement is a Finance concern. |
| Feedback models | services | Service Operations | KEEP | preserve `services.*` | Client feedback on delivery. |
| Budget | services | Finance / Planning & Control | MOVE SOURCE | `services.Budget` | Branch + Department + fiscal-period allocation. |
| Expense | services | Finance | MOVE SOURCE | `services.Expense` | Spending/expense concern. |
| CRM models | services | CRM | MOVE SOURCE / INVESTIGATE | preserve `services.*` | Map overlap with `user.Lead` first. |
| MarketingCampaign models | services | CRM / Marketing | MOVE SOURCE | preserve `services.*` | Commercial growth concern. |
| Document models | services | Platform Files or Service Operations | INVESTIGATE | preserve `services.*` | Generic vs service-specific ownership. |
| Content models | services | Governance/Content or Service Operations | INVESTIGATE | preserve `services.*` | Inspect semantics. |
| Event models | services | Governance/Events or Service Operations | INVESTIGATE | preserve `services.*` | Inspect semantics. |
| Property models in services | services | Real Estate / Service boundary | INVESTIGATE | preserve `services.*` | Determine whether duplicate or service-specific. |

## Operations-app models

| Model | Current Django app | Target domain | Decision | Transition identity | Notes |
|---|---|---|---|---|---|
| Project | operations | Project Operations | KEEP | `operations.Project` | Already correctly bounded. |
| Milestone | operations | Project Operations | KEEP | `operations.Milestone` | Project aggregate. |
| Task | operations | Project Operations | KEEP | `operations.Task` | Project execution. |
| Worksite | operations | Project Operations | KEEP | `operations.Worksite` | Project execution. |
| SiteEquipment | operations | Project Operations | KEEP | `operations.SiteEquipment` | Worksite equipment. |
| Contract | operations | Project Operations | KEEP | `operations.Contract` | Project contract. |
| Timeline | operations | Project Operations | KEEP | `operations.Timeline` | Project schedule. |

## Finance-app models

| Model | Current Django app | Target domain | Decision | Transition identity | Notes |
|---|---|---|---|---|---|
| FinanceAccount | finance | Finance | KEEP | `finance.FinanceAccount` | Already correctly owned. |

## Important ownership boundaries

### Invoice vs Payment

Current recommendation:

```text
Invoice
→ Service Operations
  commercial obligation generated from a service/quote/order

Payment
→ Finance
  actual monetary settlement
```

### Legacy vs modern Service Request

There are currently two distinct concepts:

```text
user.ClientService + user.ServiceRequest
services.Service + services.ServiceRequest
```

No model should be deleted, merged, or renamed until endpoint consumers, frontend consumers,
database usage and migration history are mapped.

### Technical audit vs compliance audit

```text
AuditLog
→ Platform / Audit

Compliance-oriented Audit
→ Legal & Compliance
```

They should not be merged merely because both contain the word "audit".

## Source-move acceptance checklist

For every moved model implementation:

- record current `_meta.label`;
- record current `_meta.db_table`;
- record constraints and indexes;
- record relationships;
- scan migrations for direct imports of the old Python path;
- move implementation to target domain package;
- keep compatibility import when needed;
- preserve existing Django app label;
- preserve existing database table;
- verify old imports still work during transition;
- run `python manage.py check`;
- run `python manage.py makemigrations --check --dry-run`;
- run existing tests;
- compare API schema/contracts for affected endpoints.

A pure source move must not accidentally produce table-create/table-delete migrations.
