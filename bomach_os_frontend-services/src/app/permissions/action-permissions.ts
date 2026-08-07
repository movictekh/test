import type { AuthUser } from '@/app/auth'

import { PERMISSIONS, hasPermission } from './permissions'

export const APP_ACTIONS = {
  serviceCreate: 'services.create',
  serviceUpdate: 'services.update',
  requestCreate: 'service_requests.create',
  requestUpdate: 'service_requests.update',
  quoteCreate: 'quotes.create',
  quoteApprove: 'quotes.approve',
  invoiceCreate: 'service_invoices.create',
  paymentConfirm: 'payment.confirm',
  approvalAct: 'approval.act',
  orderUpdate: 'orders.update',
  taskUpdate: 'tasks.update',
  deliverableUpdate: 'deliverable.update',
  deliverableApprove: 'deliverable.approve',
} as const

export type AppAction = keyof typeof APP_ACTIONS

const actionPermissions = {
  serviceCreate: PERMISSIONS.servicesCreate,
  serviceUpdate: PERMISSIONS.servicesUpdate,
  requestCreate: PERMISSIONS.serviceRequestsCreate,
  requestUpdate: PERMISSIONS.serviceRequestsUpdate,
  quoteCreate: PERMISSIONS.quotesCreate,
  quoteApprove: PERMISSIONS.quotesApprove,
  invoiceCreate: PERMISSIONS.serviceInvoicesCreate,
  paymentConfirm: PERMISSIONS.paymentConfirm,
  approvalAct: PERMISSIONS.approvalAct,
  orderUpdate: PERMISSIONS.ordersUpdate,
  taskUpdate: PERMISSIONS.tasksUpdate,
  deliverableUpdate: PERMISSIONS.deliverableUpdate,
  deliverableApprove: PERMISSIONS.deliverableApprove,
} as const

export function canPerformAction(user: AuthUser | null, action: AppAction): boolean {
  return hasPermission(user, actionPermissions[action])
}
