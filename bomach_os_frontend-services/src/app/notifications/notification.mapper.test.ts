import { describe, expect, it } from 'vitest'

import { mapNotificationPayload } from './notification.mapper'

describe('notification transport mapper', () => {
  it('maps a backend envelope without creating business notifications locally', () => {
    expect(
      mapNotificationPayload({
        results: [
          {
            id: 'N1',
            title: 'Deliverable awaiting review',
            message: 'DEL-701 requires review',
            created_at: '2026-08-07T11:00:00Z',
            is_read: false,
            severity: 'warning',
            entity_type: 'deliverable',
            entity_id: 'DEL-701',
          },
        ],
      }),
    ).toEqual([
      {
        id: 'N1',
        title: 'Deliverable awaiting review',
        description: 'DEL-701 requires review',
        timestamp: '2026-08-07T11:00:00Z',
        read: false,
        tone: 'warning',
        entityType: 'deliverable',
        entityId: 'DEL-701',
      },
    ])
  })
})
