# Domain Boundaries and Contracts

## Purpose

This document defines the target business boundaries for the Bomach backend.

It answers four questions for every domain:

1. What does this domain own?
2. What may it depend on?
3. What must it not own or mutate directly?
4. What should other domains use when they need to interact with it?

This is an architectural contract for source organization. It does **not** by itself change
Django app labels, database tables, migrations, API routes, permission keys, or runtime behavior.

---

# Global dependency principles

## 1. Ownership controls writes

The domain that owns a business concept owns the rules that change that concept.

Examples:

- Finance may read an Invoice, but Service Operations should own the commercial rules that
  create or materially alter the Invoice.
- Project Operations may reference a Client, but CRM owns Client business state.
- HR may reference a Branch or Role, but Organization owns those records.

Cross-domain writes should progressively move behind owner-provided services/public interfaces.

## 2. Reads are less strict during transition

Simple direct model reads are temporarily acceptable where they are clear, efficient, and
do not bypass business invariants.

Complex or reusable reads should move to selectors/public query interfaces.

## 3. No domain may import another domain's HTTP layer

Forbidden direction:

```text
finance
  ↓
services.api.v1.invoices
```

Acceptable transition:

```text
finance
  ↓
services.models.payment.Invoice
```

Preferred long-term interaction:

```text
finance
  ↓
service_operations.public.invoice_queries
```

## 4. The composition root is not a business domain

The application composition root may import every domain.

No domain may depend on the application composition root.

Target:

```text
bomach_backend.api
 ├── identity
 ├── organization
 ├── people
 ├── crm
 ├── service_operations
 ├── project_operations
 ├── real_estate
 ├── finance
 ├── legal_compliance
 ├── governance
 └── platform capabilities
```

## 5. Platform is not Shared

`shared` is for domain-neutral technical infrastructure.

`platform` is for reusable business-aware capabilities.

Examples:

```text
shared:
- pagination
- base schemas
- common errors
- request IDs
- logging helpers

platform:
- approvals
- workflow automation
- notifications
- audit trail
```

Do not move domain-specific business logic into `shared`.

---

# Domain: Identity

## Purpose

Identity answers:

> Who can authenticate to Bomach systems, and how is that identity secured?

## Owns

- User
- authentication credentials and login identity
- OTP / verification codes
- token blacklist / token revocation
- account verification
- authentication-related 2FA state
- authentication-side biometric identity hooks

## Does not own

- Employee employment state
- Department
- Branch
- Role definition
- Client commercial relationship
- Estate
- Finance accounts
- business workflows

## Allowed dependencies

- Shared infrastructure
- narrowly defined Organization information where required for access context

## Public interface candidates

```text
identity.public.get_user(...)
identity.public.get_authenticated_identity(...)
identity.public.deactivate_user(...)
identity.public.verify_identity(...)
```

## Likely events

```text
UserCreated
UserActivated
UserDeactivated
UserVerified
AuthenticationFailed
```

---

# Domain: Organization

## Purpose

Organization answers:

> How is Bomach structured and where do people/business activities belong?

## Owns

- Company
- Branch
- Department
- Unit
- Role definitions
- reporting structure
- WorkLocation
- role resource/access definitions where organizational

## Does not own

- employee performance results
- payroll
- customer records
- service fulfilment
- Finance transactions

## Allowed dependencies

- Identity for created-by / ownership references
- Shared infrastructure

## Public interface candidates

```text
organization.public.get_branch(...)
organization.public.list_user_branches(...)
organization.public.get_department(...)
organization.public.get_role(...)
```

## Likely events

```text
BranchCreated
BranchDeactivated
DepartmentCreated
RoleChanged
```

---

# Domain: People / HR

## Purpose

People answers:

> Who works for Bomach, and what is their employment lifecycle?

## Owns

- Employee
- EmployeeDocument
- Attendance
- recruitment
- JobPosting
- Applicant
- Interview
- Offer
- Leave
- Payroll
- Performance Reviews
- Employee KPI records
- Employee targets
- Training
- Awards
- Work Reports
- Disciplinary Cases
- employee evaluations
- employee assets/assignments

## Does not own

- login identity
- Branch or Department definitions
- Client
- Service Orders
- Finance accounts

## Allowed dependencies

- Identity
- Organization
- Platform Approvals
- Platform Notifications
- Shared infrastructure

## Public interface candidates

```text
people.public.get_employee(...)
people.public.get_employee_for_user(...)
people.public.get_manager(...)
people.public.create_employee(...)
```

## Likely events

```text
EmployeeCreated
EmployeeExited
LeaveRequested
LeaveApproved
PayrollPosted
PerformanceReviewCompleted
```

---

# Domain: CRM / Customer & Revenue Relationship

## Purpose

CRM answers:

> Who are Bomach's customers/prospects/partners, and how are commercial relationships developed?

## Owns

- Client
- Lead
- Partner
- PartnerAgreement
- inquiries
- follow-ups
- pipeline opportunities
- sales/revenue relationship activity
- marketing campaign ownership where campaign purpose is customer acquisition/revenue

## Does not own

