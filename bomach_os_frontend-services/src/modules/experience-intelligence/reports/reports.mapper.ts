import type { BranchPerformanceItem, ReportsKpis, ServicePerformanceItem } from './reports.types'

function objectValue(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' ? (value as Record<string, unknown>) : {}
}

function stringValue(value: unknown): string {
  return typeof value === 'string' ? value : ''
}

function numberValue(value: unknown): number {
  if (typeof value === 'number') return value
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : 0
}

export function mapReportsKpis(value: unknown): ReportsKpis {
  const row = objectValue(value)

  return {
    quoteToOrderConversion: numberValue(row.quote_to_order_conversion),
    averageResponseTimeMinutes: numberValue(row.average_response_time_minutes),
    grossServiceMargin: numberValue(row.gross_service_margin),
    onTimeDelivery: numberValue(row.on_time_delivery),
  }
}

export function mapServicePerformance(value: unknown): ServicePerformanceItem[] {
  if (!Array.isArray(value)) return []

  return value.map((entry) => {
    const row = objectValue(entry)

    return {
      serviceName: stringValue(row.service_name) || 'Unknown Service',
      completionRate: numberValue(row.completion_rate),
      revenue: numberValue(row.revenue),
    }
  })
}

export function mapBranchPerformance(value: unknown): BranchPerformanceItem[] {
  if (!Array.isArray(value)) return []

  return value.map((entry) => {
    const row = objectValue(entry)

    return {
      branchName: stringValue(row.branch_name) || 'Unknown Branch',
      requests: numberValue(row.requests),
      activeOrders: numberValue(row.active_orders),
      revenue: numberValue(row.revenue),
      sla: numberValue(row.sla),
      csat: numberValue(row.csat),
    }
  })
}
