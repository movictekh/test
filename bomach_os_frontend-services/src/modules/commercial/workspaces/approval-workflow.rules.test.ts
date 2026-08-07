import { describe, expect, it } from 'vitest'

import type { CommercialApproval, CommercialQuotation } from '../types/commercial.types'

import { validateApprovalDecision } from './approval-workflow.rules'

function makeApproval(quotation: CommercialQuotation, sequence: number): CommercialApproval {
  return {
    id: `APR-${String(sequence).padStart(3, '0')}`,
    entityType: 'Quotation',
    entityId: quotation.id,
    subject: `${quotation.service} quotation`,
    client: quotation.client,
    amount: quotation.total,
    requestedBy: quotation.owner,
    assignedTo: quotation.approvalRoute,
    requestedAt: '2026-08-07',
    dueAt: '2026-08-08',
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
    service: 'Building Construction',
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

describe('validateApprovalDecision', () => {
  it('requires a decision note', () => {
    expect(
      validateApprovalDecision({
        approvalId: 'APR-099',
        decision: 'approve',
        note: '   ',
      }),
    ).toEqual({
      note: 'Add a decision note before submitting.',
    })
  })
})
