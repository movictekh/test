import { describe, expect, it } from 'vitest'

import { mapEmployeeOptions, mapServiceOrder, mapServiceOrderList } from './service-order.mapper'

describe('service order mapper', () => {
  it('maps order detail, milestones, activities and counts', () => {
    const order = mapServiceOrder({
      id: 7,
      order_number: 'ORD-7',
      client_id: 3,
      service: { id: 2, name: 'Boundary Survey' },
      quote: { id: 4, quote_number: 'QTE-4' },
      service_request_id: 5,
      invoice_id: 6,
      description: 'Mobilised survey',
      amount: '650000.00',
      order_status: 'active',
      payment_status: 'partial',
      valid_until: '2026-09-30',
      due_date: '2026-09-20',
      progress: 33,
      stage: 'Field Survey',
      next_action: 'Complete field work',
      created_at: '2026-08-10T10:00:00Z',
      updated_at: '2026-08-10T11:00:00Z',
      created_by_id: 1,
      assigned_to_id: 9,
      branch_id: 2,
      task_counts: { to_do: 2, in_progress: 1 },
      deliverable_counts: { under_review: 1, approved: 2 },
      milestones: [
        {
          id: 1,
          name: 'Field Survey',
          status: 'active',
          sort_order: 1,
          client_visible: true,
          created_at: '',
          updated_at: '',
        },
      ],
      activities: [
        {
          id: 1,
          activity_type: 'order_created',
          visibility: 'internal_client',
          note: 'Order created',
          created_at: '2026-08-10T10:00:00Z',
        },
      ],
    })

    expect(order.orderNumber).toBe('ORD-7')
    expect(order.amount).toBe(650000)
    expect(order.taskCounts.in_progress).toBe(1)
    expect(order.deliverableCounts.approved).toBe(2)
    expect(order.milestones[0]?.status).toBe('active')
  })

  it('maps limit-offset list shape', () => {
    const page = mapServiceOrderList({
      count: 1,
      items: [
        {
          id: 1,
          order_number: 'ORD-1',
          client_id: 1,
          service: { id: 2, name: 'Survey' },
          amount: '10',
          order_status: 'pending_mobilisation',
          payment_status: 'partial',
          valid_until: '2026-09-01',
          progress: 0,
          created_by_id: 1,
        },
      ],
    })
    expect(page.count).toBe(1)
    expect(page.items[0]?.serviceName).toBe('Survey')
  })

  it('maps employee lookup display names', () => {
    const employees = mapEmployeeOptions({
      count: 1,
      items: [
        {
          id: 9,
          user_id: 4,
          first_name: 'Ada',
          last_name: 'Okoro',
          employee_id: 'EMP-9',
          designation: 'Surveyor',
          branch_name: 'Enugu',
          is_active: true,
        },
      ],
    })
    expect(employees[0]?.name).toBe('Ada Okoro')
    expect(employees[0]?.id).toBe(9)
  })
})
