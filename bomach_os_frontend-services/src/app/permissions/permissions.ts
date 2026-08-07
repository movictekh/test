import type { AppRole, AuthUser } from '@/app/auth'

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
  portalRead: 'portal.read',
} as const satisfies Record<string, AppPermission>

const allPermissions: readonly AppPermission[] = Object.values(PERMISSIONS)

export const rolePermissions: Record<AppRole, readonly AppPermission[]> = {
  CEO: allPermissions,
  // Demo login role: full staff + portal access for local prototype work.
  SERVICE_ADMINISTRATOR: allPermissions,
  HEAD_OF_OPERATIONS: [
    PERMISSIONS.dashboardRead,
    PERMISSIONS.serviceRead,
    PERMISSIONS.requestRead,
    PERMISSIONS.requestUpdate,
    PERMISSIONS.quoteRead,
    PERMISSIONS.quoteApprove,
    PERMISSIONS.invoiceRead,
    PERMISSIONS.approvalRead,
    PERMISSIONS.approvalAct,
    PERMISSIONS.orderRead,
    PERMISSIONS.orderUpdate,
    PERMISSIONS.taskRead,
    PERMISSIONS.taskUpdate,
    PERMISSIONS.deliverableRead,
    PERMISSIONS.realEstateRead,
    PERMISSIONS.deliverableApprove,
    PERMISSIONS.reportRead,
  ],
  SERVICE_MANAGER: [
    PERMISSIONS.dashboardRead,
    PERMISSIONS.serviceRead,
    PERMISSIONS.requestRead,
    PERMISSIONS.requestCreate,
    PERMISSIONS.requestUpdate,
    PERMISSIONS.quoteRead,
    PERMISSIONS.quoteCreate,
    PERMISSIONS.invoiceRead,
    PERMISSIONS.approvalRead,
    PERMISSIONS.orderRead,
    PERMISSIONS.orderUpdate,
    PERMISSIONS.taskRead,
    PERMISSIONS.taskUpdate,
    PERMISSIONS.deliverableRead,
    PERMISSIONS.realEstateRead,
    PERMISSIONS.deliverableUpdate,
  ],
  FINANCE: [
    PERMISSIONS.dashboardRead,
    PERMISSIONS.requestRead,
    PERMISSIONS.quoteRead,
    PERMISSIONS.invoiceRead,
    PERMISSIONS.invoiceCreate,
    PERMISSIONS.paymentConfirm,
    PERMISSIONS.reportRead,
  ],
  SALES_CSRC: [
    PERMISSIONS.dashboardRead,
    PERMISSIONS.serviceRead,
    PERMISSIONS.requestRead,
    PERMISSIONS.requestCreate,
    PERMISSIONS.requestUpdate,
    PERMISSIONS.quoteRead,
    PERMISSIONS.quoteCreate,
    PERMISSIONS.invoiceRead,
    PERMISSIONS.orderRead,
  ],
  CIVIL_ENGINEER: [
    PERMISSIONS.dashboardRead,
    PERMISSIONS.requestRead,
    PERMISSIONS.requestUpdate,
    PERMISSIONS.orderRead,
    PERMISSIONS.orderUpdate,
    PERMISSIONS.taskRead,
    PERMISSIONS.taskUpdate,
    PERMISSIONS.deliverableRead,
    PERMISSIONS.deliverableUpdate,
  ],
  LAND_SURVEYOR: [
    PERMISSIONS.dashboardRead,
    PERMISSIONS.requestRead,
    PERMISSIONS.requestUpdate,
    PERMISSIONS.orderRead,
    PERMISSIONS.orderUpdate,
    PERMISSIONS.taskRead,
    PERMISSIONS.taskUpdate,
    PERMISSIONS.deliverableRead,
    PERMISSIONS.deliverableUpdate,
  ],
  PROPERTY_MANAGER: [
    PERMISSIONS.dashboardRead,
    PERMISSIONS.serviceRead,
    PERMISSIONS.requestRead,
    PERMISSIONS.requestCreate,
    PERMISSIONS.requestUpdate,
    PERMISSIONS.orderRead,
    PERMISSIONS.orderUpdate,
    PERMISSIONS.taskRead,
    PERMISSIONS.taskUpdate,
    PERMISSIONS.realEstateRead,
  ],
  PROJECT_MANAGER: [
    PERMISSIONS.dashboardRead,
    PERMISSIONS.requestRead,
    PERMISSIONS.orderRead,
    PERMISSIONS.orderUpdate,
    PERMISSIONS.taskRead,
    PERMISSIONS.taskUpdate,
    PERMISSIONS.deliverableRead,
    PERMISSIONS.deliverableUpdate,
  ],
  CLIENT: [PERMISSIONS.portalRead],
}

export function getUserPermissions(user: AuthUser | null): readonly AppPermission[] {
  if (!user) return []
  return user.permissions.length > 0 ? user.permissions : rolePermissions[user.role]
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
