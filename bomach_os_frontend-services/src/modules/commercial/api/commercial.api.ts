import { apiClient } from '@/shared/api/api-client'

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
    return apiClient.get<CommercialWorkspace>('/ui-prototype/commercial')
  },

  createRequest(input: CreateServiceRequestInput) {
    return apiClient.post<CommercialWorkspace>('/ui-prototype/commercial/requests', input)
  },

  createQuotation(input: CreateQuotationInput) {
    return apiClient.post<CommercialWorkspace>('/ui-prototype/commercial/quotations', input)
  },

  updateQuotation(quotationId: string, input: UpdateQuotationInput) {
    return apiClient.patch<CommercialWorkspace>(
      `/ui-prototype/commercial/quotations/${quotationId}`,
      input,
    )
  },

  createInvoice(input: CreateInvoiceInput) {
    return apiClient.post<CommercialWorkspace>('/ui-prototype/commercial/invoices', input)
  },

  recordPayment(input: RecordPaymentInput) {
    return apiClient.post<CommercialWorkspace>(
      `/ui-prototype/commercial/invoices/${input.invoiceId}/payments`,
      input,
    )
  },

  decideApproval(input: DecideApprovalInput) {
    return apiClient.patch<CommercialWorkspace>(
      `/ui-prototype/commercial/approvals/${input.approvalId}`,
      input,
    )
  },

  updateRequest(requestId: string, input: UpdateServiceRequestInput) {
    return apiClient.patch<CommercialWorkspace>(
      `/ui-prototype/commercial/requests/${requestId}`,
      input,
    )
  },
}
