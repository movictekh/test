import { describe, expect, it } from 'vitest'

import type { AuthUser } from '@/app/auth'
import { PERMISSIONS } from '@/app/permissions'

import { canApproveQueueItem, canRejectQueueItem } from './approval-queue-capabilities'
import type { ApprovalQueueItem } from './approval-queue.types'

const item = (overrides: Partial<ApprovalQueueItem>): ApprovalQueueItem => ({
  id: 'deliverable-1',
  source: 'deliverable',
  sourceDisplay: 'Deliverable',
  refNumber: 'DEL-1',
  subject: 'Survey plan',
  requesterName: 'Surveyor',
  approverName: 'Supervisor',
  amount: null,
  createdAt: '',
  status: 'pending',
  actionLabel: 'Approve',
  approveUrl: '/api/v1/orders/1/deliverables/1/approve',
  rejectUrl: '/api/v1/orders/1/deliverables/1/reject',
  ...overrides,
})

const userWith = (...permissions: string[]) =>
  ({
    id: 1,
    permissions,
  }) as unknown as AuthUser

describe('approval queue capabilities', () => {
  it('uses order update permission for deliverable decisions', () => {
    const user = userWith(PERMISSIONS.ordersUpdate)
    expect(canApproveQueueItem(user, item({}))).toBe(true)
    expect(canRejectQueueItem(user, item({}))).toBe(true)
  })

  it('does not invent quote rejection when no URL is supplied', () => {
    const quote = item({
      source: 'quotation',
      approveUrl: '/api/v1/quotes/1/approve',
      rejectUrl: null,
    })
    const user = userWith(PERMISSIONS.quotesApprove)
    expect(canApproveQueueItem(user, quote)).toBe(true)
    expect(canRejectQueueItem(user, quote)).toBe(false)
  })
})
