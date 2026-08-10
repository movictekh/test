import { describe, expect, it } from 'vitest'

import { mapApprovalQueuePage, mapApprovalQueueStats } from './approval-queue.mapper'

describe('approval queue mapper', () => {
  it('maps normalized operational approval items', () => {
    const page = mapApprovalQueuePage({
      count: 1,
      results: [
        {
          id: 'quotation-7',
          source: 'quotation',
          source_display: 'Quotation',
          ref_number: 'QTE-7',
          subject: 'Building quotation',
          requester_name: 'Operations Lead',
          approver_name: 'CEO',
          amount: '165000000.00',
          created_at: '2026-08-10T10:00:00Z',
          status: 'pending',
          action_label: 'Approve & Send',
          approve_url: '/api/v1/quotes/7/approve',
          reject_url: null,
        },
      ],
    })

    expect(page.count).toBe(1)
    expect(page.items[0]?.source).toBe('quotation')
    expect(page.items[0]?.amount).toBe(165000000)
    expect(page.items[0]?.approveUrl).toBe('/api/v1/quotes/7/approve')
    expect(page.items[0]?.rejectUrl).toBeNull()
  })

  it('maps queue KPI statistics', () => {
    expect(
      mapApprovalQueueStats({
        pending_count: 4,
        high_value_count: 2,
        oldest_waiting_days: 3,
        sla_percent: '87.50',
      }),
    ).toEqual({
      pendingCount: 4,
      highValueCount: 2,
      oldestWaitingDays: 3,
      slaPercent: 87.5,
    })
  })
})
