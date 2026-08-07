import type {
  ExecutionTaskStatus,
  OrderMilestone,
  ServiceOrderStatus,
} from '../types/fulfillment.types'

export const orderBoardColumns = [
  'Pending Mobilisation',
  'Active',
  'Quality Review',
  'Awaiting Client',
  'Completed',
] as const satisfies readonly ServiceOrderStatus[]

export const taskBoardColumns = [
  'To Do',
  'In Progress',
  'Review',
  'Done',
] as const satisfies readonly ExecutionTaskStatus[]

export function clampProgress(value: number): number {
  if (!Number.isFinite(value)) return 0
  return Math.max(0, Math.min(100, Math.round(value)))
}

export function advanceMilestones(milestones: OrderMilestone[]): {
  milestones: OrderMilestone[]
  progress: number
  stage: string
  completed: boolean
} {
  const next = milestones.map((item) => ({ ...item }))
  const activeIndex = next.findIndex((item) => item.status === 'Active')

  if (activeIndex < 0) {
    return {
      milestones: next,
      progress: next.every((item) => item.status === 'Done') ? 100 : 0,
      stage: next.at(-1)?.name ?? 'Order Setup',
      completed: next.length > 0 && next.every((item) => item.status === 'Done'),
    }
  }

  const current = next[activeIndex]
  if (!current) {
    return {
      milestones: next,
      progress: next.every((item) => item.status === 'Done') ? 100 : 0,
      stage: next.at(-1)?.name ?? 'Order Setup',
      completed: next.length > 0 && next.every((item) => item.status === 'Done'),
    }
  }

  next[activeIndex] = { id: current.id, name: current.name, status: 'Done' }

  const following = next[activeIndex + 1]
  if (following) {
    next[activeIndex + 1] = { id: following.id, name: following.name, status: 'Active' }
  }

  const doneCount = next.filter((item) => item.status === 'Done').length
  const completed = !following
  const stage = completed ? 'Completed' : following.name

  return {
    milestones: next,
    progress: completed ? 100 : clampProgress((doneCount / next.length) * 100),
    stage,
    completed,
  }
}

export function nextTaskStatus(status: ExecutionTaskStatus): ExecutionTaskStatus {
  const index = taskBoardColumns.indexOf(status as (typeof taskBoardColumns)[number])
  if (index < 0) return 'To Do'
  return taskBoardColumns[Math.min(index + 1, taskBoardColumns.length - 1)] ?? 'To Do'
}

export function canCompleteTask({
  evidenceRequired,
  evidenceCount,
}: {
  evidenceRequired: boolean
  evidenceCount: number
}): boolean {
  return !evidenceRequired || evidenceCount > 0
}

export function taskProgressForStatus(
  status: ExecutionTaskStatus,
  currentProgress: number,
): number {
  if (status === 'Done') return 100
  if (status === 'Review') return Math.max(currentProgress, 80)
  if (status === 'In Progress') return Math.max(currentProgress, 25)
  return clampProgress(currentProgress)
}

export function commercialSourceAlreadyOrdered(
  orders: Array<{ requestId: string; quotationId?: string; invoiceId?: string }>,
  source: { requestId: string; quotationId: string; invoiceId: string },
): boolean {
  return orders.some(
    (order) =>
      order.invoiceId === source.invoiceId ||
      order.quotationId === source.quotationId ||
      order.requestId === source.requestId,
  )
}

export function canCompleteOrderWithDeliverables(
  deliverables: Array<{
    orderId: string
    approvalMode: 'Supervisor approval' | 'Client approval' | 'No approval'
    status: 'Under Review' | 'Approved' | 'Rejected'
  }>,
  orderId: string,
): boolean {
  return deliverables
    .filter((item) => item.orderId === orderId && item.approvalMode !== 'No approval')
    .every((item) => item.status === 'Approved')
}
