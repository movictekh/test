import type { AuthUser } from '@/app/auth'

import type { AppPermission, PermissionMode } from './permission.types'

export const PERMISSIONS = {
  dashboardRead: 'dashboard.read',
  serviceRead: 'service.read',
  serviceCreate: 'service.create',
  serviceUpdate: 'service.update',
  requestRead: 'request.read',
  requestCreate: 'request.create',
  requestUpdate: 'request.update',
  quoteRead: 'quote.read',
  quoteCreate: 'quote.create',
  quoteApprove: 'quote.approve',
  invoiceRead: 'invoice.read',
  invoiceCreate: 'invoice.create',
  paymentConfirm: 'payment.confirm',
  approvalRead: 'approval.read',
  approvalAct: 'approval.act',
  orderRead: 'order.read',
  orderUpdate: 'order.update',
  taskRead: 'task.read',
  taskUpdate: 'task.update',
  deliverableRead: 'deliverable.read',
  deliverableUpdate: 'deliverable.update',
  deliverableApprove: 'deliverable.approve',
  realEstateRead: 'real-estate.read',
  reportRead: 'report.read',
  auditRead: 'audit.read',
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
