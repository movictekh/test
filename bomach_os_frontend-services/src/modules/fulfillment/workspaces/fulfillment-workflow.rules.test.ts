import { describe, expect, it } from 'vitest'

import { advanceMilestones, clampProgress, nextTaskStatus } from './fulfillment-workflow.rules'

describe('fulfillment workflow rules', () => {
  it('clamps progress into the prototype range', () => {
    expect(clampProgress(-10)).toBe(0)
    expect(clampProgress(47.4)).toBe(47)
    expect(clampProgress(140)).toBe(100)
  })

  it('advances the active milestone and activates the next one', () => {
    const result = advanceMilestones([
      { id: 'M1', name: 'Discovery', status: 'Done' },
      { id: 'M2', name: 'Requirements', status: 'Active' },
      { id: 'M3', name: 'Design', status: 'Pending' },
    ])

    expect(result.milestones.map((item) => item.status)).toEqual(['Done', 'Done', 'Active'])
    expect(result.stage).toBe('Design')
    expect(result.completed).toBe(false)
  })

  it('completes an order when its last active milestone advances', () => {
    const result = advanceMilestones([
      { id: 'M1', name: 'Pickup', status: 'Done' },
      { id: 'M2', name: 'Delivery', status: 'Active' },
    ])

    expect(result.progress).toBe(100)
    expect(result.stage).toBe('Completed')
    expect(result.completed).toBe(true)
  })

  it('moves tasks through the exact prototype columns', () => {
    expect(nextTaskStatus('To Do')).toBe('In Progress')
    expect(nextTaskStatus('In Progress')).toBe('Review')
    expect(nextTaskStatus('Review')).toBe('Done')
    expect(nextTaskStatus('Done')).toBe('Done')
  })
})
