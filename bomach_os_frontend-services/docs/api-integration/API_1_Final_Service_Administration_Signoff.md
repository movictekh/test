# API-1 — Service Administration Final Integration

## Completed scope

```text
API-1.01 Contract layer
API-1.02 Catalogue live reads
API-1.03 Service core
API-1.04 Subservices
API-1.05 Request Forms
API-1.06 Pricing Configs
API-1.07 Workflows
API-1.08 Branch Activation
API-1.09 Publish/readiness
API-1.10 Filtering/pagination
API-1.11 Integration sign-off
```

## Real backend flows

Service catalogue, category lookup, pricing, request forms, workflows,
branches and branch activations now use backend APIs.

The completed create lifecycle remains incremental rather than pretending to be
one database transaction across multiple endpoints.

## Publish readiness

A Service can publish when the backend prerequisites are satisfied:

1. active request form;
2. active pricing config;
3. at least one active branch.

Workflow remains optional.

## Branch identity

Branch Activation no longer generates slug IDs from branch names. It loads real
numeric branch IDs from `GET /branches` and submits those IDs to Service branch
activation endpoints.

## Workflow owner roles

The existing UI displays role names, but the backend persists `owner_role_id`.
Until a verified role selector is added, the frontend deliberately submits
`owner_role_id: null` instead of guessing an ID.

## Catalogue filters

Catalogue search/status/division and pagination now participate in the backend
query rather than downloading a large fixed record set and filtering it locally.

## Command Center

Command Center stays permission-gated with `dashboard.view`. Its Service
Operations aggregate backend contract remains outside API-1 and is not changed
by this sign-off.

## Recommended Service Administrator test grants

```text
roles.view_own

services.*
categories.list
branches.list

service_subservices.*
service_request_forms.*
service_pricing_configs.*
service_workflows.*
service_branch_activations.*
```

`dashboard.view` is optional depending on whether the role should open Command Center.
