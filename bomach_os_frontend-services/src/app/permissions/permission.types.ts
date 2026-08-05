export const APP_PERMISSION_VALUES = [
  'dashboard.read',
  'service.read',
  'service.create',
  'service.update',
  'request.read',
  'request.create',
  'request.update',
  'quote.read',
  'quote.create',
  'quote.approve',
  'invoice.read',
  'invoice.create',
  'payment.confirm',
  'approval.read',
  'approval.act',
  'order.read',
  'order.update',
  'task.read',
  'task.update',
  'deliverable.read',
  'deliverable.update',
  'deliverable.approve',
  'real-estate.read',
  'report.read',
  'audit.read',
  'portal.read',
] as const

export type AppPermission = (typeof APP_PERMISSION_VALUES)[number]

export type PermissionMode = 'all' | 'any'
