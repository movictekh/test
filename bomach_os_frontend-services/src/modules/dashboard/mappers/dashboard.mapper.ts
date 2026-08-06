import type {
  DashboardActivityItem,
  DashboardAttentionItem,
  DashboardConfigurationReadiness,
  DashboardMetric,
  DashboardMetricKey,
  DashboardMyWork,
  DashboardPipelineStage,
  DashboardRiskItem,
  DashboardSeverity,
  OperationsDashboardSummary,
} from '../types/dashboard.types'

type UnknownRecord = Record<string, unknown>

function record(value: unknown): UnknownRecord {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
    ? (value as UnknownRecord)
    : {}
}

function array(value: unknown): unknown[] {
  return Array.isArray(value) ? value : []
}

function text(value: unknown, fallback = ''): string {
  return typeof value === 'string' && value.trim() ? value.trim() : fallback
}

function number(value: unknown, fallback = 0): number {
  const parsed = typeof value === 'number' ? value : Number(value)
  return Number.isFinite(parsed) ? parsed : fallback
}

function severity(value: unknown): DashboardSeverity {
  return value === 'danger' || value === 'warning' ? value : 'info'
}

function metricKey(value: unknown): DashboardMetricKey {
  const supported: DashboardMetricKey[] = [
    'open_requests',
    'pending_quotations',
    'awaiting_approval',
    'active_orders',
    'outstanding_invoices',
    'payment_submissions',
    'open_tasks',
    'service_configuration',
  ]

  const candidate = text(value) as DashboardMetricKey
  return supported.includes(candidate) ? candidate : 'open_requests'
}

function destination(value: unknown): { section: string } | undefined {
  const source = record(value)
  const section = text(source.section ?? source.destination ?? source.route_section)
  return section ? { section } : undefined
}

function mapMetric(value: unknown): DashboardMetric {
  const source = record(value)
  const trendDirection = source.trend === 'down' ? 'down' : source.trend === 'up' ? 'up' : undefined
  const trendLabel = text(source.trend_label ?? source.change_label)

  return {
    key: metricKey(source.key),
    label: text(source.label, 'Operational metric'),
    value: number(source.value ?? source.count),
    description: text(source.description),
    ...(trendDirection && trendLabel
      ? { trend: { direction: trendDirection, label: trendLabel } }
      : {}),
  }
}

function mapAttention(value: unknown, index: number): DashboardAttentionItem {
  const source = record(value)
  const destinationValue = destination(source.destination ?? source.section)
  return {
    id: text(source.id, `attention-${index + 1}`),
    severity: severity(source.severity),
    title: text(source.title, 'Operational attention required'),
    description: text(source.description ?? source.detail),
    recordType: text(source.record_type ?? source.type, 'record'),
    ...(text(source.record_number) ? { recordNumber: text(source.record_number) } : {}),
    ...(text(source.due_label ?? source.due)
      ? { dueLabel: text(source.due_label ?? source.due) }
      : {}),
    ...(destinationValue ? { destination: destinationValue } : {}),
  }
}

function mapPipeline(value: unknown, index: number): DashboardPipelineStage {
  const source = record(value)
  const destinationValue = destination(source.destination ?? source.section)
  return {
    key: text(source.key ?? source.stage, `stage-${index + 1}`),
    label: text(source.label, 'Stage'),
    count: number(source.count ?? source.value),
    ...(destinationValue ? { destination: destinationValue } : {}),
  }
}

function mapRisk(value: unknown, index: number): DashboardRiskItem {
  const source = record(value)
  const destinationValue = destination(source.destination ?? source.section)
  return {
    id: text(source.id, `risk-${index + 1}`),
    severity: severity(source.severity),
    label: text(source.label ?? source.title, 'At-risk work'),
    count: number(source.count ?? source.value),
    description: text(source.description),
    ...(destinationValue ? { destination: destinationValue } : {}),
  }
}

function mapMyWork(value: unknown): DashboardMyWork {
  const source = record(value)
  return {
    assignedRequests: number(source.assigned_requests ?? source.requests),
    activeOrders: number(source.active_orders ?? source.orders),
    openTasks: number(source.open_tasks ?? source.tasks),
    pendingReviews: number(source.pending_reviews ?? source.reviews),
  }
}

function mapConfiguration(value: unknown): DashboardConfigurationReadiness | undefined {
  const source = record(value)
  if (Object.keys(source).length === 0) return undefined

  return {
    activeServices: number(source.active_services),
    draftServices: number(source.draft_services),
    missingWorkflow: number(source.missing_workflow ?? source.services_missing_workflow),
    missingBranchActivation: number(
      source.missing_branch_activation ?? source.services_missing_branch_activation,
    ),
  }
}

function unwrapSummary(payload: unknown): UnknownRecord {
  const source = record(payload)
  const data = record(source.data)
  const summary = record(source.summary)
  return Object.keys(data).length > 0 ? data : Object.keys(summary).length > 0 ? summary : source
}

export function mapDashboardSummary(payload: unknown): OperationsDashboardSummary {
  const source = unwrapSummary(payload)
  const configuration = mapConfiguration(source.configuration)

  return {
    generatedAt: text(source.generated_at, new Date().toISOString()),
    ...(text(source.greeting_name) ? { greetingName: text(source.greeting_name) } : {}),
    metrics: array(source.metrics).map(mapMetric),
    attentionItems: array(source.attention_items).map(mapAttention),
    pipeline: array(source.pipeline).map(mapPipeline),
    risks: array(source.risks ?? source.at_risk).map(mapRisk),
    myWork: mapMyWork(source.my_work),
    ...(configuration ? { configuration } : {}),
  }
}

function unwrapActivities(payload: unknown): unknown[] {
  if (Array.isArray(payload)) return payload
  const source = record(payload)
  const data = source.data
  if (Array.isArray(data)) return data
  return array(source.items ?? source.activities ?? source.recent_activity)
}

export function mapDashboardActivity(payload: unknown): DashboardActivityItem[] {
  return unwrapActivities(payload).map((value, index) => {
    const source = record(value)
    const destinationValue = destination(source.destination ?? source.section)
    const description = text(source.description ?? source.detail)
    const actor = text(source.actor ?? source.actor_name ?? source.created_by_name)
    const recordType = text(source.record_type ?? source.type)
    const recordNumber = text(source.record_number)
    return {
      id: text(source.id, `activity-${index + 1}`),
      title: text(source.title ?? source.action, 'Operational activity'),
      ...(description ? { description } : {}),
      ...(actor ? { actor } : {}),
      occurredAt: text(
        source.occurred_at ?? source.created_at ?? source.timestamp,
        new Date().toISOString(),
      ),
      ...(recordType ? { recordType } : {}),
      ...(recordNumber ? { recordNumber } : {}),
      ...(destinationValue ? { destination: destinationValue } : {}),
    }
  })
}
