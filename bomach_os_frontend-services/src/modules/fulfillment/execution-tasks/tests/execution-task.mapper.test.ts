import { describe, expect, it } from 'vitest'

import { mapExecutionTask, mapExecutionTaskList } from '../execution-task.mapper'

describe('execution task mapper', () => {
  it('maps the ServiceExecutionTaskOut contract into frontend shape', () => {
    expect(
      mapExecutionTask({
        id: 42,
        task_number: 'TSK-ABC123',
        order_id: 7,
        milestone_id: 3,
        title: 'Capture coordinates',
        description: 'Capture all field coordinates.',
        instructions: 'Use the approved control points.',
        acceptance_criteria: 'Coordinates validated.',
        status: 'in_progress',
        priority: 'high',
        evidence_required: true,
        owner_id: 9,
        assignee_ids: [10, 11],
        due_date: '2026-08-18',
        completed_at: null,
        created_by_id: 1,
        created_at: '2026-08-11T10:00:00Z',
        updated_at: '2026-08-11T11:00:00Z',
      }),
    ).toEqual({
      id: 42,
      taskNumber: 'TSK-ABC123',
      orderId: 7,
      milestoneId: 3,
      title: 'Capture coordinates',
      description: 'Capture all field coordinates.',
      instructions: 'Use the approved control points.',
      acceptanceCriteria: 'Coordinates validated.',
      status: 'in_progress',
      priority: 'high',
      evidenceRequired: true,
      ownerId: 9,
      assigneeIds: [10, 11],
      dueDate: '2026-08-18',
      completedAt: null,
      createdById: 1,
      createdAt: '2026-08-11T10:00:00Z',
      updatedAt: '2026-08-11T11:00:00Z',
    })
  })

  it('maps Ninja pagination responses', () => {
    const result = mapExecutionTaskList({
      count: 1,
      items: [
        {
          id: 1,
          task_number: 'TSK-1',
          order_id: 2,
          title: 'Task',
          status: 'to_do',
          priority: 'normal',
          evidence_required: false,
          assignee_ids: [],
          created_by_id: 1,
        },
      ],
    })

    expect(result.count).toBe(1)
    expect(result.items).toHaveLength(1)
    expect(result.items[0]?.taskNumber).toBe('TSK-1')
  })
})
