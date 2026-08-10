import { describe, expect, it } from 'vitest'
import { mapApprovalRequest } from './approval.mapper'

describe('approval mapper', () => {
  it('maps multi-step request and decision history', () => {
    const request = mapApprovalRequest({
      id: 9,
      approval_request_id: 'APR-ABC',
      flow_id: 2,
      flow_name: 'Contract Approval',
      action_type: 'contract',
      action_type_display: 'Contract / Client Proposal',
      title: 'Approve proposal',
      description: 'Review commercial proposal',
      status: 'pending',
      status_display: 'Pending',
      current_step: 2,
      total_steps: 3,
      pending_step_name: 'Finance Review',
      pending_step_required_level: 'head_finance',
      pending_step_required_level_display: 'Head of Finance',
      decisions: [
        {
          id: 1,
          step_order: 1,
          step_name: 'Commercial Review',
          decision: 'approved',
          decision_display: 'Approved',
          comment: 'Scope confirmed',
          approver_id: 4,
          approver_name: 'Reviewer',
          created_at: '2026-08-10T09:00:00Z',
        },
      ],
      metadata: { reference: 'QTE-1' },
      created_by_id: 8,
      created_by_name: 'Requester',
      created_at: '2026-08-10T08:00:00Z',
      updated_at: '2026-08-10T09:00:00Z',
    })
    expect(request.currentStep).toBe(2)
    expect(request.totalSteps).toBe(3)
    expect(request.pendingStepRequiredLevelDisplay).toBe('Head of Finance')
    expect(request.decisions[0]?.decision).toBe('approved')
  })
})
