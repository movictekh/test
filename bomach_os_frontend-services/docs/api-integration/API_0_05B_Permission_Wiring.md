# API-0.05B — Permission Behavior Wiring

## Scope

This pass applies the canonical backend permission contract from API-0.05A to
Service Administration behavior.

The backend remains the final security boundary. The frontend now also presents
the correct read-only and mutation affordances before a request is attempted.

## Rules

### Collection access

Navigation and route access use `*.list`.

Examples:

```text
Service Catalogue       -> services.list
Calculator Library      -> service_pricing_configs.list
Request Form Builder    -> service_request_forms.list
Workflow Designer       -> service_workflows.list
Branch Activation       -> service_branch_activations.list
```

### Detail access

Opening a Service detail requires:

```text
services.view
```

A user with only `services.list` may see the catalogue but does not receive the
detail action.

### Create access

```text
Create Service     -> services.create
Duplicate Service  -> services.create
New Calculator     -> service_pricing_configs.create
New Request        -> service_requests.create
```

### Update access

```text
Request Form save/edit   -> service_request_forms.update
Workflow edit/save       -> service_workflows.update
Branch activation edit   -> service_branch_activations.update
```

## Current Configure Service workspace caveat

The current mock Configure Service workspace saves core Service data,
Subservices, Request Form, Pricing Config, Workflow and Branch Activation in one
combined mutation.

The real backend does not work that way; API-1 will split these into independent
endpoint mutations.

Until API-1 replaces the mock combined mutation, saving the full Configure
Service workspace requires all affected update permissions:

```text
services.update
service_subservices.update
service_request_forms.update
service_pricing_configs.update
service_workflows.update
service_branch_activations.update
```

A user with `services.view` but without that complete update set gets a
view-only Configure Service workspace.

This is intentionally conservative and prevents the frontend from presenting a
combined mutation that the user's backend role is not fully authorized to
perform.

## Deliverables

Deliverables remains excluded from canonical authorization wiring because its
matching backend contract is not implemented/verified.

See:

```text
docs/api-integration/Missing_Backend_Contracts.md
```
