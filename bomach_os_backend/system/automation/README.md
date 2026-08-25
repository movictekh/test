# System Automation

`system.automation` owns generic trigger / condition / action automation.

Canonical ownership:

- WorkflowRule
- WorkflowRuleLog
- workflow-rule CRUD API and schemas
- workflow evaluation engine

Current automation behavior remains unchanged:

- trigger choices remain `service_order_status_changed` and
  `quote_status_changed`;
- the current action remains `send_notification`;
- conditions retain the same AND/operator behavior;
- actions continue to call `system.notifications.services.notify_users`;
- each rule evaluation continues to create WorkflowRuleLog records.

Django identities remain `user.WorkflowRule` and `user.WorkflowRuleLog`.
Historical migrations and tables are unchanged.

Legacy `user.models.workflow_rule`, `user.services.workflow_engine`,
`user.api.schemas.workflow_rule`, and `user.api.v1.workflow_rule` are true
module aliases of the canonical implementation.
