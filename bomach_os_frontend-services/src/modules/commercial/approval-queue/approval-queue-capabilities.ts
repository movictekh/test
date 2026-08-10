import type { AuthUser } from '@/app/auth'
import { hasPermission, PERMISSIONS } from '@/app/permissions'

import type { ApprovalQueueItem } from './approval-queue.types'

export function canApproveQueueItem(user: AuthUser | null, item: ApprovalQueueItem) {
  if (!item.approveUrl || item.status !== 'pending') return false

  if (item.source === 'quotation') {
    return hasPermission(user, PERMISSIONS.quotesApprove)
  }

  if (item.source === 'deliverable') {
    return hasPermission(user, PERMISSIONS.ordersUpdate)
  }

  if (item.source === 'expense') {
    return hasPermission(user, PERMISSIONS.expensesApprove)
  }

  return false
}

export function canRejectQueueItem(user: AuthUser | null, item: ApprovalQueueItem) {
  if (!item.rejectUrl || item.status !== 'pending') return false

  if (item.source === 'deliverable') {
    return hasPermission(user, PERMISSIONS.ordersUpdate)
  }

  if (item.source === 'expense') {
    return hasPermission(user, PERMISSIONS.expensesReject)
  }

  return false
}
