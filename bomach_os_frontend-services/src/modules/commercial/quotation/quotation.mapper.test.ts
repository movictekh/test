import { describe, expect, it } from 'vitest'
import { mapQuotation } from './quotation.mapper'

describe('quotation mapper', () => {
  it('maps backend decimals, ids and statuses', () => {
    const q = mapQuotation({
      id: 4,
      quote_number: 'QTE-ABC',
      client_id: 2,
      client_name: 'Acme',
      service_id: 3,
      service_name: 'Survey',
      service_request_id: 9,
      service_request_number: 'REQ-001',
      required_approver_role_id: 7,
      required_approver_role_name: 'Commercial Manager',
      service_fee: '100000.00',
      amount: '107500.00',
      status: 'awaiting_approval',
      created_at: '2026-08-09T10:00:00Z',
      updated_at: '2026-08-09T10:00:00Z',
    })
    expect(q.quoteNumber).toBe('QTE-ABC')
    expect(q.amount).toBe(107500)
    expect(q.status).toBe('awaiting_approval')
    expect(q.requiredApproverRoleId).toBe(7)
  })
})
