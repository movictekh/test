# Bomach Service Operations Module

## Functional Overview, Business Flow, Expected Features, and Implementation Notes

## 1. Introduction

This document explains what the Bomach Service Operations Module is, how it is expected to work, the main business flow, the major sections in the module, and what each section brings into the system.

The current HTML file is a working prototype and design guide. It shows the screens, sample data, roles, actions, workflows, and general user experience I want the final application to have.

The final production application will not remain as one large HTML file. It will be rebuilt in a structured React and TypeScript codebase using tools such as:

- React
- TypeScript
- Vite
- Tailwind CSS
- TanStack Router
- TanStack Query
- TanStack Form
- TanStack Table
- TanStack Virtual where needed
- TanStack Pacer where needed
- ESLint
- Proper testing tools
- A backend API and database

The main purpose of the prototype is to help me understand the business process and define the expected behaviour before I start writing production code.

---

## 2. What the Service Operations Module Is

The Bomach Service Operations Module is a system for managing the full life cycle of every service Bomach offers.

It starts from the point where a service is created and configured. It then follows the client request through pricing, approval, payment, execution, delivery, client acceptance, feedback, reporting, and audit.

The simplest way to explain it is:

> The Service Operations Module converts a client need into a controlled, paid, traceable, and measurable service delivery process.

It brings together four main parts of the business:

### Commercial operations

This covers how the client requests a service, how the request is reviewed, how the quotation is prepared, how approval is obtained, and how payment is collected.

### Operational delivery

This covers how the service is turned into actual work, who is responsible, what tasks must be completed, what milestones must be reached, and what deliverables must be produced.

### Client experience

This covers what the client can see, what the client needs to approve, how the client follows progress, and how feedback is collected.

### Governance and management

This covers approvals, reports, audit history, accountability, branch performance, service performance, and management visibility.

---

## 3. Why the Module Is Needed

Without a central system, different divisions may manage their work in different ways.

For example:

- some requests may remain in WhatsApp chats;
- some quotations may be prepared manually;
- some approvals may happen through phone calls;
- some teams may use spreadsheets;
- some work may begin without proper payment confirmation;
- some deliverables may not have version history;
- management may not have one reliable view of ongoing work;
- it may be difficult to know who made an important decision.

The Service Operations Module is expected to solve these problems by creating one standard process that every division can follow.

The actual workflow can still be different for each service, but the main business records remain consistent.

These records include:

- Service
- Request
- Assessment
- Quotation
- Approval
- Invoice
- Payment
- Service Order
- Milestone
- Task
- Deliverable
- Client Approval
- Feedback
- Audit Event

---

## 4. The Main Business Flow

The complete service journey is expected to follow this pattern:

```text
Service Configuration
        ↓
Service Request
        ↓
Review or Assessment
        ↓
Quotation
        ↓
Internal Approval
        ↓
Client Acceptance
        ↓
Invoice
        ↓
Payment Confirmation
        ↓
Service Order
        ↓
Tasks and Milestones
        ↓
Deliverables
        ↓
Quality Review
        ↓
Client Acceptance
        ↓
Completion
        ↓
Feedback and Audit
```

This flow connects the commercial side of the business to the operational side.

It also ensures that important actions are recorded and can be reviewed later.

---

## 5. The Five Main Layers of the Module

## 5.1 Service Definition

This is where the business defines what a service is and how it should work.

A service should contain information such as:

- service name;
- service code;
- division;
- description;
- service owner;
- status;
- service-level target;
- fulfilment mode;
- sub-services;
- pricing method;
- request form;
- workflow stages;
- active branches.

Examples of services in the prototype include:

- Estate Plot Sales
- Property Brokerage
- Cadastral Land Survey
- Building Construction
- Structural Inspection
- Express Delivery
- Business Software Development
- Farm Produce Supply

The service definition is the foundation of everything else.

It tells the system:

- what information to collect from the client;
- how to calculate an estimate;
- which team should handle the request;
- what stages must be followed;
- which approvals are required;
- where the service is available.

---

## 5.2 Commercial Processing

This is the part that handles the client journey before the work begins.

The main commercial flow is:

