import { describe, expect, it } from 'vitest'

import {
  validateOrderActivity,
  validateOrderCreation,
  validateOrderMilestone,
} from './service-order.validation'

describe('service order validation', () => {
  it('requires a next action during mobilisation', () => {
    expect(validateOrderCreation({ nextAction: '' })).toBeTruthy()
    expect(validateOrderCreation({ nextAction: 'Confirm team' })).toBe('')
  })

  it('requires activity note and milestone name', () => {
    expect(
      validateOrderActivity({ activityType: 'progress_update', visibility: 'internal', note: '' }),
    ).toBeTruthy()
    expect(validateOrderMilestone({ name: '' })).toBeTruthy()
  })
})
