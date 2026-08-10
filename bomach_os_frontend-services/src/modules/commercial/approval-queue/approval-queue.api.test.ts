import { describe, expect, it } from 'vitest'

import { normalizeApprovalActionPath } from './approval-queue.api'

describe('approval queue action path', () => {
  it('normalizes queue-provided API v1 paths for the shared client', () => {
    expect(normalizeApprovalActionPath('/api/v1/quotes/7/approve')).toBe('/quotes/7/approve')

    expect(normalizeApprovalActionPath('/api/v1/orders/4/deliverables/9/reject')).toBe(
      '/orders/4/deliverables/9/reject',
    )
  })

  it('rejects unknown action paths rather than guessing', () => {
    expect(() => normalizeApprovalActionPath('/api/v1/unknown/9/approve')).toThrow()
    expect(() => normalizeApprovalActionPath('/quotes/7/approve')).toThrow()
  })
})
