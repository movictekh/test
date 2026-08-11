import { describe, expect, it } from 'vitest'

import { mapDeliverable, mapDeliverableList } from '../deliverable.mapper'

describe('deliverable mapper', () => {
  it('maps ServiceDeliverableOut into frontend shape', () => {
    expect(
      mapDeliverable({
        id: 11,
        deliverable_number: 'DEL-ABC123',
        order_id: 4,
        milestone_id: 7,
        task_id: 9,
        title: 'Boundary Survey Report',
        deliverable_type: 'report',
        version: 'v2',
        file_url: 'https://files.example.com/report.pdf',
        file_name: 'boundary-report.pdf',
        content_type: 'application/pdf',
        file_size_bytes: 2048,
        description: 'Signed boundary survey report.',
        client_visible: true,
        status: 'under_review',
        approval_mode: 'client',
        owner_id: 3,
        approved_by_id: null,
        approved_at: null,
        rejected_by_id: null,
        rejected_at: null,
        rejection_reason: '',
        created_by_id: 1,
        created_at: '2026-08-11T10:00:00Z',
        updated_at: '2026-08-11T11:00:00Z',
      }),
    ).toEqual({
      id: 11,
      deliverableNumber: 'DEL-ABC123',
      orderId: 4,
      milestoneId: 7,
      taskId: 9,
      title: 'Boundary Survey Report',
      deliverableType: 'report',
      version: 'v2',
      fileUrl: 'https://files.example.com/report.pdf',
      fileName: 'boundary-report.pdf',
      contentType: 'application/pdf',
      fileSizeBytes: 2048,
      description: 'Signed boundary survey report.',
      clientVisible: true,
      status: 'under_review',
      approvalMode: 'client',
      ownerId: 3,
      approvedById: null,
      approvedAt: null,
      rejectedById: null,
      rejectedAt: null,
      rejectionReason: '',
      createdById: 1,
      createdAt: '2026-08-11T10:00:00Z',
      updatedAt: '2026-08-11T11:00:00Z',
    })
  })

  it('maps paginated list responses', () => {
    const result = mapDeliverableList({
      count: 1,
      items: [
        {
          id: 1,
          deliverable_number: 'DEL-1',
          order_id: 2,
          title: 'Drawing',
          deliverable_type: 'drawing',
          version: 'v1',
          file_url: 'https://files.example.com/drawing.pdf',
          client_visible: false,
          status: 'approved',
          approval_mode: 'none',
          created_by_id: 1,
        },
      ],
    })

    expect(result.count).toBe(1)
    expect(result.items).toHaveLength(1)
    expect(result.items[0]?.deliverableNumber).toBe('DEL-1')
  })
})
