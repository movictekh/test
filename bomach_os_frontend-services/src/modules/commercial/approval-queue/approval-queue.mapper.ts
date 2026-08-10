import type {
  ApprovalQueueChoices,
  ApprovalQueueItem,
  ApprovalQueuePage,
  ApprovalQueueStats,
} from './approval-queue.types'

type R = Record<string, unknown>

const rec = (value: unknown): R =>
  typeof value === 'object' && value !== null && !Array.isArray(value) ? (value as R) : {}

const text = (value: unknown, fallback = '') => (typeof value === 'string' ? value : fallback)

const number = (value: unknown, fallback = 0) => {
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : fallback
}

const nullableNumber = (value: unknown) => (value == null || value === '' ? null : number(value))

const nullableText = (value: unknown) => (value == null || value === '' ? null : text(value))

const array = (value: unknown): unknown[] => (Array.isArray(value) ? value : [])

export function mapApprovalQueueItem(payload: unknown): ApprovalQueueItem {
  const value = rec(payload)
  return {
    id: text(value.id),
    source: text(value.source) as ApprovalQueueItem['source'],
    sourceDisplay: text(value.source_display, text(value.source)),
    refNumber: text(value.ref_number),
    subject: text(value.subject),
    requesterName: text(value.requester_name),
    approverName: text(value.approver_name),
    amount: nullableNumber(value.amount),
    createdAt: text(value.created_at),
    status: text(value.status, 'pending') as ApprovalQueueItem['status'],
    actionLabel: text(value.action_label),
    approveUrl: nullableText(value.approve_url),
    rejectUrl: nullableText(value.reject_url),
  }
}

export function mapApprovalQueuePage(payload: unknown): ApprovalQueuePage {
  const value = rec(payload)
  return {
    count: number(value.count),
    items: array(value.results).map(mapApprovalQueueItem),
  }
}

export function mapApprovalQueueStats(payload: unknown): ApprovalQueueStats {
  const value = rec(payload)
  return {
    pendingCount: number(value.pending_count),
    highValueCount: number(value.high_value_count),
    oldestWaitingDays: number(value.oldest_waiting_days),
    slaPercent: number(value.sla_percent),
  }
}

export function mapApprovalQueueChoices(payload: unknown): ApprovalQueueChoices {
  const value = rec(payload)
  const mapChoices = (items: unknown) =>
    array(items)
      .map((item) => {
        const row = rec(item)
        return { value: text(row.value), label: text(row.label) }
      })
      .filter((item) => item.value && item.label)

  return {
    sources: mapChoices(value.sources),
    statuses: mapChoices(value.statuses),
  }
}
