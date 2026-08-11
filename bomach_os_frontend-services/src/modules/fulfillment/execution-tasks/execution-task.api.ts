import { apiClient } from '@/shared/api/api-client'

import { mapExecutionTask, mapExecutionTaskList } from './execution-task.mapper'
import type {
  CreateExecutionTaskInput,
  ExecutionTaskFilters,
  UpdateExecutionTaskInput,
} from './execution-task.types'

function taskQuery(filters: ExecutionTaskFilters = {}) {
  const query = new URLSearchParams()
  const limit = filters.limit ?? 10
  const page = filters.page ?? 1

  query.set('limit', String(limit))
  query.set('offset', String((page - 1) * limit))

  if (filters.status) query.set('status', filters.status)
  if (filters.priority) query.set('priority', filters.priority)
  if (filters.milestoneId) query.set('milestone_id', String(filters.milestoneId))
  if (filters.search) query.set('search', filters.search)

  return query.toString()
}

function taskPayload(input: CreateExecutionTaskInput | UpdateExecutionTaskInput) {
  return {
    ...(input.milestoneId !== undefined ? { milestone_id: input.milestoneId } : {}),
    ...(input.title !== undefined ? { title: input.title } : {}),
    ...(input.description !== undefined ? { description: input.description } : {}),
    ...(input.instructions !== undefined ? { instructions: input.instructions } : {}),
    ...(input.acceptanceCriteria !== undefined
      ? { acceptance_criteria: input.acceptanceCriteria }
      : {}),
    ...(input.priority !== undefined ? { priority: input.priority } : {}),
    ...(input.evidenceRequired !== undefined ? { evidence_required: input.evidenceRequired } : {}),
    ...(input.ownerId !== undefined ? { owner_id: input.ownerId } : {}),
    ...(input.assigneeIds !== undefined ? { assignee_ids: input.assigneeIds } : {}),
    ...(input.dueDate !== undefined ? { due_date: input.dueDate } : {}),
    ...('status' in input && input.status !== undefined ? { status: input.status } : {}),
  }
}

export const executionTaskApi = {
  async list(orderId: number, filters: ExecutionTaskFilters = {}) {
    return mapExecutionTaskList(
      await apiClient.get<unknown>(`/orders/${orderId}/tasks?${taskQuery(filters)}`),
    )
  },

  async detail(orderId: number, taskId: number) {
    return mapExecutionTask(await apiClient.get<unknown>(`/orders/${orderId}/tasks/${taskId}`))
  },

  async create(orderId: number, input: CreateExecutionTaskInput) {
    return mapExecutionTask(
      await apiClient.post<unknown>(`/orders/${orderId}/tasks`, {
        ...taskPayload(input),
        status: 'to_do',
      }),
    )
  },

  async update(orderId: number, taskId: number, input: UpdateExecutionTaskInput) {
    return mapExecutionTask(
      await apiClient.patch<unknown>(`/orders/${orderId}/tasks/${taskId}`, taskPayload(input)),
    )
  },

  async advance(orderId: number, taskId: number) {
    return mapExecutionTask(
      await apiClient.post<unknown>(`/orders/${orderId}/tasks/${taskId}/advance`, {}),
    )
  },

  async cancel(orderId: number, taskId: number) {
    return mapExecutionTask(
      await apiClient.patch<unknown>(`/orders/${orderId}/tasks/${taskId}`, {
        status: 'cancelled',
      }),
    )
  },

  async remove(orderId: number, taskId: number) {
    return apiClient.delete<unknown>(`/orders/${orderId}/tasks/${taskId}`)
  },
}
