import { describe, expect, it } from 'vitest'

import { getRecordDestination } from './record-links'

describe('record deep links', () => {
  it('maps core business entities to an exact route and record search param', () => {
    expect(getRecordDestination('request', 'REQ-1')).toEqual({
      section: 'service-requests',
      search: { request: 'REQ-1' },
    })
    expect(getRecordDestination('order', 'ORD-1')).toEqual({
      section: 'service-orders',
      search: { order: 'ORD-1' },
    })
    expect(getRecordDestination('deliverable', 'DEL-1')).toEqual({
      section: 'deliverables',
      search: { deliverable: 'DEL-1' },
    })
    expect(getRecordDestination('feedback', 'FDB-1')).toEqual({
      section: 'feedback-quality',
      search: { feedback: 'FDB-1' },
    })
  })

  it('does not manufacture a route for an unsupported entity type', () => {
    expect(getRecordDestination('unknown', '1')).toBeNull()
  })
})
