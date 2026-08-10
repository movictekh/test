import { describe, expect, it } from 'vitest'
import { getApprovalCapabilities } from './approval-capabilities'
import type { ApprovalRequest } from './approval.types'

const make = (overrides: Partial<ApprovalRequest>): ApprovalRequest => ({
  id: 1,
  approvalRequestId: 'APR-1',
  flowId: 1,
  flowName: 'Flow',
  actionType: 'general',
  actionTypeDisplay: 'General',
  title: 'Request',
  description: 'Description',
  status: 'pending',
  statusDisplay: 'Pending',
  currentStep: 1,
  totalSteps: 2,
  pendingStepName: 'Review',
  pendingStepRequiredLevel: 'manager',
  pendingStepRequiredLevelDisplay: 'Manager',
  decisions: [],
  metadata: {},
  createdById: 7,
  createdByName: 'Requester',
  createdAt: '',
  updatedAt: '',
  ...overrides,
})

describe('approval capabilities', () => {
  it('allows creator to cancel pending request', () => {
    expect(getApprovalCapabilities(make({}), 7).cancel).toBe(true)
  })
  it('does not allow non-creator to cancel', () => {
    expect(getApprovalCapabilities(make({}), 8).cancel).toBe(false)
  })
  it('closes decision capability after completion', () => {
    expect(getApprovalCapabilities(make({ status: 'approved' }), 7).decide).toBe(false)
  })
})
