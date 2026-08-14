# Service Operations — Final Architecture Sign-Off

- Sprint: ARCH-5
- Status: Complete
- Date: 2026-08-14
- Architecture style: Modular monolith

## Final ownership

Service Operations owns the business lifecycle:

```text
Service Definition
→ Service Request
→ Quote
→ Invoice
→ payment condition
→ Service Order
→ execution
→ Deliverable
→ Feedback / reporting
```

## Final source structure

```text
domains/service_operations/
├── models/
│   ├── catalogue.py
│   ├── requests.py
│   ├── delivery.py
│   └── feedback.py
├── services/
│   ├── catalogue.py
│   └── orders.py
├── selectors.py
└── api/
    └── v1/
        ├── routers/
        │   ├── catalogue.py
        │   ├── categories.py
        │   ├── service_leads.py
        │   ├── service_request_admin.py
        │   ├── client_service_portal.py
        │   ├── service_requests.py
        │   ├── _service_request_support.py
        │   ├── quotes.py
        │   ├── invoices.py
        │   ├── orders.py
        │   ├── feedback.py
        │   └── reports.py
        └── schemas/
```

## Dependency direction

```text
HTTP routers
    ↓
application services / selectors
    ↓
Service Operations models
```

API-only serialization/query support remains private to the API v1 layer where it is
transport-specific.

## Django migration identity

Service Operations model source is domain-owned while existing Django identities remain under
the `services` app label.

This intentionally preserves:

- migration history;
- table names;
- foreign-key identities;
- existing data.

A true app-label migration is explicitly outside this sprint.

## Intentional compatibility/transitional seams

The following are intentional and are not unfinished Service Operations work:

### `services/models/service.py`

Thin Django compatibility shell only.

### `services/models/feedback.py`

Thin Django compatibility shell only.

### `services/models/payment.py`

`Invoice` and `InvoiceItem` are imported from Service Operations.

`Payment` remains physically owned by the transitional Finance workstream so this sprint does
not modify Finance endpoint/business ownership.

### Finance calls

Service Operations may call Finance application services where payment review/exception
handling is required.

Service Operations does not depend on Finance HTTP/router modules.

### Expense reporting

Any existing Service Operations reporting read from the Finance-owned Expense model is a
cross-domain read and does not transfer Expense ownership.

## Service Request HTTP surface

The external `/service-requests/` contract remains unchanged while source is separated into:

1. staff/admin operations;
2. client commercial/delivery portal;
3. client request intake/self-service.

Generic request-id routes remain registered last.

## File growth standard

Files are split by responsibility, not arbitrary line count.

Guidance:

- under 500 lines: normally acceptable when cohesive;
- 500–799 lines: review as the file evolves;
- 800+ lines: explicit responsibility review required before sprint sign-off.

This is a review trigger, not a mechanical style rule.

## Regression guarantees for this sprint

The final audit verifies:

- Python import/compile integrity;
- Django system checks;
- no migration changes;
- domain model app-label identity;
- Finance Payment boundary;
- direct domain API composition;
- absence of migrated legacy Service Operations API source;
- Service Request route precedence;
- complete HTTP/OpenAPI compatibility excluding generated operation IDs.

## Sprint conclusion

ARCH-5 Service Operations is complete for the current modular-monolith stage.

Do not continue polishing this domain merely for architectural symmetry. Re-open it only for:

- a real defect;
- a real new Service Operations feature;
- a demonstrated boundary violation;
- a later planned Django app-label migration.

The next architecture sprint should move to another legacy ownership area rather than continue
refactoring Service Operations.

## Final file-size report

