# API-0.05 — Permission Contract Normalization

## Status

API-0.05A establishes the canonical backend permission vocabulary.

API-0.05B applies read-only/write-specific UI behavior after this contract pass is verified.

## Canonical rule

Verified frontend authorization uses backend permission strings directly:

```text
resource.action
```

The frontend does not translate `list` or `view` into `read`.

Example:

```text
orders.list
orders.view
```

remain two different permissions.

## Auth hydration

```text
User
→ Employee
→ Role.permissions
→ flatten resource/action map
→ exact app-used permissions
→ AuthUser.permissions
```

`mapBackendPermissions` normalizes and filters only. It does not invent aliases.

## Service Administration resources

```text
services
service_subservices
service_request_forms
service_pricing_configs
service_workflows
service_branch_activations
```

## Deferred frontend permissions

These remain explicitly temporary until their owning backend authorization contract is signed off:

```text
payment.confirm
approval.act
deliverable.read
deliverable.update
deliverable.approve
real-estate.read
```

They must not be treated as verified backend contracts.

Command Center and Notifications are not being invented as backend feature integrations here.

Audit remains outside active product work while its product status is on hold.

## Next — API-0.05B

Wire exact permissions into:

- navigation;
- direct routes;
- Service Administration detail access;
- create/update/delete controls;
- Request Form actions;
- Pricing Config actions;
- Workflow actions;
- Branch Activation actions;
- read-only regression tests.