```text
Request → Assessment → Quotation → Approval → Invoice → Payment
```

This layer answers questions such as:

- Who is the client?
- What service does the client need?
- What is the scope?
- Is more information required?
- Is a professional assessment required?
- What is the estimated price?
- Has the quotation been approved?
- Has the client accepted it?
- Has an invoice been issued?
- Has the required payment been received?

---

## 5.3 Operational Fulfilment

This starts after the service has been approved and the required payment condition has been met.

The main operational flow is:

```text
Service Order → Milestones → Tasks → Deliverables → Review → Completion
```

This layer answers questions such as:

- Who owns the work?
- What stage is active?
- What task should happen next?
- Is the work delayed?
- What evidence is required?
- What deliverable should be uploaded?
- Does a supervisor need to approve it?
- Does the client need to sign off?
- Is the order ready to close?

---

## 5.4 Client Experience

This layer gives the client a clear view of what is happening.

The client should be able to see:

- open requests;
- accepted quotations;
- invoices and payments;
- active service orders;
- current progress;
- documents;
- approvals;
- actions required;
- feedback forms.

The client portal should reduce the need for repeated calls asking for updates.

It should also make the service process more transparent.

---

## 5.5 Governance and Intelligence

This layer gives management visibility and control.

It includes:

- approval queues;
- audit logs;
- dashboards;
- branch reports;
- service reports;
- revenue reports;
- service-level reports;
- overdue alerts;
- client satisfaction reports;
- operational performance reports.

This layer helps management answer questions such as:

- Which requests are being delayed?
- Which quotations are waiting for approval?
- How much money has been confirmed?
- Which branch is performing best?
- Which service has the highest conversion rate?
- Which team is missing deadlines?
- Who made a particular change?

---

# 6. Important Business Records

## 6.1 Service

A service is the reusable definition of what Bomach offers.

It is not tied to one client.

For example:

```text
Building Construction
```

The service definition may include:

- required request fields;
- pricing calculator;
- approval rules;
- workflow stages;
- responsible role;
- active branches.

---

## 6.2 Service Request

A service request is one client asking for one service.

For example:

```text
Chief Okafor requests the construction of a six-bedroom duplex.
```

The request should record:

- client details;
- customer type;
- service;
- division;
- branch;
- request source;
- budget;
- estimated value;
- scope;
- priority;
- owner;
- status;
- next action;
- due date;
- communication history.

A request is not yet confirmed work.

---

## 6.3 Assessment

Some services cannot be priced correctly without a professional review.

Examples include:

- construction site assessment;
- structural inspection;
- land survey review;
- software discovery;
- property verification.

An assessment may involve:

- assigning a professional;
- scheduling a date;
- visiting a location;
- collecting documents;
- uploading evidence;
- recording findings;
- making recommendations.

---

## 6.4 Quotation

A quotation is Bomach's formal offer to the client.

It should explain:

- what Bomach will deliver;
- how much it will cost;
- what taxes or charges apply;
- what deposit is required;
- how long the offer is valid;
- what terms apply;
- who approved it.

The quotation may go through statuses such as:

```text
Draft
Awaiting Approval
Sent
Accepted
Rejected
Expired
```

A quotation should support versions because the scope and price may change during negotiation.

---

## 6.5 Approval

An approval is a formal decision that must be made before an action can continue.

Examples include:

- high-value quotation approval;
- discount approval;
- milestone approval;
- deliverable approval;
- client approval;
- closure approval.

An approval should record:

- approval type;
- related record;
- requester;
- approver;
- amount where applicable;
- due date;
- decision;
- comment;
- date;
- history.

---

## 6.6 Invoice

An invoice is the formal request for payment.

It should include:

- linked quotation;
- client;
- service;
- total amount;
- amount paid;
- balance;
- due date;
- payment schedule;
- status.

Possible invoice statuses include:

```text
Unpaid
Part Paid
Paid
Overdue
Cancelled
```

---

## 6.7 Payment

A payment is the confirmed money received from the client.

A proper payment record should include:

- invoice;
- amount;
- payment reference;
- payment method;
- transaction ID;
- payment date;
- confirming officer;
- receipt;
- reconciliation status.

