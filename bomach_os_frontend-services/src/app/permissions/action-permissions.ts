import type { AuthUser } from '@/app/auth'

import { PERMISSIONS, hasPermission } from './permissions'

export const APP_ACTIONS = {
  serviceCreate: 'service.create',
  serviceUpdate: 'service.update',
  requestCreate: 'request.create',
  requestUpdate: 'request.update',
  quoteCreate: 'quote.create',
  quoteApprove: 'quote.approve',
  invoiceCreate: 'invoice.create',
  paymentConfirm: 'payment.confirm',
  approvalAct: 'approval.act',
  orderUpdate: 'order.update',
  taskUpdate: 'task.update',
  deliverableUpdate: 'deliverable.update',
  deliverableApprove: 'deliverable.approve',
} as const

export type AppAction = keyof typeof APP_ACTIONS

const actionPermissions = {
  serviceCreate: PERMISSIONS.serviceCreate,
  serviceUpdate: PERMISSIONS.serviceUpdate,
  requestCreate: PERMISSIONS.requestCreate,
  requestUpdate: PERMISSIONS.requestUpdate,
  quoteCreate: PERMISSIONS.quoteCreate,
  quoteApprove: PERMISSIONS.quoteApprove,
  invoiceCreate: PERMISSIONS.invoiceCreate,
  paymentConfirm: PERMISSIONS.paymentConfirm,
  approvalAct: PERMISSIONS.approvalAct,
  orderUpdate: PERMISSIONS.orderUpdate,
  taskUpdate: PERMISSIONS.taskUpdate,
  deliverableUpdate: PERMISSIONS.deliverableUpdate,
  deliverableApprove: PERMISSIONS.deliverableApprove,
} as const

export function canPerformAction(user: AuthUser | null, action: AppAction): boolean {
  return hasPermission(user, actionPermissions[action])
}
