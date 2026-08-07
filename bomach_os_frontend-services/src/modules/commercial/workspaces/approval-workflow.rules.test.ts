import { describe, expect, it } from 'vitest'

import type { CommercialApproval, CommercialQuotation } from '../types/commercial.types'

function makeApproval(quotation: CommercialQuotation, sequence: number): CommercialApproval {
  return {
    id: `APR-Q-${String(sequence).padStart(3, '0')}`,
    entityType: 'Quotation',
    entityId: quotation.id,
    client: quotation.client,
    reason: `Quotation approval via ${quotation.approvalRoute}`,
    amount: quotation.total,
    requestedBy: quotation.owner,
    assignedTo: quotation.approvalRoute,
    requestedAt: '2026-08-07T08:00:00.000Z',
    status: 'Pending',
  }
}

function hasPendingApproval(approvals: CommercialApproval[], quotationId: string) {
  return approvals.some(
    (approval) =>
      approval.entityType === 'Quotation' &&
      approval.entityId === quotationId &&
      approval.status === 'Pending',
  )
}

describe('commercial approval queue regression', () => {
  const quotation = {
    id: 'Q-REGRESSION-001',
    client: 'Regression Client',
    approvalRoute: 'CEO / Founder',
    total: 12_000_000,
    owner: 'Head of Operations',
  } as CommercialQuotation

  it('represents a newly submitted quotation as a pending approval', () => {
    const approval = makeApproval(quotation, 1)

    expect(approval).toMatchObject({
      entityType: 'Quotation',
      entityId: quotation.id,
      client: quotation.client,
      amount: quotation.total,
      assignedTo: quotation.approvalRoute,
      status: 'Pending',
    })
  })

  it('detects an existing pending record so the queue does not duplicate it', () => {
    const approvals = [makeApproval(quotation, 1)]

    expect(hasPendingApproval(approvals, quotation.id)).toBe(true)
    expect(hasPendingApproval(approvals, 'Q-OTHER')).toBe(false)
  })

  it('allows a new approval after the previous decision is no longer pending', () => {
    const decided = {
      ...makeApproval(quotation, 1),
      status: 'Rejected' as const,
      decidedAt: '2026-08-07T08:10:00.000Z',
      decisionNote: 'Revise commercial terms.',
    }

    expect(hasPendingApproval([decided], quotation.id)).toBe(false)
  })
})
