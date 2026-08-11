import { describe, expect, it } from 'vitest'

import {
  validateExecutionTaskCreate,
  validateExecutionTaskUpdate,
} from '../execution-task.validation'

describe('execution task validation', () => {
  it('requires a task title on create', () => {
    expect(validateExecutionTaskCreate({ title: '   ' })).toBe('Task title is required.')
  })

  it('accepts a valid create payload', () => {
    expect(
      validateExecutionTaskCreate({
        title: 'Validate field observations',
        priority: 'high',
        evidenceRequired: true,
      }),
    ).toBe('')
  })

  it('rejects a blank title when title is included in an update', () => {
    expect(validateExecutionTaskUpdate({ title: '' })).toBe('Task title is required.')
  })

  it('allows metadata-only updates without title', () => {
    expect(validateExecutionTaskUpdate({ priority: 'critical' })).toBe('')
  })
})
