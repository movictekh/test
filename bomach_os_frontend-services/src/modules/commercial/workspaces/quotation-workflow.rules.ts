import type {
  CommercialServiceRequest,
  CreateQuotationInput,
  QuotationStatus,
} from '../types/commercial.types'

const eligibleStatuses = new Set<CommercialServiceRequest['status']>([
  'Under Review',
  'Site Assessment',
  'Awaiting Quotation',
  'Quoted',
])

export function getQuotationEligibleRequests(
  requests: CommercialServiceRequest[],
): CommercialServiceRequest[] {
  return requests.filter((request) => eligibleStatuses.has(request.status))
}

export type QuotationDraft = Omit<CreateQuotationInput, 'status'>

export function validateQuotationDraft(value: QuotationDraft) {
  const errors: Partial<Record<keyof QuotationDraft, string>> = {}
  const subtotal = Number(value.serviceFee) + Number(value.otherCharges)

  if (!value.requestId) errors.requestId = 'Select an eligible request'
  if (!value.validUntil) errors.validUntil = 'Validity date is required'
  if (!value.scopeSummary.trim()) errors.scopeSummary = 'Scope is required'
  if (!Number.isFinite(value.serviceFee) || value.serviceFee <= 0) {
    errors.serviceFee = 'Service fee must be greater than zero'
  }
  if (!Number.isFinite(value.otherCharges) || value.otherCharges < 0) {
    errors.otherCharges = 'Other charges cannot be negative'
  }
  if (!Number.isFinite(value.discount) || value.discount < 0) {
    errors.discount = 'Discount cannot be negative'
  } else if (value.discount > subtotal) {
    errors.discount = 'Discount cannot exceed subtotal'
  }
  if (value.taxPercent < 0 || value.taxPercent > 100) {
    errors.taxPercent = 'Tax must be between 0 and 100'
  }
  if (value.depositPercent < 0 || value.depositPercent > 100) {
    errors.depositPercent = 'Deposit must be between 0 and 100'
  }
  if (!value.approvalRoute.trim()) errors.approvalRoute = 'Approval route is required'
  if (!value.paymentTerms.trim()) errors.paymentTerms = 'Payment terms are required'

  return errors
}

export function quotationActionAllowed(
  status: QuotationStatus,
  action: 'submit-approval' | 'approve' | 'send' | 'accept' | 'reject' | 'revise',
): boolean {
  const transitions: Record<typeof action, QuotationStatus[]> = {
    'submit-approval': ['Draft'],
    approve: ['Awaiting Approval'],
    send: ['Approved'],
    accept: ['Sent'],
    reject: ['Sent'],
    revise: ['Draft', 'Rejected'],
  }
  return transitions[action].includes(status)
}
