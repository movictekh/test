import { apiClient } from '@/shared/api/api-client'

import { mapDeliverable, mapDeliverableList } from './deliverable.mapper'
import type {
  CreateDeliverableInput,
  DeliverableFilters,
  UpdateDeliverableInput,
} from './deliverable.types'

function deliverableQuery(filters: DeliverableFilters = {}) {
  const query = new URLSearchParams()
  const limit = filters.limit ?? 10
  const page = filters.page ?? 1

  query.set('limit', String(limit))
  query.set('offset', String((page - 1) * limit))

  if (filters.status) query.set('status', filters.status)
  if (filters.deliverableType) query.set('deliverable_type', filters.deliverableType)
  if (filters.clientVisible !== undefined)
    query.set('client_visible', String(filters.clientVisible))
  if (filters.milestoneId) query.set('milestone_id', String(filters.milestoneId))
  if (filters.taskId) query.set('task_id', String(filters.taskId))
  if (filters.search) query.set('search', filters.search)

  return query.toString()
}

function createPayload(input: CreateDeliverableInput) {
  return {
    milestone_id: input.milestoneId ?? null,
    task_id: input.taskId ?? null,
    title: input.title,
    deliverable_type: input.deliverableType,
    version: input.version,
    file_url: input.fileUrl,
    file_name: input.fileName ?? '',
    content_type: input.contentType ?? '',
    file_size_bytes: input.fileSizeBytes ?? 0,
    description: input.description ?? '',
    client_visible: input.clientVisible,
    approval_mode: input.approvalMode,
    owner_id: input.ownerId ?? null,
  }
}

function updatePayload(input: UpdateDeliverableInput) {
  return {
    ...(input.milestoneId !== undefined ? { milestone_id: input.milestoneId } : {}),
    ...(input.taskId !== undefined ? { task_id: input.taskId } : {}),
    ...(input.title !== undefined ? { title: input.title } : {}),
    ...(input.deliverableType !== undefined ? { deliverable_type: input.deliverableType } : {}),
    ...(input.version !== undefined ? { version: input.version } : {}),
    ...(input.fileUrl !== undefined ? { file_url: input.fileUrl } : {}),
    ...(input.fileName !== undefined ? { file_name: input.fileName } : {}),
    ...(input.contentType !== undefined ? { content_type: input.contentType } : {}),
    ...(input.fileSizeBytes !== undefined ? { file_size_bytes: input.fileSizeBytes } : {}),
    ...(input.description !== undefined ? { description: input.description } : {}),
    ...(input.clientVisible !== undefined ? { client_visible: input.clientVisible } : {}),
    ...(input.ownerId !== undefined ? { owner_id: input.ownerId } : {}),
  }
}

export const deliverableApi = {
  async list(orderId: number, filters: DeliverableFilters = {}) {
    return mapDeliverableList(
      await apiClient.get<unknown>(`/orders/${orderId}/deliverables?${deliverableQuery(filters)}`),
    )
  },

  async detail(orderId: number, deliverableId: number) {
    return mapDeliverable(
      await apiClient.get<unknown>(`/orders/${orderId}/deliverables/${deliverableId}`),
    )
  },

  async create(orderId: number, input: CreateDeliverableInput) {
    return mapDeliverable(
      await apiClient.post<unknown>(`/orders/${orderId}/deliverables`, createPayload(input)),
    )
  },

  async update(orderId: number, deliverableId: number, input: UpdateDeliverableInput) {
    return mapDeliverable(
      await apiClient.patch<unknown>(
        `/orders/${orderId}/deliverables/${deliverableId}`,
        updatePayload(input),
      ),
    )
  },

  async approve(orderId: number, deliverableId: number) {
    return mapDeliverable(
      await apiClient.post<unknown>(`/orders/${orderId}/deliverables/${deliverableId}/approve`, {}),
    )
  },

  async reject(orderId: number, deliverableId: number, reason: string) {
    return mapDeliverable(
      await apiClient.post<unknown>(`/orders/${orderId}/deliverables/${deliverableId}/reject`, {
        reason,
      }),
    )
  },

  async remove(orderId: number, deliverableId: number) {
    return apiClient.delete<unknown>(`/orders/${orderId}/deliverables/${deliverableId}`)
  },
}