Payment confirmation is important because some services should not move into execution until the required payment threshold has been reached.

---

## 6.8 Service Order

A service order is the operational record used to execute the work.

It should only exist when the request has moved beyond the enquiry stage and the business is ready to deliver.

The service order should contain:

- linked request;
- client;
- service;
- division;
- fulfilment mode;
- owner;
- start date;
- due date;
- order value;
- current stage;
- progress;
- milestones;
- tasks;
- deliverables;
- activity history;
- approvals;
- feedback.

Possible order statuses include:

```text
Pending Mobilisation
Active
Quality Review
Awaiting Client
Completed
On Hold
Cancelled
```

---

## 6.9 Milestone

A milestone is a major stage in the service.

Examples for construction include:

- Mobilisation
- Site Setup
- Foundation
- Substructure
- Superstructure
- Roofing
- Handover

Examples for surveying include:

- Document Review
- Field Survey
- Processing
- Professional Review
- Delivery

Examples for software include:

- Discovery
- Requirements
- Design
- Development
- Quality Assurance
- Deployment

Milestones may have statuses such as:

```text
Pending
Active
Done
Blocked
```

---

## 6.10 Task

A task is a specific activity that someone must complete.

Examples include:

- schedule a site assessment;
- verify plot availability;
- inspect reinforcement;
- review a survey plan;
- upload proof of delivery;
- prepare a product specification.

A task should record:

- title;
- linked request or order;
- owner;
- due date;
- priority;
- status;
- instructions;
- acceptance criteria;
- evidence requirement.

Task statuses may include:

```text
To Do
In Progress
Review
Done
Blocked
```

---

## 6.11 Deliverable

A deliverable is a formal output produced during the service.

Examples include:

- survey plan;
- engineering report;
- drawing;
- certificate;
- legal document;
- progress report;
- product requirements document;
- proof of delivery;
- handover file.

A deliverable should record:

- linked order;
- title;
- type;
- version;
- owner;
- client visibility;
- status;
- reviewer;
- comments;
- approval history;
- upload date;
- download history.

---

## 6.12 Client Approval

Client approval is required when the client must review or accept something.

Examples include:

- quotation acceptance;
- document approval;
- milestone approval;
- revised scope approval;
- handover acceptance.

This should be separate from internal approval because the client is not part of the internal approval chain.

---

## 6.13 Feedback

Feedback is used to measure the client's experience.

It may include:

- completion feedback;
- milestone feedback;
- complaint;
- defect report;
- rework request;
- testimonial;
- referral.

A feedback record should include:

- client;
- service;
- order;
- rating;
- type;
- comment;
- status;
- corrective action;
- date.

---

## 6.14 Audit Event

An audit event is a permanent record of an important action.

It should answer:

- Who performed the action?
- What did the person do?
- When did it happen?
- Which record was affected?
- What changed?
- Where did the action come from?

Examples include:

- request status changed;
- quotation approved;
- payment confirmed;
- plot reserved;
- deliverable uploaded;
- milestone completed;
- order closed.

---

# 7. Difference Between the Main Records

These records should not be mixed up.

| Record | Meaning |
|---|---|
| Service | A reusable definition of what Bomach offers |
| Request | A client expressing a need |
| Assessment | A review needed before pricing or execution |
| Quotation | Bomach's formal offer |
| Approval | Permission required before continuing |
| Invoice | A request for payment |
| Payment | Money received and confirmed |
| Service Order | The record used to execute the work |
| Milestone | A major stage of the work |
| Task | A specific activity assigned to someone |
| Deliverable | A formal output produced from the work |
| Client Approval | Client sign-off on an item or stage |
| Feedback | The client's response to the service |
| Audit Event | A permanent record of an important action |

A simple way to remember the relationship is:

```text
The Service defines the process.

The Request starts the commercial journey.

The Quotation defines the offer.

The Invoice requests payment.

The Payment confirms money received.

The Order controls execution.

The Milestones divide the work into major stages.

The Tasks perform the work.

The Deliverables prove the output.

The Approvals control risk.

The Feedback measures the result.

The Audit Log preserves accountability.
```

