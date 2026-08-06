import type {
  DashboardActivityItem,
  DashboardAttentionItem,
  DashboardBranchPerformance,
  DashboardConfigurationReadiness,
  DashboardDestination,
  DashboardExecutiveAlert,
  DashboardHealthMetric,
  DashboardMetric,
  DashboardMetricKey,
  DashboardMyWork,
  DashboardPipelineStage,
  DashboardProgressTone,
  DashboardRevenueByDivision,
  DashboardRiskItem,
  DashboardServicePerformance,
  DashboardSeverity,
  OperationsDashboardSummary,
} from '../types/dashboard.types'

type R = Record<string, unknown>
const rec = (v: unknown): R =>
  typeof v === 'object' && v !== null && !Array.isArray(v) ? (v as R) : {}
const arr = (v: unknown): unknown[] => (Array.isArray(v) ? v : [])
const str = (v: unknown, fallback = '') => (typeof v === 'string' && v.trim() ? v.trim() : fallback)
const num = (v: unknown, fallback = 0) => {
  const parsed = typeof v === 'number' ? v : Number(v)
  return Number.isFinite(parsed) ? parsed : fallback
}
const sev = (v: unknown): DashboardSeverity =>
  v === 'danger' || v === 'warning' || v === 'success' ? v : 'info'
const tone = (v: unknown, score: number): DashboardProgressTone =>
  v === 'danger' || v === 'warning' || v === 'success'
    ? v
    : score < 80
      ? 'danger'
      : score < 90
        ? 'warning'
        : score >= 95
          ? 'success'
          : 'brand'
const format = (v: unknown) =>
  v === 'currency' || v === 'percent' || v === 'number' ? v : undefined
const dest = (v: unknown): DashboardDestination | undefined => {
  if (typeof v === 'string' && v.trim()) return { section: v.trim() }
  const x = rec(v)
  const section = str(x.section ?? x.destination ?? x.route_section)
  return section ? { section } : undefined
}

const metricKeys: DashboardMetricKey[] = [
  'open_requests',
  'pending_quotations',
  'awaiting_approval',
  'active_orders',
  'outstanding_invoices',
  'payment_submissions',
  'open_tasks',
  'service_configuration',
]

function mapMetric(value: unknown): DashboardMetric {
  const x = rec(value)
  const key = str(x.key) as DashboardMetricKey
  const valueFormat = format(x.value_format ?? x.format)
  const direction = x.trend === 'up' || x.trend === 'down' ? x.trend : undefined
  const trendLabel = str(x.trend_label ?? x.change_label)

  return {
    key: metricKeys.includes(key) ? key : 'open_requests',
    label: str(x.label, 'Operational metric'),
    value: num(x.value ?? x.count),
    ...(valueFormat ? { valueFormat } : {}),
    description: str(x.description),
    ...(direction && trendLabel ? { trend: { direction, label: trendLabel } } : {}),
  }
}

function mapAttention(value: unknown, index: number): DashboardAttentionItem {
  const x = rec(value)
  const severity = sev(x.severity)
  const destination = dest(x.destination ?? x.section)
  const statusToneRaw = x.status_tone ?? x.statusSeverity ?? x.status_severity
  const statusTone =
    statusToneRaw === 'danger' || statusToneRaw === 'warning' || statusToneRaw === 'info'
      ? statusToneRaw
      : undefined
  return {
    id: str(x.id, `attention-${index + 1}`),
    severity: severity === 'success' ? 'info' : severity,
    title: str(x.title ?? x.status_label ?? x.status, 'Operational attention required'),
    description: str(x.description ?? x.detail ?? x.next_action),
    recordType: str(x.record_type ?? x.type, 'record'),
    ...(str(x.record_number) ? { recordNumber: str(x.record_number) } : {}),
    ...(str(x.due_label ?? x.due) ? { dueLabel: str(x.due_label ?? x.due) } : {}),
    ...(str(x.request_number ?? x.record_number)
      ? { requestNumber: str(x.request_number ?? x.record_number) }
      : {}),
    ...(str(x.created_label ?? x.created)
      ? { createdLabel: str(x.created_label ?? x.created) }
      : {}),
    ...(str(x.client) ? { client: str(x.client) } : {}),
    ...(str(x.service) ? { service: str(x.service) } : {}),
    ...(str(x.status_label ?? x.status) ? { statusLabel: str(x.status_label ?? x.status) } : {}),
    ...(statusTone ? { statusTone } : {}),
    ...(str(x.owner) ? { owner: str(x.owner) } : {}),
    ...(str(x.next_action ?? x.next) ? { nextAction: str(x.next_action ?? x.next) } : {}),
    ...(destination ? { destination } : {}),
  }
}

function mapPipeline(value: unknown, index: number): DashboardPipelineStage {
  const x = rec(value)
  const destination = dest(x.destination ?? x.section)
  const state = x.state === 'done' || x.state === 'active' ? x.state : 'pending'
  return {
    key: str(x.key ?? x.stage, `stage-${index + 1}`),
    label: str(x.label, 'Stage'),
    count: num(x.count ?? x.value),
    ...(str(x.description) ? { description: str(x.description) } : {}),
    state,
    ...(destination ? { destination } : {}),
  }
}

function mapExecutiveAlert(value: unknown, index: number): DashboardExecutiveAlert {
  const x = rec(value)
  const destination = dest(x.destination ?? x.section)
  const valueFormat = format(x.value_format ?? x.format)
  return {
    id: str(x.id, `alert-${index + 1}`),
    severity: sev(x.severity),
    title: str(x.title, 'Executive alert'),
    description: str(x.description),
    ...(x.value !== undefined || x.count !== undefined ? { value: num(x.value ?? x.count) } : {}),
    ...(valueFormat ? { valueFormat } : {}),
    ...(destination ? { destination } : {}),
  }
}

