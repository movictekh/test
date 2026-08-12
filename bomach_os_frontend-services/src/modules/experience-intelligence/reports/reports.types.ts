export interface ReportsKpis {
  quoteToOrderConversion: number
  averageResponseTimeMinutes: number
  grossServiceMargin: number
  onTimeDelivery: number
}

export interface ServicePerformanceItem {
  serviceName: string
  completionRate: number
  revenue: number
}

export interface BranchPerformanceItem {
  branchName: string
  requests: number
  activeOrders: number
  revenue: number
  sla: number
  csat: number
}
