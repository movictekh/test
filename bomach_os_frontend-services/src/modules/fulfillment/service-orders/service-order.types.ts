export type ServiceOrderStatus =
  | 'pending_mobilisation'
  | 'active'
  | 'quality_review'
  | 'awaiting_client'
  | 'completed'
  | 'on_hold'
  | 'cancelled'

export type ServiceOrderPaymentStatus = 'unpaid' | 'partial' | 'paid'
export type ServiceOrderMilestoneStatus = 'pending' | 'active' | 'done'
export type ServiceOrderActivityVisibility = 'internal_client' | 'internal' | 'management'

export interface ServiceOrderMilestone {
  id: number
  workflowStageId: number | null
  name: string
  status: ServiceOrderMilestoneStatus
  sortOrder: number
  ownerRoleId: number | null
  clientVisible: boolean
  dueDate: string | null
  completedAt: string | null
  createdAt: string
  updatedAt: string
}

export interface ServiceOrderActivity {
  id: number
  activityType: string
  visibility: ServiceOrderActivityVisibility
  note: string
  progress: number | null
  nextAction: string
  createdById: number | null
  createdAt: string
}

export interface ServiceOrder {
  id: number
  orderNumber: string
  clientId: number
  serviceId: number
  serviceName: string
  quoteId: number | null
  quoteNumber: string
  serviceRequestId: number | null
  invoiceId: number | null
  description: string
  amount: number
  orderStatus: ServiceOrderStatus
  paymentStatus: ServiceOrderPaymentStatus
  validUntil: string
  dueDate: string | null
  progress: number
  stage: string
  nextAction: string
  startedAt: string | null
  completedAt: string | null
  createdAt: string
  updatedAt: string
  createdById: number
  assignedToId: number | null
  branchId: number | null
  taskCounts: Record<string, number>
  deliverableCounts: Record<string, number>
  milestones: ServiceOrderMilestone[]
  activities: ServiceOrderActivity[]
}

export interface PaginatedServiceOrders {
  count: number
  items: ServiceOrder[]
}

export interface ServiceOrderFilters {
  search?: string
  orderStatus?: string
  paymentStatus?: string
  invoiceId?: number
  page?: number
  limit?: number
}

export interface CreateServiceOrderFromInvoiceInput {
  invoiceId: number
  assignedToId?: number | null
  dueDate?: string
  description?: string
  nextAction: string
}

export interface UpdateServiceOrderInput {
  assignedToId?: number | null
  dueDate?: string | null
  description?: string
  nextAction?: string
}

export interface AddOrderActivityInput {
  activityType: string
  visibility: ServiceOrderActivityVisibility
  note: string
  nextAction?: string
}

export interface AddOrderMilestoneInput {
  name: string
  sortOrder: number
  clientVisible?: boolean
  dueDate?: string | null
}

export interface EmployeeOption {
  id: number
  userId: number
  name: string
  employeeId: string
  designation: string
  branchName: string
  active: boolean
}

export const operationalOrderStatuses: Array<{
  value: ServiceOrderStatus
  label: string
}> = [
  { value: 'pending_mobilisation', label: 'Pending Mobilisation' },
  { value: 'active', label: 'Active' },
  { value: 'quality_review', label: 'Quality Review' },
  { value: 'awaiting_client', label: 'Awaiting Client' },
  { value: 'on_hold', label: 'On Hold' },
]

export const allOrderStatuses: Array<{ value: ServiceOrderStatus; label: string }> = [
  ...operationalOrderStatuses,
  { value: 'completed', label: 'Completed' },
  { value: 'cancelled', label: 'Cancelled' },
]
