import { describe, expect, it } from 'vitest'

import {
  advanceMilestones,
  canCompleteTask,
  clampProgress,
  nextTaskStatus,
  taskProgressForStatus,
  commercialSourceAlreadyOrdered,
  canCompleteOrderWithDeliverables,
} from './fulfillment-workflow.rules'

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

  it('requires evidence before completion when configured', () => {
    expect(canCompleteTask({ evidenceRequired: true, evidenceCount: 0 })).toBe(false)
    expect(canCompleteTask({ evidenceRequired: true, evidenceCount: 1 })).toBe(true)
    expect(canCompleteTask({ evidenceRequired: false, evidenceCount: 0 })).toBe(true)
  })

  it('keeps task progress aligned with workflow state', () => {
    expect(taskProgressForStatus('In Progress', 5)).toBe(25)
    expect(taskProgressForStatus('Review', 45)).toBe(80)
    expect(taskProgressForStatus('Done', 80)).toBe(100)
  })
  it('detects an existing commercial source order by exact linked IDs', () => {
    const orders = [{ requestId: 'REQ-1', quotationId: 'Q-1', invoiceId: 'INV-1' }]
    expect(
      commercialSourceAlreadyOrdered(orders, {
        requestId: 'REQ-1',
        quotationId: 'Q-1',
        invoiceId: 'INV-1',
      }),
    ).toBe(true)
    expect(
      commercialSourceAlreadyOrdered(orders, {
        requestId: 'REQ-2',
        quotationId: 'Q-2',
        invoiceId: 'INV-2',
      }),
    ).toBe(false)
  })

  it('prevents duplicate fulfillment when a canonical source ID is reused', () => {
    const orders = [{ requestId: 'REQ-10', quotationId: 'Q-10', invoiceId: 'INV-10' }]
    expect(
      commercialSourceAlreadyOrdered(orders, {
        requestId: 'REQ-99',
        quotationId: 'Q-99',
        invoiceId: 'INV-10',
      }),
    ).toBe(true)
    expect(
      commercialSourceAlreadyOrdered(orders, {
        requestId: 'REQ-99',
        quotationId: 'Q-10',
        invoiceId: 'INV-99',
      }),
    ).toBe(true)
  })
  it('blocks order completion while a governed deliverable is pending', () => {
    expect(
      canCompleteOrderWithDeliverables(
        [{ orderId: 'ORD-1', approvalMode: 'Supervisor approval', status: 'Under Review' }],
        'ORD-1',
      ),
    ).toBe(false)
    expect(
      canCompleteOrderWithDeliverables(
        [{ orderId: 'ORD-1', approvalMode: 'Supervisor approval', status: 'Approved' }],
        'ORD-1',
      ),
    ).toBe(true)
  })
})