---

# 8. Main Sections in the Module

## 8.1 Login

The prototype includes:

- role selection;
- email or username;
- password;
- login button.

The current prototype does not perform real authentication.

In the final application, login should include:

- backend authentication;
- user identity;
- role and permission loading;
- session expiry;
- account status checks;
- secure logout;
- optional multi-factor authentication.

---

## 8.2 Command Center

The Command Center is the main dashboard.

It gives a summary of what is happening across the service system.

It may show:

- requests received;
- quotations waiting for action;
- active service orders;
- confirmed revenue;
- service-level compliance;
- overdue work;
- outstanding payments;
- management alerts;
- recent activity;
- performance by division.

The dashboard should help the user answer:

- What needs attention now?
- What is delayed?
- What is waiting for approval?
- What money is outstanding?
- What changed recently?

The dashboard should also change depending on the user's role.

---

## 8.3 Service Catalogue

The Service Catalogue is the master list of all services.

Each service should show:

- name;
- code;
- division;
- description;
- owner;
- service-level target;
- number of sub-services;
- status;
- active branches.

Possible service statuses include:

```text
Draft
Active
Paused
Archived
```

The catalogue allows the business to manage service definitions separately from client requests.

---

## 8.4 Create Service Wizard

The prototype uses a six-step wizard:

```text
1. Basic Information
2. Sub-services
3. Pricing
4. Request Form
5. Workflow
6. Publication and Branch Activation
```

The purpose of the wizard is to create the full service setup in one process.

The final system should create:

- the service;
- the calculator;
- the request form;
- the workflow;
- the branch settings.

These items should be saved together so that the system does not create a half-configured service.

---

## 8.5 Calculator Library

The Calculator Library defines how a service estimate or price is calculated.

Examples include:

- fixed price;
- unit rate;
- area rate;
- percentage;
- quantity;
- distance and weight;
- package price;
- custom formula.

A calculator may contain:

- calculator name;
- linked service;
- pricing method;
- variables;
- tax;
- required deposit;
- approval threshold;
- formula.

The calculator can help produce an initial estimate before a formal quotation is prepared.

The final production system must not execute raw JavaScript formulas entered by users.

Formula evaluation should use a safe parser or backend-controlled calculation engine.

---

## 8.6 Request Form Builder

Different services need different information.

For example, a delivery request may need:

- pickup address;
- delivery address;
- package type;
- weight;
- recipient.

A construction request may need:

- project location;
- building type;
- floor area;
- drawings;
- budget;
- target start date.

The Request Form Builder allows the service administrator to define the fields required for each service.

Field types may include:

- text;
- number;
- dropdown;
- checkbox;
- date;
- file upload;
- location;
- client identity;
- budget.

---

## 8.7 Workflow Designer

The Workflow Designer defines the stages the service must pass through.

Each stage may contain:

- stage name;
- responsible role;
- due time or service-level target;
- approval requirement;
- evidence requirement;
- client visibility;
- automation rules.

Example automation rules include:

```text
Payment threshold reached
    → Create service order
    → Notify Operations

Stage overdue
    → Escalate to supervisor

Deliverable approved
    → Notify client
    → Unlock next stage

Client requests revision
    → Reopen task
    → Keep the previous document version
```

The workflow is what makes the service executable.

---

## 8.8 Branch Activation

This section controls where a service is available.

It should support:

- active or inactive status by branch;
- branch-specific owner;
- branch-specific service-level target;
- branch capacity;
- branch pricing where needed;
- temporary suspension;
- local approval rules.

The prototype includes:

- Enugu
- Port Harcourt
- Lagos
- Abuja

---

## 8.9 Service Requests

The Service Request Register contains all incoming service requests.

It should display:

- request ID;
- date;
- branch;
- client;
- customer type;
- service;
- source;
- estimate;
- status;
- owner;
- next action.

The Request 360 page should show:

- full client information;
- request details;
- budget;
- estimate;
- current status;
- activity history;
- assigned owner;
- due date;
- next action;
- commercial actions.

The Request 360 page should become the main source of truth for the request.

---

## 8.10 Activity and Communication Journal