- Service execution
- Invoice settlement
- Project execution
- authentication identity

## Allowed dependencies

- Identity where a Client maps to a User
- Organization
- Shared infrastructure
- Platform Notifications/Workflow where appropriate

## Public interface candidates

```text
crm.public.get_client(...)
crm.public.get_lead(...)
crm.public.convert_lead(...)
crm.public.get_partner(...)
```

## Likely events

```text
LeadCreated
LeadConverted
ClientCreated
OpportunityWon
PartnerActivated
```

## Open question

The current `user.ClientService` and legacy `user.ServiceRequest` overlap with modern Service
Operations. Their consumers and stored data must be mapped before ownership is finalized.

---

# Domain: Service Operations

## Purpose

Service Operations answers:

> What services does Bomach sell, how are they requested and priced, and how are sold services fulfilled?

## Owns

- ServiceCategory
- Service
- ServiceSubService
- request-form configuration
- pricing configuration
- service-specific workflow configuration
- ServiceBranchActivation
- modern ServiceRequest
- Quote
- commercial Invoice
- ServiceOrder
- ServiceExecutionTask
- ServiceDeliverable
- Feedback
- service-performance reporting/projections

## Why Invoice remains here initially

The current Invoice is tightly coupled to:

- Service
- Quote
- ServiceRequest
- ServiceOrder
- Client

It represents the commercial obligation generated from selling/delivering a service.

Finance may manage receivables and settlement over it, but commercial invoice lifecycle remains
owned by Service Operations unless a later ADR changes that boundary.

## Does not own

- actual cash/bank account
- payment settlement
- organizational Budget
- generic Expense
- Project worksite execution
- Client master relationship
- Employee master record

## Allowed dependencies

- CRM for Client
- Organization for Branch
- Identity/People for staff ownership
- Platform Approval/Workflow/Notification
- Shared infrastructure

## Public interface candidates

```text
service_operations.public.get_service(...)
service_operations.public.get_service_request(...)
service_operations.public.get_invoice(...)
service_operations.public.issue_invoice(...)
service_operations.public.get_order(...)
```

## Likely events

```text
ServiceRequestCreated
QuoteIssued
QuoteAccepted
InvoiceIssued
ServiceOrderCreated
ServiceOrderCompleted
DeliverablePublished
FeedbackReceived
```

---

# Domain: Project Operations

## Purpose

Project Operations answers:

> How are larger projects, milestones, worksites and project tasks executed?

## Owns

- Project
- Milestone
- Task
- Worksite
- SiteEquipment
- Contract
- Timeline

## Does not own

- Client master data
- Employee master data
- Department definition
- Finance accounting
- Service catalogue

## Allowed dependencies

- CRM for Client
- Organization for Department
- People for Employees
- Platform Notifications/Approvals where required
- Shared infrastructure

## Public interface candidates

```text
project_operations.public.get_project(...)
project_operations.public.get_project_progress(...)
project_operations.public.assign_employee(...)
project_operations.public.complete_milestone(...)
```

## Likely events

```text
ProjectCreated
ProjectStarted
MilestoneCompleted
ProjectCompleted
ProjectDelayed
```

---

# Domain: Real Estate

## Purpose

Real Estate answers:

> What real-estate inventory and brokerage assets does Bomach manage or transact?

## Owns

- Estate
- EstateDocument
- Property
- PropertyImage
- BrokerageListing
- BrokerageListingImage
- estate-specific transaction records initially

## Boundary items requiring further review

- EstatePropertyInvoice
- EstatePropertyInvoiceItem
- InvoiceApproval
- Cart / CartItem

These should remain behaviorally unchanged until their consumers are fully mapped.

## Does not own

- generic Client identity
- FinanceAccount
- generic accounting/payment settlement
- Organization structure

## Allowed dependencies

- CRM for Client
- Organization for Branch where applicable
- Identity for created-by ownership
- Finance for settlement/read projections where appropriate
- Platform Approvals/Notifications
- Shared infrastructure

## Public interface candidates

```text
real_estate.public.get_estate(...)
real_estate.public.get_property(...)
real_estate.public.reserve_property(...)
real_estate.public.get_brokerage_listing(...)
```

## Likely events

```text
EstateCreated
PropertyCreated
PropertyReserved
PropertySold
BrokerageListingCreated
```

---

# Domain: Finance & Accounting

## Purpose

Finance answers:

> What money has moved, what money is owed, what is budgeted/spent, and what is the financial state of Bomach?

## Owns now / target owns

- FinanceAccount
- Payment
- PaymentSubmission
- Budget
- Expense
- receivable management/projections

## Future likely ownership

- Payables
- Cashbook / cash movement ledger
- Budget controls
- Project finance projections
- Cash-flow forecasting
- Reconciliation
- Journals
- General Ledger
- Chart of Accounts
- tax/accounting reporting

## Does not own

- Service definition
- ServiceRequest
- ServiceOrder
- Project execution
- Client master record
- Branch definition

## Allowed dependencies

- Service Operations for Invoice/commercial obligations
- CRM for Client
- Organization for Branch/Department
- Project Operations for project-finance projections
- Platform Approvals/Notifications/Audit
- Shared infrastructure