function mapHealth(value: unknown, index: number): DashboardHealthMetric {
  const x = rec(value)
  const score = num(x.value ?? x.score)
  return {
    key: str(x.key, `health-${index + 1}`),
    label: str(x.label, 'Operational health'),
    value: score,
    tone: tone(x.tone, score),
  }
}

function mapService(value: unknown, index: number): DashboardServicePerformance {
  const x = rec(value)
  const destination = dest(x.destination ?? x.section)
  return {
    id: str(x.id, `service-${index + 1}`),
    serviceName: str(x.service_name ?? x.name, 'Service'),
    completionRate: num(x.completion_rate ?? x.completion ?? x.progress),
    verifiedRevenue: num(x.verified_revenue ?? x.revenue ?? x.amount),
    ...(destination ? { destination } : {}),
  }
}

function mapBranch(value: unknown, index: number): DashboardBranchPerformance {
  const x = rec(value)
  return {
    id: str(x.id, `branch-${index + 1}`),
    branchName: str(x.branch_name ?? x.name, 'Branch'),
    requests: num(x.requests ?? x.request_count),
    activeOrders: num(x.active_orders ?? x.order_count),
    verifiedRevenue: num(x.verified_revenue ?? x.revenue ?? x.amount),
    slaPerformance: num(x.sla_performance ?? x.sla),
    clientSatisfaction: num(x.client_satisfaction ?? x.csat),
  }
}

function mapDivisionRevenue(value: unknown, index: number): DashboardRevenueByDivision {
  const x = rec(value)
  return {
    id: str(x.id, `division-${index + 1}`),
    division: str(x.division_name ?? x.division ?? x.name, 'Division'),
    verifiedRevenue: num(x.verified_revenue ?? x.revenue ?? x.amount),
  }
}

function mapRisk(value: unknown, index: number): DashboardRiskItem {
  const x = rec(value)
  const severity = sev(x.severity)
  const destination = dest(x.destination ?? x.section)
  return {
    id: str(x.id, `risk-${index + 1}`),
    severity: severity === 'success' ? 'info' : severity,
    label: str(x.label ?? x.title, 'At-risk work'),
    count: num(x.count ?? x.value),
    description: str(x.description),
    ...(destination ? { destination } : {}),
  }
}

function mapMyWork(value: unknown): DashboardMyWork {
  const x = rec(value)
  return {
    assignedRequests: num(x.assigned_requests ?? x.requests),
    activeOrders: num(x.active_orders ?? x.orders),
    openTasks: num(x.open_tasks ?? x.tasks),
    pendingReviews: num(x.pending_reviews ?? x.reviews),
  }
}

function mapConfiguration(value: unknown): DashboardConfigurationReadiness | undefined {
  const x = rec(value)
  if (!Object.keys(x).length) return undefined
  return {
    activeServices: num(x.active_services),
    draftServices: num(x.draft_services),
    missingWorkflow: num(x.missing_workflow ?? x.services_missing_workflow),
    missingBranchActivation: num(
      x.missing_branch_activation ?? x.services_missing_branch_activation,
    ),
  }
}

export function mapDashboardSummary(payload: unknown): OperationsDashboardSummary {
  const root = rec(payload)
  const source = Object.keys(rec(root.data)).length
    ? rec(root.data)
    : Object.keys(rec(root.summary)).length
      ? rec(root.summary)
      : root
  const configuration = mapConfiguration(source.configuration)

  return {
    generatedAt: str(source.generated_at, new Date().toISOString()),
    ...(str(source.greeting_name) ? { greetingName: str(source.greeting_name) } : {}),
    metrics: arr(source.metrics ?? source.overview_metrics).map(mapMetric),
    attentionItems: arr(source.attention_items ?? source.requests_requiring_action).map(
      mapAttention,
    ),
    pipeline: arr(source.pipeline ?? source.lifecycle).map(mapPipeline),
    executiveAlerts: arr(source.executive_alerts).map(mapExecutiveAlert),
    operationsHealth: arr(source.operations_health).map(mapHealth),
    servicePerformance: arr(source.service_performance).map(mapService),
    branchPerformance: arr(source.branch_performance).map(mapBranch),
    revenueByDivision: arr(source.revenue_by_division).map(mapDivisionRevenue),
    risks: arr(source.risks ?? source.at_risk).map(mapRisk),
    myWork: mapMyWork(source.my_work),
    ...(configuration ? { configuration } : {}),
  }
}

export function mapDashboardActivity(payload: unknown): DashboardActivityItem[] {
  const root = rec(payload)
  const source = Array.isArray(payload)
    ? payload
    : Array.isArray(root.data)
      ? root.data
      : arr(root.items ?? root.activities ?? root.recent_activity)

  return source.map((value, index) => {
    const x = rec(value)
    const destination = dest(x.destination ?? x.section)
    return {
      id: str(x.id, `activity-${index + 1}`),
      title: str(x.title ?? x.action, 'Operational activity'),
      ...(str(x.description ?? x.detail) ? { description: str(x.description ?? x.detail) } : {}),
      ...(str(x.actor ?? x.actor_name ?? x.created_by_name)
        ? { actor: str(x.actor ?? x.actor_name ?? x.created_by_name) }
        : {}),
      occurredAt: str(x.occurred_at ?? x.created_at ?? x.timestamp, new Date().toISOString()),
      ...(str(x.record_type ?? x.type) ? { recordType: str(x.record_type ?? x.type) } : {}),
      ...(str(x.record_number) ? { recordNumber: str(x.record_number) } : {}),
      ...(destination ? { destination } : {}),
    }
  })
}
