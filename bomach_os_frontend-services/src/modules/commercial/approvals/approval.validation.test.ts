import { describe, expect, it } from 'vitest'
import { validateApprovalDecision, validateApprovalRequest } from './approval.validation'

describe('approval validation', () => {
  it('requires flow, title and description', () => {
    const errors = validateApprovalRequest({ flowId: 0, title: '', description: '' })
    expect(errors.flowId).toBeTruthy()
    expect(errors.title).toBeTruthy()
    expect(errors.description).toBeTruthy()
  })

  it('requires rejection reason but permits approval without comment', () => {
    expect(validateApprovalDecision('reject', '')).toBeTruthy()
    expect(validateApprovalDecision('approve', '')).toBe('')
  })
})
