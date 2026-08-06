import { describe, expect, it } from 'vitest'
import type { CommercialServiceRequest } from '../types/commercial.types'
import {
  getQuotationEligibleRequests,
  quotationActionAllowed,
  validateQuotationDraft,
} from './quotation-workflow.rules'

const makeRequest = (status: CommercialServiceRequest['status']): CommercialServiceRequest => ({
  id: status,
  client: 'Client',
  clientType: 'Individual',
  phone: '08000000000',
  email: '',
  service: 'Service',
  division: 'Division',
  branch: 'Enugu',
  source: 'Walk-in',
  status,
  priority: 'Medium',
  budget: 1000,
  estimate: 1000,
  owner: 'Owner',
  createdAt: '2026-08-06',
  dueAt: '2026-08-20',
  details: 'Scope',
  nextAction: 'Next',
  intakeResponses: {},
  activities: [],
})

describe('quotation completion rules', () => {
  it('allows only quotation-ready requests', () => {
    const statuses: CommercialServiceRequest['status'][] = [
      'New',
      'Under Review',
      'Site Assessment',
      'Awaiting Quotation',
      'Quoted',
      'Converted',
      'Rejected',
      'Closed',
    ]
    expect(
      getQuotationEligibleRequests(statuses.map(makeRequest)).map((item) => item.status),
    ).toEqual(['Under Review', 'Site Assessment', 'Awaiting Quotation', 'Quoted'])
  })

  it('blocks invalid quotation values', () => {
    const errors = validateQuotationDraft({
      requestId: '',
      validUntil: '',
      scopeSummary: '',
      serviceFee: 0,
      otherCharges: -1,
      discount: 500,
      taxPercent: 101,
      depositPercent: -1,
      approvalRoute: '',
      paymentTerms: '',
    })
    expect(Object.keys(errors).length).toBeGreaterThan(0)
  })

  it('enforces separate approval and send states', () => {
    expect(quotationActionAllowed('Draft', 'submit-approval')).toBe(true)
    expect(quotationActionAllowed('Awaiting Approval', 'approve')).toBe(true)
    expect(quotationActionAllowed('Approved', 'send')).toBe(true)
    expect(quotationActionAllowed('Sent', 'accept')).toBe(true)
    expect(quotationActionAllowed('Draft', 'send')).toBe(false)
  })
})
