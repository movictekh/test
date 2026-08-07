import { apiClient } from '@/shared/api/api-client'
import { MOCK_API_PREFIX } from '@/mocks/mock-api'

import type {
  CommercialWorkspace,
  DecideApprovalInput,
  RecordPaymentInput,
  CreateInvoiceInput,
  CreateQuotationInput,
  UpdateQuotationInput,
  CreateServiceRequestInput,
  ServiceRequestStatus,
} from '../types/commercial.types'

export interface UpdateServiceRequestInput {
  status?: ServiceRequestStatus
  owner?: string
  nextAction?: string
  dueAt?: string
  estimate?: number
  activity?: {
    at: string
    title: string
    actor: string
    description: string
  }
}

export const commercialApi = {
  getWorkspace() {
    return apiClient.get<CommercialWorkspace>(`${MOCK_API_PREFIX}/commercial`)
  },

  createRequest(input: CreateServiceRequestInput) {
    return apiClient.post<CommercialWorkspace>(`${MOCK_API_PREFIX}/commercial/requests`, input)
  },

  createQuotation(input: CreateQuotationInput) {
    return apiClient.post<CommercialWorkspace>(`${MOCK_API_PREFIX}/commercial/quotations`, input)
  },

  updateQuotation(quotationId: string, input: UpdateQuotationInput) {
    return apiClient.patch<CommercialWorkspace>(
      `${MOCK_API_PREFIX}/commercial/quotations/${quotationId}`,
      input,
    )
  },

  createInvoice(input: CreateInvoiceInput) {
    return apiClient.post<CommercialWorkspace>(`${MOCK_API_PREFIX}/commercial/invoices`, input)
  },

  recordPayment(input: RecordPaymentInput) {
    return apiClient.post<CommercialWorkspace>(
      `${MOCK_API_PREFIX}/commercial/invoices/${input.invoiceId}/payments`,
      input,
    )
  },

  decideApproval(input: DecideApprovalInput) {
    return apiClient.patch<CommercialWorkspace>(
      `${MOCK_API_PREFIX}/commercial/approvals/${input.approvalId}`,
      input,
    )
  },

  updateRequest(requestId: string, input: UpdateServiceRequestInput) {
    return apiClient.patch<CommercialWorkspace>(
      `${MOCK_API_PREFIX}/commercial/requests/${requestId}`,
      input,
    )
  },
}
