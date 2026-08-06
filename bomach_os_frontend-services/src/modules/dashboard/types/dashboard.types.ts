export type DashboardMetricKey =
  | 'open_requests'
  | 'pending_quotations'
  | 'awaiting_approval'
  | 'active_orders'
  | 'outstanding_invoices'
  | 'payment_submissions'
  | 'open_tasks'
  | 'service_configuration'

export type DashboardSeverity = 'info' | 'warning' | 'danger'
export type DashboardTrend = 'up' | 'down' | 'neutral'

export interface DashboardMetric {
  key: DashboardMetricKey
  label: string
  value: number
  description: string
  trend?: {
    direction: Exclude<DashboardTrend, 'neutral'>
    label: string
  }
}

export interface DashboardAttentionItem {
  id: string
  severity: DashboardSeverity
  title: string
  description: string
  recordType: string
  recordNumber?: string
  dueLabel?: string
  destination?: {
    section: string
  }
}

export interface DashboardPipelineStage {
  key: string
  label: string
  count: number
  destination?: {
    section: string
  }
}

export interface DashboardRiskItem {
  id: string
  severity: DashboardSeverity
  label: string
  count: number
  description: string
  destination?: {
    section: string
  }
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
  destination?: {
    section: string
  }
}
