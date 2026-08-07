export type FulfillmentSection = 'service-orders' | 'execution-tasks'

export type ServiceOrderStatus =
  | 'Pending Mobilisation'
  | 'Active'
  | 'Quality Review'
  | 'Awaiting Client'
  | 'Completed'
  | 'On Hold'
  | 'Cancelled'

export type MilestoneStatus = 'Done' | 'Active' | 'Pending'

export interface OrderMilestone {
  id: string
  name: string
  status: MilestoneStatus
}

export interface OrderActivity {
  id: string
  at: string
  title: string
  actor: string
  description: string
  visibility: 'Internal and client' | 'Internal only' | 'Management only'
}

export interface ServiceOrder {
  id: string
  requestId: string
  quotationId?: string
  invoiceId?: string
  client: string
  service: string
  division: string
  mode: string
  status: ServiceOrderStatus
  progress: number
  owner: string
  startAt: string
  dueAt: string
  value: number
  stage: string
  nextAction: string
  paymentReady: boolean
  milestones: OrderMilestone[]
  activities: OrderActivity[]
}

export type ExecutionTaskStatus = 'To Do' | 'In Progress' | 'Review' | 'Done' | 'Blocked'

export type ExecutionTaskPriority = 'Normal' | 'High' | 'Critical'

export interface ExecutionTask {
  id: string
  title: string
  orderId: string
  status: ExecutionTaskStatus
  owner: string
  dueAt: string
  priority: ExecutionTaskPriority
  evidenceRequired: boolean
  instructions: string
}

export interface FulfillmentSummary {
  activeOrders: number
  dueSoon: number
  awaitingClient: number
  completed: number
  openTasks: number
  blockedTasks: number
}

export interface FulfillmentWorkspace {
  summary: FulfillmentSummary
  orders: ServiceOrder[]
  tasks: ExecutionTask[]
}

export interface CreateServiceOrderInput {
  client: string
  service: string
  division: string
  value: number
  dueAt: string
  owner: string
  mode: string
  requestId?: string
  quotationId?: string
  invoiceId?: string
  paymentReady: boolean
  workflowStages: string[]
}

export interface UpdateServiceOrderInput {
  status: ServiceOrderStatus
  progress: number
  stage: string
  nextAction: string
}

export interface AddOrderUpdateInput {
  orderId: string
  type: string
  visibility: OrderActivity['visibility']
  note: string
  progress: number
  nextAction: string
}

export interface AddMilestoneInput {
  orderId: string
  name: string
}

export interface CreateExecutionTaskInput {
  title: string
  orderId: string
  owner: string
  dueAt: string
  priority: ExecutionTaskPriority
  evidenceRequired: boolean
  instructions: string
}

export interface UpdateExecutionTaskInput {
  action: 'advance'
}
