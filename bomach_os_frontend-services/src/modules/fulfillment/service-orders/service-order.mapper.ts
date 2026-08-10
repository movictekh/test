import type {
  EmployeeOption,
  PaginatedServiceOrders,
  ServiceOrder,
  ServiceOrderActivity,
  ServiceOrderMilestone,
} from './service-order.types'

type R = Record<string, unknown>
const rec = (value: unknown): R =>
  typeof value === 'object' && value !== null && !Array.isArray(value) ? (value as R) : {}
const arr = (value: unknown): unknown[] => (Array.isArray(value) ? value : [])
const str = (value: unknown, fallback = '') => (typeof value === 'string' ? value : fallback)
const num = (value: unknown, fallback = 0) => {
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : fallback
}
const nullableNum = (value: unknown) => (value == null || value === '' ? null : num(value))
const nullableStr = (value: unknown) => (value == null || value === '' ? null : str(value))

export function mapServiceOrderMilestone(payload: unknown): ServiceOrderMilestone {
  const value = rec(payload)
  return {
    id: num(value.id),
    workflowStageId: nullableNum(value.workflow_stage_id),
    name: str(value.name),
    status: str(value.status, 'pending') as ServiceOrderMilestone['status'],
    sortOrder: num(value.sort_order),
    ownerRoleId: nullableNum(value.owner_role_id),
    clientVisible: Boolean(value.client_visible),
    dueDate: nullableStr(value.due_date),
    completedAt: nullableStr(value.completed_at),
    createdAt: str(value.created_at),
    updatedAt: str(value.updated_at),
  }
}

export function mapServiceOrderActivity(payload: unknown): ServiceOrderActivity {
  const value = rec(payload)
  return {
    id: num(value.id),
    activityType: str(value.activity_type),
    visibility: str(value.visibility, 'internal_client') as ServiceOrderActivity['visibility'],
    note: str(value.note),
    progress: nullableNum(value.progress),
    nextAction: str(value.next_action),
    createdById: nullableNum(value.created_by_id),
    createdAt: str(value.created_at),
  }
}

export function mapServiceOrder(payload: unknown): ServiceOrder {
  const value = rec(payload)
  const service = rec(value.service)
  const quote = rec(value.quote)
  const taskCounts = rec(value.task_counts)
  const deliverableCounts = rec(value.deliverable_counts)

  return {
    id: num(value.id),
    orderNumber: str(value.order_number),
    clientId: num(value.client_id),
    serviceId: num(service.id),
    serviceName: str(service.name),
    quoteId: nullableNum(quote.id),
    quoteNumber: str(quote.quote_number),
    serviceRequestId: nullableNum(value.service_request_id),
    invoiceId: nullableNum(value.invoice_id),
    description: str(value.description),
    amount: num(value.amount),
    orderStatus: str(value.order_status, 'pending_mobilisation') as ServiceOrder['orderStatus'],
    paymentStatus: str(value.payment_status, 'unpaid') as ServiceOrder['paymentStatus'],
    validUntil: str(value.valid_until),
    dueDate: nullableStr(value.due_date),
    progress: num(value.progress),
    stage: str(value.stage),
    nextAction: str(value.next_action),
    startedAt: nullableStr(value.started_at),
    completedAt: nullableStr(value.completed_at),
    createdAt: str(value.created_at),
    updatedAt: str(value.updated_at),
    createdById: num(value.created_by_id),
    assignedToId: nullableNum(value.assigned_to_id),
    branchId: nullableNum(value.branch_id),
    taskCounts: Object.fromEntries(
      Object.entries(taskCounts).map(([key, count]) => [key, num(count)]),
    ),
    deliverableCounts: Object.fromEntries(
      Object.entries(deliverableCounts).map(([key, count]) => [key, num(count)]),
    ),
    milestones: arr(value.milestones).map(mapServiceOrderMilestone),
    activities: arr(value.activities).map(mapServiceOrderActivity),
  }
}

export function mapServiceOrderList(payload: unknown): PaginatedServiceOrders {
  const value = rec(payload)
  const items = Array.isArray(payload) ? payload : (value.items ?? value.results)
  return {
    count: Array.isArray(payload) ? payload.length : num(value.count),
    items: arr(items).map(mapServiceOrder),
  }
}

export function mapEmployeeOptions(payload: unknown): EmployeeOption[] {
  const value = rec(payload)
  const items = Array.isArray(payload) ? payload : (value.items ?? value.results)
  return arr(items).map((raw) => {
    const row = rec(raw)
    const first = str(row.first_name)
    const middle = str(row.middle_name)
    const last = str(row.last_name)
    const name =
      [first, middle, last].filter(Boolean).join(' ') || str(row.email) || str(row.employee_id)
    return {
      id: num(row.id),
      userId: num(row.user_id),
      name,
      employeeId: str(row.employee_id),
      designation: str(row.designation),
      branchName: str(row.branch_name),
      active: Boolean(row.is_active),
    }
  })
}
