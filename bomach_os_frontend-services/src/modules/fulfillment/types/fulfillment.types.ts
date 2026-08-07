export type FulfillmentSection = 'service-orders' | 'execution-tasks' | 'deliverables'

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

export interface TaskEvidence {
  id: string
  label: string
  fileName: string
  addedAt: string
  addedBy: string
}

export interface TaskActivity {
  id: string
  at: string
  title: string
  actor: string
  description: string
}

export interface ExecutionTask {
  id: string
  title: string
  orderId: string
  stageName: string
  status: ExecutionTaskStatus
  owner: string
  dueAt: string
  priority: ExecutionTaskPriority
  evidenceRequired: boolean
  instructions: string
  progress: number
  blockedReason?: string
  completedAt?: string
  evidence: TaskEvidence[]
  activities: TaskActivity[]
}

export type DeliverableStatus = 'Under Review' | 'Approved' | 'Rejected'
export type DeliverableType =
  | 'Report'
  | 'Drawing'
  | 'Survey Plan'
  | 'Certificate'
  | 'Legal Document'
  | 'Progress Evidence'
  | 'Handover File'
export interface Deliverable {
  id: string
  orderId: string
  title: string
  type: DeliverableType
  version: string
  owner: string
  status: DeliverableStatus
  clientVisible: boolean
  date: string
  approvalMode: 'Supervisor approval' | 'Client approval' | 'No approval'
  fileName: string
}
export interface CreateDeliverableInput {
  orderId: string
  title: string
  type: DeliverableType
  version: string
  clientVisible: boolean
  approvalMode: Deliverable['approvalMode']
  fileName: string
}
export interface DecideDeliverableInput {
  action: 'approve' | 'reject'
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
  deliverables: Deliverable[]
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
  action: 'advance' | 'save' | 'block' | 'unblock' | 'complete' | 'add-evidence' | 'add-activity'
  progress?: number
  owner?: string
  dueAt?: string
  priority?: ExecutionTaskPriority
  note?: string
  blockedReason?: string
  evidence?: {
    label: string
    fileName: string
  }
}

export interface CommercialOrderHandoffInput {
  requestId: string
  quotationId: string
  invoiceId: string
  client: string
  service: string
  division: string
  value: number
  dueAt: string
  owner: string
  mode: string
  paymentReady: boolean
  workflowStages: string[]
}