## Public interface candidates

```text
finance.public.confirm_payment(...)
finance.public.get_account(...)
finance.public.get_receivable(...)
finance.public.get_budget(...)
finance.public.record_expense(...)
```

## Likely events

```text
PaymentSubmitted
PaymentConfirmed
PaymentRejected
BudgetApproved
ExpenseApproved
ExpensePaid
ReceivableOverdue
```

## Important boundary

```text
Invoice
→ Service Operations

Payment
→ Finance
```

This separates the commercial obligation from actual financial settlement.

---

# Domain: Legal & Compliance

## Purpose

Legal & Compliance answers:

> What legal obligations, cases and compliance processes must Bomach manage?

## Owns

- LegalCase
- Compliance records
- compliance-oriented audits
- regulatory/legal tracking

## Does not own

- technical activity AuditLog
- generic workflow engine
- User authentication

## Allowed dependencies

- Identity
- Organization
- Platform Approvals/Notifications
- Shared infrastructure

## Public interface candidates

```text
legal_compliance.public.get_case(...)
legal_compliance.public.record_compliance_result(...)
```

## Likely events

```text
LegalCaseOpened
ComplianceFindingRaised
ComplianceAuditCompleted
```

---

# Domain: Governance / Corporate

## Purpose

Governance answers:

> How are Bomach's corporate decisions, policies and ownership/governance activities recorded?

## Owns

- Shareholder
- Meeting
- BoardResolution
- Policy
- Announcement
- corporate governance records

## Does not own

- employee HR policy execution
- generic workflow engine
- legal case management

## Allowed dependencies

- Identity
- Organization
- Platform Approvals/Notifications
- Shared infrastructure

## Public interface candidates

```text
governance.public.get_policy(...)
governance.public.record_board_resolution(...)
governance.public.get_meeting(...)
```

## Likely events

```text
PolicyPublished
BoardResolutionApproved
MeetingScheduled
AnnouncementPublished
```

---

# Platform: Approvals

## Purpose

Provide reusable approval sequencing for multiple business domains.

## Owns

- ApprovalFlow
- ApprovalFlowStep
- ApprovalRequest
- ApprovalDecision

## Why it is platform

Current approval action types already span:

- leave
- expenses
- salary adjustment
- new hire
- contracts
- asset purchase
- policy change
- promotion
- general approval

No single business domain should own this engine.

## Allowed dependencies

- Identity / People for approvers
- narrow domain references through metadata/public contracts

## Public interface candidates

```text
approvals.public.request_approval(...)
approvals.public.approve(...)
approvals.public.reject(...)
approvals.public.get_status(...)
```

## Likely events

```text
ApprovalRequested
ApprovalApproved
ApprovalRejected
ApprovalCompleted
```

---

# Platform: Workflow / Automation

## Purpose

Provide generic trigger → conditions → action automation.

## Owns

- WorkflowRule
- WorkflowRuleLog
- generic workflow execution engine

## Does not own

- ServiceWorkflow / ServiceWorkflowStage

Those remain Service Operations concepts because they define service fulfilment.

## Public interface candidates

```text
workflow.public.emit_trigger(...)
workflow.public.evaluate_rules(...)
```

---

# Platform: Notifications

## Purpose

Provide reusable user-facing notification creation and later channel delivery.

## Owns

- Notification
- notification preferences/templates/channels when introduced

## Does not own

The business decision that an event should occur.

A business domain emits/requests the notification; the notification platform delivers it.

## Public interface candidates

```text
notifications.public.notify_user(...)
notifications.public.notify_users(...)
```

---

# Platform: Audit

## Purpose

Record technical/security/activity audit information across domains.

## Owns

- AuditLog
- generic technical activity/event audit trail

## Does not own

- compliance audit
- financial journal
- workflow execution logs

These may reference the technical audit platform but remain separate domain records.

## Public interface candidates

```text
audit.public.record(...)
```

---

# Open architecture decisions

The following require further evidence before final source movement:

1. `user.ClientService`
2. legacy `user.ServiceRequest`
3. CRM model overlap between `user` and `services`
4. EstatePropertyInvoice ownership
5. Cart / CartItem ownership
6. wallet model ownership
7. client inventory ownership
8. generic document/content/event models under `services`
9. property models under `services`
10. role-career/SOP/playbook records split between Organization and People

These are explicitly **not blockers** for starting low-risk structural work.

---

# First migration candidates

## Very safe structural change

Move global API composition from:

```text
user/api/__init__.py
```

to:

```text
bomach_backend/api.py
```

while preserving every existing router and path.

This removes application-composition responsibility from the User domain.

## Best pilot business domain

Project Operations / `operations`.

Reasons:

- internally coherent model graph;
- small and understandable external dependency set;
- already correctly named as a domain;
- low ambiguity around model ownership;
- not currently the active Finance feature-development area.

The pilot should establish the internal standard for:

```text
models/
api/
services/
selectors/
public/
tests/
```

without changing Django app identity, database tables or public API behavior.