```text
Service Operations Python file-size report
=========================================
  778  WATCH            domains/service_operations/models/delivery.py
  678  WATCH            domains/service_operations/api/v1/routers/orders.py
  547  WATCH            domains/service_operations/models/requests.py
  503  WATCH            domains/service_operations/api/v1/routers/_service_request_support.py
  500  WATCH            domains/service_operations/api/v1/schemas/lifecycle.py
  476  OK               domains/service_operations/api/v1/routers/service_configuration.py
  444  OK               domains/service_operations/models/catalogue.py
  395  OK               domains/service_operations/api/v1/routers/client_service_portal.py
  344  OK               domains/service_operations/api/v1/routers/quotes.py
  329  OK               domains/service_operations/api/v1/routers/catalogue.py
  316  OK               domains/service_operations/api/v1/routers/invoices.py
  308  OK               domains/service_operations/api/v1/routers/_catalogue_support.py
  281  OK               domains/service_operations/api/v1/routers/reports.py
  252  OK               domains/service_operations/api/v1/routers/service_request_admin.py
  228  OK               domains/service_operations/api/v1/schemas/catalogue.py
  228  OK               domains/service_operations/api/v1/routers/service_requests.py
  181  OK               domains/service_operations/api/v1/schemas/service_requests.py
  181  OK               domains/service_operations/api/v1/routers/feedback.py
  117  OK               domains/service_operations/services/catalogue.py
  105  OK               domains/service_operations/api/v1/routers/service_branch_activation.py
   85  OK               domains/service_operations/api/v1/routers/service_leads.py
   79  OK               domains/service_operations/services/orders.py
   69  OK               domains/service_operations/models/feedback.py
   66  OK               domains/service_operations/api/v1/routers/categories.py
   58  OK               domains/service_operations/api/v1/schemas/feedback.py
   42  OK               domains/service_operations/selectors.py
   24  OK               domains/service_operations/api/v1/schemas/reports.py
   17  OK               domains/service_operations/api/v1/__init__.py
   10  OK               domains/service_operations/models/__init__.py
    5  OK               domains/service_operations/services/__init__.py
    1  OK               domains/service_operations/api/v1/schemas/__init__.py
    1  OK               domains/service_operations/api/v1/routers/__init__.py
    1  OK               domains/service_operations/api/__init__.py
```

## Final registered model audit

```text
Service Operations models registered: 24
ClientFeedback|services.clientfeedback|services_clientfeedback|domains.service_operations.models.feedback
Invoice|services.invoice|services_invoice|domains.service_operations.models.delivery
InvoiceItem|services.invoiceitem|services_invoiceitem|domains.service_operations.models.delivery
Quote|services.quote|services_quote|domains.service_operations.models.delivery
Service|services.service|services_service|domains.service_operations.models.catalogue
ServiceBranchActivation|services.servicebranchactivation|services_servicebranchactivation|domains.service_operations.models.catalogue
ServiceCategory|services.servicecategory|services_servicecategory|domains.service_operations.models.catalogue
ServiceDeliverable|services.servicedeliverable|services_servicedeliverable|domains.service_operations.models.delivery
ServiceExecutionTask|services.serviceexecutiontask|services_serviceexecutiontask|domains.service_operations.models.delivery
ServiceLead|services.servicelead|services_servicelead|domains.service_operations.models.requests
ServiceOrder|services.serviceorder|services_serviceorder|domains.service_operations.models.delivery
ServiceOrderActivity|services.serviceorderactivity|services_serviceorderactivity|domains.service_operations.models.delivery
ServiceOrderMilestone|services.serviceordermilestone|services_serviceordermilestone|domains.service_operations.models.delivery
ServicePricingConfig|services.servicepricingconfig|services_servicepricingconfig|domains.service_operations.models.catalogue
ServicePricingField|services.servicepricingfield|services_servicepricingfield|domains.service_operations.models.catalogue
ServiceRequest|services.servicerequest|services_servicerequest|domains.service_operations.models.requests
ServiceRequestActivity|services.servicerequestactivity|services_servicerequestactivity|domains.service_operations.models.requests
ServiceRequestAnswer|services.servicerequestanswer|services_servicerequestanswer|domains.service_operations.models.requests
ServiceRequestAttachment|services.servicerequestattachment|services_servicerequestattachment|domains.service_operations.models.requests
ServiceRequestField|services.servicerequestfield|services_servicerequestfield|domains.service_operations.models.catalogue
ServiceRequestForm|services.servicerequestform|services_servicerequestform|domains.service_operations.models.catalogue
ServiceSubService|services.servicesubservice|services_servicesubservice|domains.service_operations.models.catalogue
ServiceWorkflow|services.serviceworkflow|services_serviceworkflow|domains.service_operations.models.catalogue
ServiceWorkflowStage|services.serviceworkflowstage|services_serviceworkflowstage|domains.service_operations.models.catalogue
Payment|services.payment|services_payment|services.models.payment
```
