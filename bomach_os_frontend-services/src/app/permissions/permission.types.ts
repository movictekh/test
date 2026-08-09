/**
 * Permissions consumed by the Service Operations frontend.
 *
 * Verified permissions mirror backend PERMISSIONS_MAP exactly:
 *   resource.action
 *
 * Do not rename backend actions to frontend synonyms such as "read" or "write".
 */
export const VERIFIED_APP_PERMISSION_VALUES = [
  'dashboard.view',

  'command_center.view',
  'notifications.view',
  'notifications.list',
  'notifications.mark_read',
  'notifications.mark_all_read',
  'workflow_rules.create',
  'workflow_rules.view',
  'workflow_rules.list',
  'workflow_rules.update',
  'workflow_rules.delete',
  'services.list',
  'services.view',
  'services.create',
  'services.update',
  'services.delete',

  'categories.list',

  'branches.list',

  'roles.list',

  'service_subservices.list',
  'service_subservices.view',
  'service_subservices.create',
  'service_subservices.update',
  'service_subservices.delete',

  'service_request_forms.list',
  'service_request_forms.view',
  'service_request_forms.create',
  'service_request_forms.update',
  'service_request_forms.delete',

  'service_pricing_configs.list',
  'service_pricing_configs.view',
  'service_pricing_configs.create',
  'service_pricing_configs.update',
  'service_pricing_configs.delete',

  'service_workflows.list',
  'service_workflows.view',
  'service_workflows.create',
  'service_workflows.update',
  'service_workflows.delete',

  'service_branch_activations.list',
  'service_branch_activations.view',
  'service_branch_activations.create',
  'service_branch_activations.update',
  'service_branch_activations.delete',

  'service_requests.list',
  'service_requests.view',
  'service_requests.create',
  'service_requests.update',
  'service_requests.delete',

  'quotes.list',
  'quotes.view',
  'quotes.create',
  'quotes.update',
  'quotes.delete',
  'quotes.approve',

  'service_invoices.list',
  'service_invoices.view',
  'service_invoices.create',
  'service_invoices.update',
  'service_invoices.delete',

  'payments.list',
  'payments.view',
  'payments.create',
  'payments.delete',

  'approval_requests.list',
  'approval_requests.view',
  'approval_requests.create',
  'approval_requests.approve',
  'approval_requests.reject',
  'approval_requests.cancel',

  'orders.list',
  'orders.view',
  'orders.create',
  'orders.update',
  'orders.delete',

  'tasks.list',
  'tasks.view',
  'tasks.view_own',
  'tasks.list_own',
  'tasks.create',
  'tasks.update',
  'tasks.update_own',
  'tasks.delete',

  'feedback.list',
  'feedback.view',
  'feedback.create',
  'feedback.update',
  'feedback.delete',

  'reports.view',
  'audit_logs.list',

  'estates.list',
  'estates.view',
  'estates.create',
  'estates.update',
  'estates.delete',

  'properties.list',
  'properties.view',
  'properties.create',
  'properties.update',
  'properties.delete',

  'brokerage.list',
  'brokerage.view',
  'brokerage.create',
  'brokerage.update',
  'brokerage.delete',
] as const

/**
 * Temporary frontend-only permissions for screens whose exact backend
 * authorization contract is not yet signed off.
 */
export const DEFERRED_FRONTEND_PERMISSION_VALUES = [
  'deliverable.read',
  'deliverable.update',
  'deliverable.approve',
] as const

export const APP_PERMISSION_VALUES = [
  ...VERIFIED_APP_PERMISSION_VALUES,
  ...DEFERRED_FRONTEND_PERMISSION_VALUES,
] as const

export type AppPermission = (typeof APP_PERMISSION_VALUES)[number]
export type VerifiedAppPermission = (typeof VERIFIED_APP_PERMISSION_VALUES)[number]
export type DeferredFrontendPermission = (typeof DEFERRED_FRONTEND_PERMISSION_VALUES)[number]

export type PermissionMode = 'all' | 'any'
