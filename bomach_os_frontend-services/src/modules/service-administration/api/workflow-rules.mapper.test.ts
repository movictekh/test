import { describe, expect, it } from 'vitest'

import { mapWorkflowRule, mapWorkflowRules } from './workflow-rules.mapper'

describe('workflow rules mapper', () => {
  it('maps the paginated backend list envelope', () => {
    expect(
      mapWorkflowRules({
        count: 1,
        items: [
          {
            id: 4,
            name: 'Order completed',
            description: 'Notify operations',
            trigger_event: 'service_order_status_changed',
            conditions: [{ field: 'order_status', operator: 'eq', value: 'completed' }],
            action_type: 'send_notification',
            action_config: { recipient_ids: [12] },
            is_active: true,
            created_by_name: 'Admin',
            execution_count: 3,
            created_at: '2026-08-09T08:00:00Z',
          },
        ],
      }),
    ).toEqual([
      expect.objectContaining({
        id: 4,
        triggerEvent: 'service_order_status_changed',
        executionCount: 3,
        active: true,
      }),
    ])
  })

  it('maps a create/update response object', () => {
    expect(
      mapWorkflowRule({
        id: 8,
        name: 'Quote sent',
        description: '',
        trigger_event: 'quote_status_changed',
        conditions: [{ field: 'status', operator: 'eq', value: 'sent' }],
        action_type: 'send_notification',
        action_config: { recipient_ids: [12] },
        is_active: true,
        created_by_name: 'Admin',
        created_at: '2026-08-09T08:00:00Z',
      }),
    ).toEqual(
      expect.objectContaining({
        id: 8,
        triggerEvent: 'quote_status_changed',
        active: true,
      }),
    )
  })
})