The journal should record all important communication.

Examples include:

- phone call;
- WhatsApp;
- email;
- meeting;
- site visit;
- internal note;
- document received.

Each activity should contain:

- activity type;
- actor;
- date and time;
- outcome;
- detailed note;
- next action;
- follow-up date;
- visibility.

This allows another team member to open the request and understand what has happened.

---

## 8.11 Quotations and Proposals

The quotation section manages all commercial offers.

It should support:

- quotation list;
- quotation versions;
- scope;
- line items;
- taxes;
- discounts;
- deposit;
- validity date;
- payment terms;
- approvals;
- client acceptance;
- PDF generation.

The prototype already shows the basic quote-building process.

The final system should provide a more complete commercial document.

---

## 8.12 Invoices and Payments

This section handles:

- invoice creation;
- payment schedules;
- balances;
- payment confirmation;
- receipt generation;
- overdue tracking;
- reconciliation.

Financial actions should be controlled by the backend.

The user interface should never be the final authority for payment status.

---

## 8.13 Approval Queue

The Approval Queue brings all pending approvals into one place.

It may include:

- quotation approvals;
- discount approvals;
- milestone approvals;
- deliverable approvals;
- client approvals;
- closure approvals.

The final system may also support:

- sequential approval;
- parallel approval;
- delegated approval;
- escalation;
- approval comments;
- rejection reasons;
- resubmission.

---

## 8.14 Service Orders

The Service Orders section shows all active and completed work.

The prototype uses a kanban board with columns such as:

```text
Pending Mobilisation
Active
Quality Review
Awaiting Client
Completed
```

Each order card should show:

- client;
- service;
- order number;
- progress;
- due date;
- owner;
- current stage.

---

## 8.15 Order Control Room

The Order Control Room is the main operational page.

It should bring together:

- client information;
- service information;
- progress;
- current stage;
- milestones;
- tasks;
- deliverables;
- activity history;
- financial summary;
- approvals;
- client actions;
- next action.

It should answer:

- What is this work?
- Who owns it?
- What stage is active?
- How far has it progressed?
- What is blocking it?
- What must happen next?
- What evidence has been uploaded?
- What does the client need to approve?

---

## 8.16 Execution Task Board

The Task Board shows work by status.

The basic statuses are:

```text
To Do
In Progress
Review
Done
```

The final task system may also include:

- comments;
- attachments;
- evidence;
- watchers;
- checklists;
- dependencies;
- reminders;
- escalation;
- overdue flags;
- time tracking.

---

## 8.17 Deliverables and Documents

This section manages service outputs.

Examples include:

- reports;
- drawings;
- survey plans;
- certificates;
- legal documents;
- progress evidence;
- handover files.

The final document system should support:

- secure file storage;
- version history;
- approval history;
- client visibility;
- reviewer comments;
- download history;
- access control.

---

## 8.18 Real Estate Inventory

The Real Estate section adds special functionality for estates and properties.

It includes:

- estate selection;
- plot inventory;
- plot status;
- plot price;
- plot size;
- client or reservation holder;
- brokerage listings.

Plot statuses include:

```text
Available
Reserved
Sold
Hold
```

The final system must prevent two people from reserving or selling the same plot at the same time.

---

## 8.19 Specialized Service Control

The Specialized Service section shows that different divisions can use the same core system while keeping their own business process.

The prototype includes:

- Land Surveying
- Engineering
- Courier and Logistics
- Information Technology

The core records remain the same:

- request;
- quotation;
- invoice;
- payment;
- order;
- task;
- deliverable;
- approval;
- audit.

Only the division-specific workflow and special features should change.

---

## 8.20 Client Portal

The Client Portal gives clients access to their own records.

The client should be able to see:

- requests;
- quotations;
- payments;
- active services;
- progress;
- documents;
- approvals;
- required actions;
- feedback forms.

The client should not see:

- internal notes;
- internal approvals;
- private margin information;
- internal audit details;
- management-only information.

---

## 8.21 Feedback and Quality

The Feedback section measures client satisfaction and service quality.

It should support:

- ratings;
- complaints;
- defects;
- rework;
- testimonials;
- referrals;
- corrective actions.

