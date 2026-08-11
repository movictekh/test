import type { ExecutionTask, PaginatedExecutionTasks } from './execution-task.types'

type RecordValue = Record<string, unknown>

const record = (value: unknown): RecordValue =>
  typeof value === 'object' && value !== null && !Array.isArray(value) ? (value as RecordValue) : {}

const array = (value: unknown): unknown[] => (Array.isArray(value) ? value : [])
const string = (value: unknown, fallback = '') => (typeof value === 'string' ? value : fallback)

const number = (value: unknown, fallback = 0) => {
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : fallback
}

const nullableNumber = (value: unknown) => (value == null || value === '' ? null : number(value))

const nullableString = (value: unknown) => (value == null || value === '' ? null : string(value))

export function mapExecutionTask(payload: unknown): ExecutionTask {
  const value = record(payload)

  return {
    id: number(value.id),
    taskNumber: string(value.task_number),
    orderId: number(value.order_id),
    milestoneId: nullableNumber(value.milestone_id),
    title: string(value.title),
    description: string(value.description),
    instructions: string(value.instructions),
    acceptanceCriteria: string(value.acceptance_criteria),
    status: string(value.status, 'to_do') as ExecutionTask['status'],
    priority: string(value.priority, 'normal') as ExecutionTask['priority'],
    evidenceRequired: Boolean(value.evidence_required),
    ownerId: nullableNumber(value.owner_id),
    assigneeIds: array(value.assignee_ids)
      .map((item) => number(item))
      .filter(Boolean),
    dueDate: nullableString(value.due_date),
    completedAt: nullableString(value.completed_at),
    createdById: number(value.created_by_id),
    createdAt: string(value.created_at),
    updatedAt: string(value.updated_at),
  }
}

export function mapExecutionTaskList(payload: unknown): PaginatedExecutionTasks {
  const value = record(payload)
  const items = Array.isArray(payload) ? payload : (value.items ?? value.results)

  return {
    count: Array.isArray(payload) ? payload.length : number(value.count),
    items: array(items).map(mapExecutionTask),
  }
}
