import { apiClient } from '@/shared/api/api-client'

import { mapQuotation, mapQuotationList, mapRoles } from './quotation.mapper'
import type {
  ClientQuotationDecision,
  CreateQuotationInput,
  QuotationFilters,
  QuotationSummary,
  UpdateQuotationInput,
} from './quotation.types'

function queryString(filters: QuotationFilters = {}) {
  const q = new URLSearchParams()
  const limit = filters.limit ?? 10
  const page = filters.page ?? 1
  q.set('limit', String(limit))
  q.set('offset', String((page - 1) * limit))
  if (filters.search) q.set('search', filters.search)
  if (filters.status) q.set('status', filters.status)
  return q.toString()
}

async function count(status?: string) {
  return mapQuotationList(
    await apiClient.get<unknown>(
      `/quotes?${queryString({ ...(status ? { status } : {}), page: 1, limit: 1 })}`,
    ),
  ).count
}

export const quotationsApi = {
  async list(filters: QuotationFilters = {}) {
    return mapQuotationList(await apiClient.get<unknown>(`/quotes?${queryString(filters)}`))
  },

  async detail(quoteId: number) {
    return mapQuotation(await apiClient.get<unknown>(`/quotes/${quoteId}`))
  },

  async summary(): Promise<QuotationSummary> {
    const [total, awaitingApproval, sent, accepted, rejected, expired] = await Promise.all([
      count(),
      count('awaiting_approval'),
      count('sent'),
      count('accepted'),
      count('rejected'),
      count('expired'),
    ])
    const decided = accepted + rejected
    return {
      total,
      awaitingApproval,
      sent,
      accepted,
      rejectedOrExpired: rejected + expired,
      acceptanceRate: decided ? Math.round((accepted / decided) * 100) : 0,
    }
  },

  async roles() {
    return mapRoles(await apiClient.get<unknown>('/roles'))
  },

  async create(input: CreateQuotationInput) {
    return mapQuotation(
      await apiClient.post<unknown>('/quotes', {
        client_id: input.clientId,
        service_id: input.serviceId,
        service_request_id: input.serviceRequestId,
        ...(input.previousQuoteId ? { previous_quote_id: input.previousQuoteId } : {}),
        description: input.description,
        scope_summary: input.scopeSummary,
        terms: input.terms,
        service_fee: input.serviceFee,
        other_charges: input.otherCharges,
        discount: input.discount,
        tax_rate: input.taxRate,
        deposit_percent: input.depositPercent,
        valid_until: input.validUntil,
        required_approver_role_id: input.requiredApproverRoleId,
      }),
    )
  },

  async update(quoteId: number, input: UpdateQuotationInput) {
    return mapQuotation(
      await apiClient.patch<unknown>(`/quotes/${quoteId}`, {
        description: input.description,
        scope_summary: input.scopeSummary,
        terms: input.terms,
        service_fee: input.serviceFee,
        other_charges: input.otherCharges,
        discount: input.discount,
        tax_rate: input.taxRate,
        deposit_percent: input.depositPercent,
        valid_until: input.validUntil,
        required_approver_role_id: input.requiredApproverRoleId,
      }),
    )
  },

  async approve(quoteId: number) {
    return mapQuotation(await apiClient.post<unknown>(`/quotes/${quoteId}/approve`, {}))
  },

  async clientDecision(quoteId: number, input: ClientQuotationDecision) {
    return mapQuotation(
      await apiClient.post<unknown>(
        input.decision === 'accepted'
          ? `/service-requests/quotes/${quoteId}/accept`
          : `/service-requests/quotes/${quoteId}/reject`,
        input.decision === 'accepted' ? {} : { reason: input.reason },
      ),
    )
  },
}