This helps the business understand not only whether the work was completed, but whether the client was satisfied.

---

## 8.22 Reports and Analytics

The Reports section should give management useful information.

Examples include:

- quote-to-order conversion;
- response time;
- gross service margin;
- on-time delivery;
- service performance;
- branch performance;
- revenue;
- outstanding payments;
- client satisfaction;
- rework rate.

Reports should use server-calculated data and permission-controlled access.

---

## 8.23 Audit Log

The Audit Log should preserve important actions.

It should record:

- user;
- role;
- action;
- affected record;
- previous value where needed;
- new value where needed;
- date and time;
- source of action.

Ordinary users should not be able to edit audit records.

---

# 9. Roles in the Module

The prototype includes the following roles:

- CEO / Founder
- Service Administrator
- Head of Operations
- Service Manager
- Finance and Accounts
- Sales / CSRC Officer
- Civil Engineer
- Land Surveyor
- Property Manager
- Project Manager
- Client Portal User

A simple responsibility model is:

| Role | Main Responsibility |
|---|---|
| CEO / Founder | Executive visibility and high-value approvals |
| Service Administrator | Service setup, forms, calculators, workflows, and branches |
| Head of Operations | Delivery supervision and operational performance |
| Service Manager | Request ownership and service coordination |
| Finance and Accounts | Invoices, payments, balances, and financial reporting |
| Sales / CSRC Officer | Request capture, communication, and follow-up |
| Civil Engineer | Technical assessments, inspections, and engineering approvals |
| Land Surveyor | Survey work, plans, field work, and technical review |
| Property Manager | Estate inventory, plot reservations, and property services |
| Project Manager | Projects, milestones, tasks, progress, and handover |
| Client Portal User | Personal requests, payments, progress, documents, and approvals |

The final application must enforce permissions.

Role switching in the prototype is only for demonstration.

---

# 10. Core Data Relationships

The main relationship can be explained like this:

```text
SERVICE
├── Calculator
├── Request Form
├── Workflow
├── Sub-services
└── Branch Availability

SERVICE REQUEST
├── Client
├── Service
├── Branch
├── Assessment
├── Activities
└── Quotation

QUOTATION
├── Request
├── Versions
├── Approval
└── Invoice

INVOICE
├── Quotation
├── Payment Schedule
└── Payments

SERVICE ORDER
├── Request
├── Service
├── Milestones
├── Tasks
├── Deliverables
├── Activities
├── Approvals
└── Feedback

AUDIT LOG
└── Records important actions across the whole module
```

The end-to-end relationship is:

```text
Service
   ↓
Request
   ↓
Quotation
   ↓
Invoice
   ↓
Payment
   ↓
Service Order
   ├── Milestones
   ├── Tasks
   ├── Deliverables
   └── Approvals
           ↓
       Completion
           ↓
        Feedback
```

---

# 11. Current Flow Inside the HTML Prototype

The current prototype is one large HTML file.

The main runtime flow is:

```text
Browser loads the HTML
        ↓
CSS applies the design
        ↓
JavaScript defines roles and sample data
        ↓
The application loads saved browser data
        ↓
Navigation and notifications are created
        ↓
The current page is rendered
        ↓
The user performs an action
        ↓
The application updates its local data
        ↓
The data is saved to localStorage
        ↓
An audit event is added where needed
        ↓
The screen is rendered again
```

The prototype uses:

- one global data object;
- page-rendering functions;
- inline click handlers;
- browser localStorage;
- modal forms;
- toast messages;
- simple audit events.

This is useful for demonstrating the product idea.

It is not the final production structure.

---

# 12. How the Production Application Will Be Different

The production application will separate the large prototype into clear modules.

For example:

```text
Service Administration
├── Service Catalogue
├── Calculators
├── Request Forms
├── Workflows
└── Branch Activation

Commercial Operations
├── Requests
├── Quotations
├── Invoices
└── Approvals

Fulfilment
├── Service Orders
├── Tasks
└── Deliverables

Specialized Services
├── Real Estate
├── Surveying
├── Engineering
├── Logistics
└── Information Technology

Experience and Intelligence
├── Client Portal
├── Feedback
├── Reports
└── Audit
```

