import type { AppRecordSearch } from '@/shared/navigation'

export type DashboardMetricKey =
  | 'open_requests'
  | 'pending_quotations'
  | 'awaiting_approval'
  | 'active_orders'
  | 'outstanding_invoices'
  | 'payment_submissions'
  | 'open_tasks'
  | 'service_configuration'

export type DashboardSeverity = 'info' | 'warning' | 'danger' | 'success'
export type DashboardProgressTone = 'brand' | 'success' | 'warning' | 'danger'

export interface DashboardDestination {
  section: string
  search?: AppRecordSearch
}

export interface DashboardMetric {
  key: DashboardMetricKey
  label: string
  value: number
  valueFormat?: 'number' | 'currency' | 'percent'
  description: string
  trend?: { direction: 'up' | 'down'; label: string }
}

export interface DashboardAttentionItem {
  id: string
  severity: Exclude<DashboardSeverity, 'success'>
  title: string
  description: string
  recordType: string
  recordNumber?: string
  dueLabel?: string
  requestNumber?: string
  createdLabel?: string
  client?: string
  service?: string
  statusLabel?: string
  statusTone?: Exclude<DashboardSeverity, 'success'>
  owner?: string
  nextAction?: string
  priority?: string
  destination?: DashboardDestination
}

export interface DashboardPipelineStage {
  key: string
  label: string
  count: number
  description?: string
  state?: 'done' | 'active' | 'pending'
  destination?: DashboardDestination
}

export interface DashboardExecutiveAlert {
  id: string
  severity: DashboardSeverity
  title: string
  description: string
  value?: number
  valueFormat?: 'number' | 'currency' | 'percent'
  destination?: DashboardDestination
}

export interface DashboardHealthMetric {
  key: string
  label: string
  value: number
  tone: DashboardProgressTone
}

export interface DashboardServicePerformance {
  id: string
  serviceName: string
  completionRate: number
  verifiedRevenue: number
  destination?: DashboardDestination
}

export interface DashboardBranchPerformance {
  id: string
  branchName: string
  requests: number
  activeOrders: number
  verifiedRevenue: number
  slaPerformance: number
  clientSatisfaction: number
}

export interface DashboardRevenueByDivision {
  id: string
  division: string
  verifiedRevenue: number
}

export interface DashboardRiskItem {
  id: string
  severity: Exclude<DashboardSeverity, 'success'>
  label: string
  count: number
  description: string
  destination?: DashboardDestination
}

export interface DashboardMyWork {
  assignedRequests: number
  activeOrders: number
  openTasks: number
  pendingReviews: number
}

export interface DashboardConfigurationReadiness {
  activeServices: number
  draftServices: number
  missingWorkflow: number
  missingBranchActivation: number
}

export interface OperationsDashboardSummary {
  generatedAt: string
  greetingName?: string
  metrics: DashboardMetric[]
  attentionItems: DashboardAttentionItem[]
  pipeline: DashboardPipelineStage[]
  executiveAlerts: DashboardExecutiveAlert[]
  operationsHealth: DashboardHealthMetric[]
  servicePerformance: DashboardServicePerformance[]
  branchPerformance: DashboardBranchPerformance[]
  revenueByDivision: DashboardRevenueByDivision[]
  risks: DashboardRiskItem[]
  myWork: DashboardMyWork
  configuration?: DashboardConfigurationReadiness
}

export interface DashboardActivityItem {
  id: string
  title: string
  description?: string
  actor?: string
  occurredAt: string
  recordType?: string
  recordNumber?: string
  destination?: DashboardDestination
}
