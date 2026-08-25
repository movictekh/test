# System Approvals

`system.approvals` owns the reusable cross-domain approval-flow capability.

Canonical ownership:

- ApprovalFlow
- ApprovalFlowStep
- ApprovalRequest
- ApprovalDecision
- approval flow/request HTTP API
- approval API schemas

Existing behavior and persistence remain unchanged:

- Django identities remain `user.*`;
- database tables remain unchanged;
- historical migrations remain under `user`;
- legacy `user.models.approval`, `user.api.schemas.approval`, and
  `user.api.v1.approval` module paths remain true aliases of the canonical
  System Approvals modules.

This capability is intentionally distinct from `user.api.v1.approval_queue`.
The approval queue is a read-side aggregation over Quote, ServiceDeliverable,
and Expense domain states. It is not the generic ApprovalFlow engine and is
left untouched in this batch.
