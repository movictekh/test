export interface DashboardSummaryContract {
  generated_at?: string
  greeting_name?: string
  metrics?: unknown[]
  attention_items?: unknown[]
  requests_requiring_action?: unknown[]
  pipeline?: unknown[]
  risks?: unknown[]
  my_work?: unknown
  configuration?: unknown
  summary?: unknown
  data?: unknown
}

export interface DashboardRecentActivityContract {
  items?: unknown[]
  activities?: unknown[]
  recent_activity?: unknown[]
  data?: unknown
}
