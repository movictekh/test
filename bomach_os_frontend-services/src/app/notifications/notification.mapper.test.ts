import { describe, expect, it } from 'vitest'

import { mapNotificationList } from './notification.mapper'

describe('notification transport mapper', () => {
  it('maps a backend notification list into app notifications', () => {
    expect(
      mapNotificationList({
        count: 1,
        next: null,
        previous: null,
        results: [
          {
            id: 1,
            title: 'Deliverable awaiting review',
            message: 'DEL-701 requires review',
            created_at: '2026-08-07T11:00:00Z',
            is_read: false,
            notification_type: 'warning',
            link: '',
            metadata: {
              entity_type: 'deliverable',
              entity_id: 'DEL-701',
            },
          },
        ],
      }),
    ).toEqual({
      count: 1,
      next: null,
      previous: null,
      notifications: [
        {
          id: '1',
          title: 'Deliverable awaiting review',
          description: 'DEL-701 requires review',
          timestamp: '2026-08-07T11:00:00Z',
          read: false,
          tone: 'warning',
          metadata: {
            entity_type: 'deliverable',
            entity_id: 'DEL-701',
          },
        },
      ],
    })
  })
})
