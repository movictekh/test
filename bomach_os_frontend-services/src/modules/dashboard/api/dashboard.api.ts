import { apiClient } from '@/shared/api/api-client'
import { getRecordDestination } from '@/shared/navigation'

import type {
  DashboardActivityItem,
  DashboardAttentionItem,
  DashboardExecutiveAlert,
  DashboardMetric,
  DashboardPipelineStage,
} from '../types/dashboard.types'

interface FinancialsDto {
  revenue: string
  expenses: string
  outstanding: string
  margin_pct: number
}

interface ApprovalSummaryDto {
  items: Array<{
    domain: string
    count: number
    oldest_days: number
  }>
  total_pending: number
}

interface PipelineDto {
  stages: Array<{
    name: string
    count: number
    value: string
  }>
  conversion_rate: number
}

interface ActionItemDto {
  id: number
  type: string
  title: string
  description: string
  due_date: string | null
  priority: string
  link: string
}

interface ActivityDto {
  id: number
  type: string
  title: string
  description: string
  timestamp: string
  link: string
  actor_name: string
}

function number(value: string | number): number {
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : 0
}

function destinationFromBackend(type: string, link: string) {
  const match = link.match(
    /^\/(orders|quotes|invoices|approvals|requests|tasks|deliverables|feedback)\/(.+)$/,
  )

  if (match) {
    const [, resource, id] = match
    if (resource && id) {
      const entityType =
        resource === 'quotes'
          ? 'quote'
          : resource === 'invoices'
            ? 'invoice'
            : resource === 'approvals'
              ? 'approval'
              : resource === 'requests'
                ? 'request'
                : resource === 'orders'
                  ? 'order'
                  : resource.slice(0, -1)

      return getRecordDestination(entityType, id) ?? undefined
    }
  }

  return getRecordDestination(type, undefined) ?? undefined
}

export const dashboardApi = {
  async financials(): Promise<DashboardMetric[]> {
    const dto = await apiClient.get<FinancialsDto>('/command-center/financials')

    return [
      {
        key: 'outstanding_invoices',
        label: 'Verified revenue',
        value: number(dto.revenue),
        valueFormat: 'currency',
        description: 'Backend-reported revenue',
      },
      {
        key: 'open_requests',
        label: 'Approved expenses',
        value: number(dto.expenses),
        valueFormat: 'currency',
        description: 'Backend-reported approved expenses',
      },
      {
        key: 'payment_submissions',
        label: 'Outstanding',
        value: number(dto.outstanding),
        valueFormat: 'currency',
        description: 'Backend-reported outstanding amount',
      },
      {
        key: 'service_configuration',
        label: 'Margin',
        value: dto.margin_pct,
        valueFormat: 'percent',
        description: 'Backend-reported margin',
      },
    ]
  },

  async pendingApprovals(): Promise<{ total: number; alerts: DashboardExecutiveAlert[] }> {
    const dto = await apiClient.get<ApprovalSummaryDto>('/command-center/pending-approvals')

    return {
      total: dto.total_pending,
      alerts: dto.items.map((item) => ({
        id: `approval-${item.domain}`,
        severity: item.count > 0 ? 'warning' : 'info',
        title: item.domain
          .replace(/_/g, ' ')
          .replace(/\b\w/g, (character) => character.toUpperCase()),
        description:
          item.count === 0
            ? 'No pending items'
            : `${item.count} pending${item.oldest_days > 0 ? ` - oldest ${item.oldest_days}d` : ''}`,
        value: item.count,
        valueFormat: 'number',
        destination: { section: 'approvals' },
      })),
    }
  },

  async pipeline(): Promise<{ stages: DashboardPipelineStage[]; conversionRate: number }> {
    const dto = await apiClient.get<PipelineDto>('/command-center/pipeline')

    return {
      stages: dto.stages.map((stage) => ({
        key: stage.name.toLowerCase().replace(/[^a-z0-9]+/g, '-'),
        label: stage.name,
        count: stage.count,
        description: `Value: ${number(stage.value).toLocaleString('en-NG')}`,
        state: 'pending',
        destination: { section: 'service-orders' },
      })),
      conversionRate: dto.conversion_rate,
    }
  },

  async actionItems(): Promise<DashboardAttentionItem[]> {
    const dto = await apiClient.get<ActionItemDto[]>('/command-center/action-items')

    return dto.map((item) => {
      const destination = destinationFromBackend(item.type, item.link)

      return {
        id: String(item.id),
        severity: item.priority === 'high' || item.priority === 'critical' ? 'warning' : 'info',
        title: item.title,
        description: item.description,
        recordType: item.type,
        ...(item.due_date ? { dueLabel: item.due_date } : {}),
        priority: item.priority,
        ...(destination ? { destination } : {}),
      }
    })
  },

  async activity(): Promise<DashboardActivityItem[]> {
    const dto = await apiClient.get<ActivityDto[]>('/command-center/activity')

    return dto.map((item) => {
      const destination = destinationFromBackend(item.type, item.link)

      return {
        id: `${item.type}-${item.id}`,
        title: item.title,
        description: item.description,
        ...(item.actor_name ? { actor: item.actor_name } : {}),
        occurredAt: item.timestamp,
        recordType: item.type,
        ...(destination ? { destination } : {}),
      }
    })
  },
}