The final codebase will use:

- routes for page navigation;
- TanStack Query for backend data;
- TanStack Form for forms and wizards;
- TanStack Table for registers;
- TanStack Virtual for large lists where needed;
- TanStack Pacer for debouncing and throttling;
- shared design components;
- module-owned business logic;
- typed API contracts;
- proper backend persistence;
- proper authentication and authorization;
- automated tests.

---

# 13. What the Prototype Already Demonstrates

The prototype already shows the expected behaviour for:

- login screen;
- role switching;
- dashboard;
- service catalogue;
- service creation wizard;
- calculator library;
- request form builder;
- workflow designer;
- branch activation;
- service requests;
- communication journal;
- quotations;
- approvals;
- invoices;
- payments;
- service orders;
- milestones;
- tasks;
- deliverables;
- real estate inventory;
- specialized service views;
- client portal;
- feedback;
- reports;
- audit log;
- notifications;
- CSV export;
- browser storage.

---

# 14. What the Prototype Does Not Yet Provide

The prototype does not yet provide production-ready:

- authentication;
- authorization;
- backend API;
- database persistence;
- multi-user updates;
- payment gateway integration;
- secure file uploads;
- email or SMS notifications;
- real-time collaboration;
- immutable audit records;
- secure formula execution;
- transaction handling;
- conflict handling;
- document generation;
- digital signatures;
- monitoring;
- backup and recovery;
- complete testing;
- production deployment controls.

The prototype shows what the product should do.

The production application will provide the secure and scalable implementation.

---

# 15. Example End-to-End Scenario

A client wants Bomach to construct a duplex.

## Step 1: Request

The client contacts Bomach.

A request is created with:

- client details;
- project location;
- building type;
- budget;
- target start date;
- available drawings;
- scope.

## Step 2: Review

The request is assigned to the correct team.

The team decides that a site assessment is required.

## Step 3: Assessment

An engineer visits the site and records:

- site conditions;
- measurements;
- risks;
- recommendations;
- uploaded evidence.

## Step 4: Quotation

A quotation is prepared with:

- scope;
- project amount;
- professional fees;
- taxes;
- mobilisation percentage;
- payment terms;
- validity date.

## Step 5: Approval

The quotation goes to the correct approver.

The approver may:

- approve;
- reject;
- request changes.

## Step 6: Client Acceptance

The approved quotation is sent to the client.

The client accepts the offer.

## Step 7: Invoice

Finance creates a mobilisation invoice.

For example:

```text
30% mobilisation payment is required before work begins.
```

## Step 8: Payment Confirmation

Finance confirms the payment.

The system records the payment details and updates the invoice balance.

## Step 9: Service Order

The request becomes a construction service order.

The order contains:

- project manager;
- agreed value;
- start date;
- due date;
- milestones;
- tasks;
- current stage.

## Step 10: Execution

The project team works through:

- mobilisation;
- site setup;
- foundation;
- substructure;
- superstructure;
- inspection;
- handover.

## Step 11: Deliverables

The team uploads:

- reports;
- drawings;
- photographs;
- inspection records;
- certificates;
- handover documents.

## Step 12: Review and Acceptance

The work goes through technical review and client approval.

## Step 13: Completion and Feedback

The order is completed.

The client provides feedback.

Management can now review:

- delivery time;
- revenue;
- progress;
- approvals;
- quality;
- client satisfaction;
- team performance.

---

# 16. What the Module Brings Into the Business

## 16.1 One Standard Process

Every division uses the same main business language:

```text
Request
Quotation
Invoice
Payment
Order
Task
Deliverable
Approval
Feedback
Audit
```

The detailed workflow may change, but the main structure remains consistent.

## 16.2 Clear Traceability

The business can trace:

- where the client came from;
- who handled the request;
- what was quoted;
- who approved it;
- what was paid;
- who performed the work;
- what was delivered;
- whether the client accepted it;
- whether there was a complaint.

## 16.3 Clear Ownership

Each request, order, task, and approval has an owner.

This reduces confusion about who is responsible.

