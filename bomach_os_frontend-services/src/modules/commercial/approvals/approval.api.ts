import { apiClient } from '@/shared/api/api-client'

import {
  mapApprovalActionTypes,
  mapApprovalFlow,
  mapApprovalFlowList,
  mapApprovalRequest,
  mapApprovalRequestList,
} from './approval.mapper'
import type {
  ApprovalRequestFilters,
  ApprovalSummary,
  CreateApprovalRequestInput,
} from './approval.types'

const ROOT = '/approvals'

function requestQuery(filters: ApprovalRequestFilters = {}) {
  const query = new URLSearchParams()
  const limit = filters.limit ?? 10
  const page = filters.page ?? 1
  query.set('limit', String(limit))
  query.set('offset', String((page - 1) * limit))
  if (filters.search) query.set('search', filters.search)
  if (filters.status) query.set('status', filters.status)
  if (filters.actionType) query.set('action_type', filters.actionType)
  if (filters.myRequests) query.set('my_requests', 'true')
  return query.toString()
}

async function allRequests() {
  const pageSize = 100
  const first = mapApprovalRequestList(
    await apiClient.get<unknown>(
      `${ROOT}/requests?${requestQuery({ page: 1, limit: pageSize })}`,
    ),
  )
  const items = [...first.items]
  const pages = Math.ceil(first.count / pageSize)
  for (let page = 2; page <= pages; page += 1) {
    const next = mapApprovalRequestList(
      await apiClient.get<unknown>(
        `${ROOT}/requests?${requestQuery({ page, limit: pageSize })}`,
      ),
    )
    items.push(...next.items)
  }
  return items
}

export const approvalApi = {
  async listRequests(filters: ApprovalRequestFilters = {}) {
    return mapApprovalRequestList(
      await apiClient.get<unknown>(
        `${ROOT}/requests?${requestQuery(filters)}`,
      ),
    )
  },

  async requestDetail(requestId: number) {
    return mapApprovalRequest(
      await apiClient.get<unknown>(`${ROOT}/requests/${requestId}`),
    )
  },

  async summary(): Promise<ApprovalSummary> {
    const items = await allRequests()
    return {
      pending: items.filter((item) => item.status === 'pending').length,
      approved: items.filter((item) => item.status === 'approved').length,
      rejected: items.filter((item) => item.status === 'rejected').length,
      cancelled: items.filter((item) => item.status === 'cancelled').length,
    }
  },

  async createRequest(input: CreateApprovalRequestInput) {
    return mapApprovalRequest(
      await apiClient.post<unknown>(`${ROOT}/requests`, {
        flow_id: input.flowId,
        title: input.title,
        description: input.description,
        metadata: {},
      }),
    )
  },

  async approve(requestId: number, comment: string) {
    return mapApprovalRequest(
      await apiClient.post<unknown>(
        `${ROOT}/requests/${requestId}/approve`,
        { comment },
      ),
    )
  },

  async reject(requestId: number, comment: string) {
    return mapApprovalRequest(
      await apiClient.post<unknown>(
        `${ROOT}/requests/${requestId}/reject`,
        { comment },
      ),
    )
  },

  async cancel(requestId: number) {
    await apiClient.delete<unknown>(`${ROOT}/requests/${requestId}`)
  },

  async activeFlows() {
    return mapApprovalFlowList(
      await apiClient.get<unknown>(
        `${ROOT}/flows?is_active=true&limit=100&offset=0`,
      ),
    )
  },

  async flowDetail(flowId: number) {
    return mapApprovalFlow(
      await apiClient.get<unknown>(`${ROOT}/flows/${flowId}`),
    )
  },

  async actionTypes() {
    return mapApprovalActionTypes(
      await apiClient.get<unknown>(`${ROOT}/flows/choices`),
    )
  },
}
