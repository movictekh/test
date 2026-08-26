import type { AuthUser } from '@/app/auth'

import type { AppPermission, PermissionMode } from './permission.types'

export const PERMISSIONS = {
  dashboardView: 'dashboard.view',
  commandCenterView: 'command_center.view',

  notificationsView: 'notifications.view',
  notificationsList: 'notifications.list',
  notificationsMarkRead: 'notifications.mark_read',
  notificationsMarkAllRead: 'notifications.mark_all_read',

  workflowRulesCreate: 'workflow_rules.create',
  workflowRulesView: 'workflow_rules.view',
  workflowRulesList: 'workflow_rules.list',
  workflowRulesUpdate: 'workflow_rules.update',
  workflowRulesDelete: 'workflow_rules.delete',

  employeesList: 'employees.list',
  clientsList: 'clients.list',
  clientsCreate: 'clients.create',

  servicesList: 'services.list',
  servicesView: 'services.view',
  servicesCreate: 'services.create',
  servicesUpdate: 'services.update',
  servicesDelete: 'services.delete',

  categoriesList: 'categories.list',

  branchesList: 'branches.list',

  rolesList: 'roles.list',

  serviceSubservicesList: 'service_subservices.list',
  serviceSubservicesView: 'service_subservices.view',
  serviceSubservicesCreate: 'service_subservices.create',
  serviceSubservicesUpdate: 'service_subservices.update',
  serviceSubservicesDelete: 'service_subservices.delete',

  serviceRequestFormsList: 'service_request_forms.list',
  serviceRequestFormsView: 'service_request_forms.view',
  serviceRequestFormsCreate: 'service_request_forms.create',
  serviceRequestFormsUpdate: 'service_request_forms.update',
  serviceRequestFormsDelete: 'service_request_forms.delete',

  servicePricingConfigsList: 'service_pricing_configs.list',
  servicePricingConfigsView: 'service_pricing_configs.view',
  servicePricingConfigsCreate: 'service_pricing_configs.create',
  servicePricingConfigsUpdate: 'service_pricing_configs.update',
  servicePricingConfigsDelete: 'service_pricing_configs.delete',

  serviceWorkflowsList: 'service_workflows.list',
  serviceWorkflowsView: 'service_workflows.view',
  serviceWorkflowsCreate: 'service_workflows.create',
  serviceWorkflowsUpdate: 'service_workflows.update',
  serviceWorkflowsDelete: 'service_workflows.delete',

  serviceBranchActivationsList: 'service_branch_activations.list',
  serviceBranchActivationsView: 'service_branch_activations.view',
  serviceBranchActivationsCreate: 'service_branch_activations.create',
  serviceBranchActivationsUpdate: 'service_branch_activations.update',
  serviceBranchActivationsDelete: 'service_branch_activations.delete',

  serviceRequestsList: 'service_requests.list',
  serviceRequestsView: 'service_requests.view',
  serviceRequestsCreate: 'service_requests.create',
  serviceRequestsUpdate: 'service_requests.update',
  serviceRequestsDelete: 'service_requests.delete',

  quotesList: 'quotes.list',
  quotesView: 'quotes.view',
  quotesCreate: 'quotes.create',
  quotesUpdate: 'quotes.update',
  quotesDelete: 'quotes.delete',
  quotesApprove: 'quotes.approve',

  serviceInvoicesList: 'service_invoices.list',
  serviceInvoicesView: 'service_invoices.view',
  serviceInvoicesCreate: 'service_invoices.create',
  serviceInvoicesUpdate: 'service_invoices.update',
  serviceInvoicesDelete: 'service_invoices.delete',

  paymentsList: 'payments.list',
  paymentsView: 'payments.view',
  paymentsCreate: 'payments.create',
  paymentsDelete: 'payments.delete',

  expensesApprove: 'expenses.approve',

  expensesReject: 'expenses.reject',
  approvalRequestsList: 'approval_requests.list',
  approvalRequestsView: 'approval_requests.view',
  approvalRequestsCreate: 'approval_requests.create',
  approvalRequestsApprove: 'approval_requests.approve',
  approvalRequestsReject: 'approval_requests.reject',
  approvalRequestsCancel: 'approval_requests.cancel',

  ordersList: 'orders.list',
  ordersView: 'orders.view',
  ordersCreate: 'orders.create',
  ordersUpdate: 'orders.update',
  ordersDelete: 'orders.delete',

  tasksList: 'tasks.list',
  tasksView: 'tasks.view',
  tasksViewOwn: 'tasks.view_own',
  tasksListOwn: 'tasks.list_own',
  tasksCreate: 'tasks.create',
  tasksUpdate: 'tasks.update',
  tasksUpdateOwn: 'tasks.update_own',
  tasksDelete: 'tasks.delete',

  feedbackList: 'feedback.list',
  feedbackView: 'feedback.view',
  feedbackCreate: 'feedback.create',
  feedbackUpdate: 'feedback.update',
  feedbackDelete: 'feedback.delete',

  reportsView: 'reports.view',

  estatesList: 'estates.list',
  estatesView: 'estates.view',
  estatesCreate: 'estates.create',
  estatesUpdate: 'estates.update',
  estatesDelete: 'estates.delete',

  propertiesList: 'properties.list',
  propertiesView: 'properties.view',
  propertiesCreate: 'properties.create',
  propertiesUpdate: 'properties.update',
  propertiesDelete: 'properties.delete',

  brokerageList: 'brokerage.list',
  brokerageView: 'brokerage.view',
  brokerageCreate: 'brokerage.create',
  brokerageUpdate: 'brokerage.update',
  brokerageDelete: 'brokerage.delete',

  // Deferred until owning backend contracts are verified.
  deliverableRead: 'deliverable.read',
  deliverableUpdate: 'deliverable.update',
  deliverableApprove: 'deliverable.approve',
} as const satisfies Record<string, AppPermission>

export function getUserPermissions(user: AuthUser | null): readonly AppPermission[] {
  return user?.permissions ?? []
}

export function hasPermission(user: AuthUser | null, permission: AppPermission): boolean {
  return getUserPermissions(user).includes(permission)
}

export function hasPermissions(
  user: AuthUser | null,
  permissions: readonly AppPermission[],
  mode: PermissionMode = 'all',
): boolean {
  if (permissions.length === 0) return true

  const granted = new Set(getUserPermissions(user))

  return mode === 'all'
    ? permissions.every((permission) => granted.has(permission))
    : permissions.some((permission) => granted.has(permission))
}