## 16.4 Better Commercial Control

The module helps control:

- pricing;
- discounts;
- quotations;
- approvals;
- payment terms;
- commercial leakage.

## 16.5 Better Operational Visibility

Management can see work by:

- division;
- branch;
- service;
- owner;
- status;
- stage;
- due date;
- progress;
- value.

## 16.6 Flexible Service Configuration

The business can configure:

- forms;
- calculators;
- workflows;
- branches;
- service owners;
- service-level targets.

## 16.7 Better Client Experience

Clients can see:

- progress;
- payments;
- documents;
- approvals;
- required actions.

## 16.8 Better Accountability

Important actions are recorded in the audit log.

## 16.9 Better Reporting

Management can compare:

- branches;
- services;
- teams;
- revenue;
- delays;
- conversion;
- satisfaction;
- rework.

## 16.10 Cross-Division Growth

The same platform can support:

- real estate;
- surveying;
- engineering;
- logistics;
- technology;
- agriculture;
- hospitality.

---

# 17. Important Things I Need to Remember

## A Service is not a Request

A service is reusable configuration.

A request is one client asking for that service.

## A Request is not an Order

A request represents a need or enquiry.

An order represents confirmed work that is ready for execution.

## A Quotation is not an Invoice

A quotation is an offer.

An invoice requests payment after the offer has been accepted.

## A Milestone is not a Task

A milestone is a major stage.

A task is a specific activity inside the stage.

## A Task is not a Deliverable

A task is work that must be done.

A deliverable is the formal output produced.

## Internal Completion is not always Client Acceptance

The team may finish the work, but the service may still require:

- technical review;
- supervisor approval;
- client approval;
- signature;
- handover.

---

# 18. Talking Points

When I need to explain the module, I can use these points:

1. The Service Operations Module manages the full life cycle of every service Bomach provides.

2. It starts by defining the service, including pricing, request fields, workflow, owners, branches, and service-level targets.

3. A client request becomes a structured record instead of remaining inside WhatsApp, email, or a spreadsheet.

4. The request may go through review or assessment before a quotation is prepared.

5. Quotations may require internal approval before they are sent to the client.

6. Once the client accepts, an invoice is created and payment is confirmed.

7. After the required payment threshold is met, the system creates a service order.

8. The service order controls execution through milestones, tasks, deliverables, approvals, and progress updates.

9. The client portal allows the client to follow progress, view payments, access documents, and complete approvals.

10. Feedback, reporting, and audit logs complete the process and give management visibility.

11. The main goal is to connect commercial activity, operational delivery, client experience, and governance in one system.

---

# 19. Two-Minute Explanation

The Bomach Service Operations Module is the part of the system that manages the full journey of every service Bomach offers.

It starts before a client makes a request because the service administrator first defines the service. This includes the service name, division, pricing method, request form, workflow, responsible roles, branches, and service-level expectations.

When a client requests a service, the system creates a structured request record. The request contains the client information, scope, source, budget, owner, status, due date, and communication history.

The request may go through review or professional assessment before a quotation is prepared. The quotation explains what Bomach will deliver, how much it will cost, what deposit is required, and what terms apply.

Where necessary, the quotation goes through internal approval. After approval, it is sent to the client. Once the client accepts, Finance creates an invoice and confirms payment.

When the required payment condition is met, the system creates a service order. The service order controls the actual work through milestones, tasks, deliverables, progress updates, quality reviews, and client approvals.

The client portal allows the client to follow progress, view payments, access documents, and complete required actions.

At the end, the system records feedback, reports, and audit events.

The main idea is that the module connects the commercial side of the business, the operational side, the client experience, and management control in one traceable process.

---

# 20. Final Summary

The Service Operations Module is the system that turns a client request into properly managed service delivery.

It helps Bomach:

- define services;
- capture requests;
- prepare quotations;
- control approvals;
- issue invoices;
- confirm payments;
- create service orders;
- manage milestones and tasks;
- store deliverables;
- collect client approvals;
- track feedback;
- produce reports;
- preserve audit history.

The current HTML file is the product and design guide.

The React and TypeScript application will be the structured production implementation.
