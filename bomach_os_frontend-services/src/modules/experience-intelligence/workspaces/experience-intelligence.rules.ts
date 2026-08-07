import type { CommercialWorkspace } from '@/modules/commercial/types/commercial.types'
import type { FulfillmentWorkspace } from '@/modules/fulfillment/types/fulfillment.types'

import type {
  BranchPerformanceRow,
  FeedbackSummary,
  ReportSnapshot,
  ServiceFeedback,
  ServicePerformanceRow,
} from '../types/experience-intelligence.types'

function percentage(numerator: number, denominator: number): number {
  if (denominator <= 0) return 0
  return Math.round((numerator / denominator) * 100)
}

export function deriveFeedbackSummary(feedback: ServiceFeedback[]): FeedbackSummary {
  if (feedback.length === 0) {
    return {
      averageRating: 0,
      clientSatisfaction: 0,
      reworkRate: 0,
      repeatClients: 0,
    }
  }

  const averageRating = feedback.reduce((sum, item) => sum + item.rating, 0) / feedback.length

  const satisfied = feedback.filter((item) => item.rating >= 4).length
  const rework = feedback.filter(
    (item) => item.type === 'Defect / Rework' || item.type === 'Complaint',
  ).length

  const clientCounts = new Map<string, number>()
  for (const item of feedback) {
    clientCounts.set(item.client, (clientCounts.get(item.client) ?? 0) + 1)
  }

  const repeatClientCount = [...clientCounts.values()].filter((count) => count > 1).length

  return {
    averageRating: Number(averageRating.toFixed(1)),
    clientSatisfaction: percentage(satisfied, feedback.length),
    reworkRate: Number(((rework / feedback.length) * 100).toFixed(1)),
    repeatClients: percentage(repeatClientCount, clientCounts.size),
  }
}

function servicePerformance(fulfillment: FulfillmentWorkspace): ServicePerformanceRow[] {
  const byService = new Map<string, { progress: number[]; value: number }>()

  for (const order of fulfillment.orders) {
    const current = byService.get(order.service) ?? { progress: [], value: 0 }
    current.progress.push(order.progress)
    current.value += order.value
    byService.set(order.service, current)
  }

  return [...byService.entries()]
    .map(([service, value]) => ({
      service,
      averageCompletion: Math.round(
        value.progress.reduce((sum, progress) => sum + progress, 0) /
          Math.max(1, value.progress.length),
      ),
      orderValue: value.value,
    }))
    .sort((a, b) => b.orderValue - a.orderValue)
    .slice(0, 5)
}

function branchPerformance(
  commercial: CommercialWorkspace,
  fulfillment: FulfillmentWorkspace,
  feedback: ServiceFeedback[],
): BranchPerformanceRow[] {
  const branches = [...new Set(commercial.requests.map((request) => request.branch))]
    .filter(Boolean)
    .sort()

  const requestById = new Map(commercial.requests.map((request) => [request.id, request]))
  const orderById = new Map(fulfillment.orders.map((order) => [order.id, order]))

  return branches.map((branch) => {
    const branchRequests = commercial.requests.filter((request) => request.branch === branch)
    const requestIds = new Set(branchRequests.map((request) => request.id))

    const branchOrders = fulfillment.orders.filter((order) => requestIds.has(order.requestId))
    const activeOrders = branchOrders.filter((order) => order.status !== 'Completed').length

    const revenue = commercial.invoices
      .filter((invoice) => requestIds.has(invoice.requestId))
      .reduce((sum, invoice) => sum + invoice.amountPaid, 0)

    const branchFeedback = feedback.filter((item) => {
      const order = orderById.get(item.orderId)
      const request = order ? requestById.get(order.requestId) : undefined
      return request?.branch === branch
    })

    const csat = branchFeedback.length
      ? percentage(branchFeedback.filter((item) => item.rating >= 4).length, branchFeedback.length)
      : 0

    // SLA is exposed as a branch KPI, but current mock contracts do
    // not yet carry completion timestamps. Use a transparent deterministic
    // placeholder until the backend analytics contract provides SLA history.
    const sla = branchOrders.length
      ? Math.max(
          0,
          Math.min(
            100,
            Math.round(
              branchOrders.reduce((sum, order) => sum + Math.min(order.progress + 20, 100), 0) /
                branchOrders.length,
            ),
          ),
        )
      : 0

    return {
      branch,
      requests: branchRequests.length,
      activeOrders,
      revenue,
      sla,
      csat,
    }
  })
}

export function deriveReportSnapshot(
  commercial: CommercialWorkspace,
  fulfillment: FulfillmentWorkspace,
  feedback: ServiceFeedback[],
): ReportSnapshot {
  const linkedOrders = fulfillment.orders.filter(
    (order) => Boolean(order.quotationId) && Boolean(order.invoiceId),
  ).length

  const quoteToOrderConversion = percentage(linkedOrders, commercial.quotations.length)

  return {
    quoteToOrderConversion,
    // These measures need richer backend
    // event/cost history than the current contracts provide.
    averageResponseMinutes: 38,
    grossServiceMargin: 29,
    onTimeDelivery: 87,
    services: servicePerformance(fulfillment),
    branches: branchPerformance(commercial, fulfillment, feedback),
  }
}
