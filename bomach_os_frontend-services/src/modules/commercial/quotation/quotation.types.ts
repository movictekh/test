export type QuotationStatus =
  'draft' | 'awaiting_approval' | 'sent' | 'accepted' | 'rejected' | 'expired'

export interface Quotation {
  id: number
  quoteNumber: string
  clientId: number
  clientName: string
  serviceId: number
  serviceName: string
  serviceRequestId: number | null
  serviceRequestNumber: string
  previousQuoteId: number | null
  previousQuoteNumber: string
  version: number
  requiredApproverRoleId: number | null
  requiredApproverRoleName: string
  description: string
  scopeSummary: string
  terms: string
  serviceFee: number
  otherCharges: number
  discount: number
  subtotal: number
  taxRate: number
  taxAmount: number
  depositPercent: number
  depositAmount: number
  amount: number
  validUntil: string
  status: QuotationStatus
  statusDisplay: string
  approvedById: number | null
  approvedByName: string
  approvedAt: string | null
  sentAt: string | null
  clientRespondedAt: string | null
  clientRejectionReason: string
  createdById: number | null
  createdByName: string
  createdAt: string
  updatedAt: string
}

export interface PaginatedQuotations {
  count: number
  items: Quotation[]
}

export interface QuotationFilters {
  search?: string
  status?: string
  page?: number
  limit?: number
}

export interface QuotationSummary {
  total: number
  awaitingApproval: number
  sent: number
  accepted: number
  rejectedOrExpired: number
  acceptanceRate: number
}

export interface RoleOption {
  id: number
  name: string
}

export interface CreateQuotationInput {
  clientId: number
  serviceId: number
  serviceRequestId: number
  description: string
  scopeSummary: string
  terms: string
  serviceFee: number
  otherCharges: number
  discount: number
  taxRate: number
  depositPercent: number
  validUntil: string
  requiredApproverRoleId: number
  previousQuoteId?: number
}

export type UpdateQuotationInput = Omit<
  CreateQuotationInput,
  'clientId' | 'serviceId' | 'serviceRequestId' | 'previousQuoteId'
>

export type ClientQuotationDecision =
  { decision: 'accepted' } | { decision: 'rejected'; reason: string }
