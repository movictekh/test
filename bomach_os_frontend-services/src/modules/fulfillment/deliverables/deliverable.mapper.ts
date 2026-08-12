import type { Deliverable, PaginatedDeliverables } from './deliverable.types'

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

export function mapDeliverable(payload: unknown): Deliverable {
  const value = record(payload)

  return {
    id: number(value.id),
    deliverableNumber: string(value.deliverable_number),
    orderId: number(value.order_id),
    milestoneId: nullableNumber(value.milestone_id),
    taskId: nullableNumber(value.task_id),
    title: string(value.title),
    deliverableType: string(value.deliverable_type, 'report') as Deliverable['deliverableType'],
    version: string(value.version, 'v1'),
    fileUrl: string(value.file_url),
    fileName: string(value.file_name),
    contentType: string(value.content_type),
    fileSizeBytes: number(value.file_size_bytes),
    description: string(value.description),
    clientVisible: Boolean(value.client_visible),
    status: string(value.status, 'draft') as Deliverable['status'],
    approvalMode: string(value.approval_mode, 'none') as Deliverable['approvalMode'],
    ownerId: nullableNumber(value.owner_id),
    approvedById: nullableNumber(value.approved_by_id),
    approvedAt: nullableString(value.approved_at),
    rejectedById: nullableNumber(value.rejected_by_id),
    rejectedAt: nullableString(value.rejected_at),
    rejectionReason: string(value.rejection_reason),
    createdById: number(value.created_by_id),
    createdAt: string(value.created_at),
    updatedAt: string(value.updated_at),
  }
}

export function mapDeliverableList(payload: unknown): PaginatedDeliverables {
  const value = record(payload)
  const items = Array.isArray(payload) ? payload : (value.items ?? value.results)

  return {
    count: Array.isArray(payload) ? payload.length : number(value.count),
    items: array(items).map(mapDeliverable),
  }
}
