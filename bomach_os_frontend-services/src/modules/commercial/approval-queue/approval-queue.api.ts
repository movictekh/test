import { apiClient } from '@/shared/api/api-client'

import {
  mapApprovalQueueChoices,
  mapApprovalQueuePage,
  mapApprovalQueueStats,
} from './approval-queue.mapper'
import type { ApprovalQueueFilters, ApprovalQueueItem } from './approval-queue.types'

const ROOT = '/approvals/queue'
const API_PREFIX = '/api/v1'

function queueQuery(filters: ApprovalQueueFilters) {
  const query = new URLSearchParams()
  const limit = filters.limit ?? 10
  const page = filters.page ?? 1

  query.set('limit', String(limit))
  query.set('offset', String((page - 1) * limit))

  if (filters.status) query.set('status', filters.status)
  if (filters.search) query.set('search', filters.search)
  if (filters.source) query.set('source', filters.source)
  if (filters.highValue) query.set('high_value', 'true')

  return query.toString()
}

export function normalizeApprovalActionPath(url: string) {
  if (!url.startsWith(`${API_PREFIX}/`)) {
    throw new Error('This approval action is not available.')
  }

  const path = url.slice(API_PREFIX.length)

  if (
    !path.startsWith('/quotes/') &&
    !path.startsWith('/orders/') &&
    !path.startsWith('/expenses/')
  ) {
    throw new Error('This approval action is not available.')
  }

  return path
}

export const approvalQueueApi = {
  async list(filters: ApprovalQueueFilters) {
    return mapApprovalQueuePage(await apiClient.get<unknown>(`${ROOT}/?${queueQuery(filters)}`))
  },

  async stats() {
    return mapApprovalQueueStats(await apiClient.get<unknown>(`${ROOT}/stats`))
  },

  async choices() {
    return mapApprovalQueueChoices(await apiClient.get<unknown>(`${ROOT}/choices`))
  },

  async approve(item: ApprovalQueueItem) {
    if (!item.approveUrl) throw new Error('This item cannot be approved.')
    return apiClient.post<unknown>(normalizeApprovalActionPath(item.approveUrl))
  },

  async reject(item: ApprovalQueueItem, reason: string) {
    if (!item.rejectUrl) throw new Error('This item cannot be rejected.')

    const path = normalizeApprovalActionPath(item.rejectUrl)

    if (item.source === 'deliverable') {
      return apiClient.post<unknown>(path, { reason })
    }

    return apiClient.post<unknown>(path)
  },
}
