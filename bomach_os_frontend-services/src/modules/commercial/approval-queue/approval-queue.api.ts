import { apiClient } from '@/shared/api/api-client'

import {
  mapApprovalQueueChoices,
  mapApprovalQueueItem,
  mapApprovalQueuePage,
  mapApprovalQueueStats,
} from './approval-queue.mapper'
import type { ApprovalQueueFilters, ApprovalQueueItem } from './approval-queue.types'

const ROOT = '/approvals/queue'
const API_PREFIX = '/api/v1'
const STATUS_PAGE_LIMIT = 100

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

async function fetchStatusItems(
  status: NonNullable<ApprovalQueueFilters['status']>,
  filters: Omit<ApprovalQueueFilters, 'status' | 'page' | 'limit'>,
) {
  let offset = 0
  const items: ApprovalQueueItem[] = []

  while (true) {
    const query = new URLSearchParams()
    query.set('status', status)
    query.set('limit', String(STATUS_PAGE_LIMIT))
    query.set('offset', String(offset))

    if (filters.search) query.set('search', filters.search)
    if (filters.source) query.set('source', filters.source)
    if (filters.highValue) query.set('high_value', 'true')

    const response = (await apiClient.get<{
      count?: unknown
      results?: unknown[]
    }>(`${ROOT}/?${query.toString()}`)) ?? { results: [] }

    const batch = Array.isArray(response.results) ? response.results.map(mapApprovalQueueItem) : []
    items.push(...batch)

    if (batch.length < STATUS_PAGE_LIMIT) break
    offset += STATUS_PAGE_LIMIT
  }

  return items
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
    if (!filters.status) {
      const [pendingItems, approvedItems, rejectedItems] = await Promise.all([
        fetchStatusItems('pending', filters),
        fetchStatusItems('approved', filters),
        fetchStatusItems('rejected', filters),
      ])

      const page = filters.page ?? 1
      const limit = filters.limit ?? 10
      const rank = { pending: 0, approved: 1, rejected: 2 } as const

      const items = [...pendingItems, ...approvedItems, ...rejectedItems].sort((left, right) => {
        const byStatus = rank[left.status] - rank[right.status]
        if (byStatus !== 0) return byStatus
        return new Date(right.createdAt).getTime() - new Date(left.createdAt).getTime()
      })

      const offset = (page - 1) * limit
      return {
        count: items.length,
        items: items.slice(offset, offset + limit),
      }
    }

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
