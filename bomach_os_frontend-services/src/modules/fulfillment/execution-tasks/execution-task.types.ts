export type ExecutionTaskStatus = 'to_do' | 'in_progress' | 'review' | 'done' | 'cancelled'
export type ExecutionTaskPriority = 'normal' | 'high' | 'critical'

export interface ExecutionTask {
  id: number
  taskNumber: string
  orderId: number
  milestoneId: number | null
  title: string
  description: string
  instructions: string
  acceptanceCriteria: string
  status: ExecutionTaskStatus
  priority: ExecutionTaskPriority
  evidenceRequired: boolean
  ownerId: number | null
  assigneeIds: number[]
  dueDate: string | null
  completedAt: string | null
  createdById: number
  createdAt: string
  updatedAt: string
}

export interface PaginatedExecutionTasks {
  count: number
  items: ExecutionTask[]
}

export interface ExecutionTaskFilters {
  status?: ExecutionTaskStatus
  priority?: ExecutionTaskPriority
  milestoneId?: number
  search?: string
  page?: number
  limit?: number
}

export interface CreateExecutionTaskInput {
  milestoneId?: number | null
  title: string
  description?: string
  instructions?: string
  acceptanceCriteria?: string
  priority?: ExecutionTaskPriority
  evidenceRequired?: boolean
  ownerId?: number | null
  assigneeIds?: number[]
  dueDate?: string | null
}

export interface UpdateExecutionTaskInput {
  milestoneId?: number | null
  title?: string
  description?: string
  instructions?: string
  acceptanceCriteria?: string
  priority?: ExecutionTaskPriority
  evidenceRequired?: boolean
  ownerId?: number | null
  assigneeIds?: number[]
  dueDate?: string | null
  status?: ExecutionTaskStatus
}

export const executionTaskBoardStatuses: Array<{
  value: Exclude<ExecutionTaskStatus, 'cancelled'>
  label: string
}> = [
  { value: 'to_do', label: 'To Do' },
  { value: 'in_progress', label: 'In Progress' },
  { value: 'review', label: 'Review' },
  { value: 'done', label: 'Done' },
]

export const executionTaskPriorities: Array<{
  value: ExecutionTaskPriority
  label: string
}> = [
  { value: 'normal', label: 'Normal' },
  { value: 'high', label: 'High' },
  { value: 'critical', label: 'Critical' },
]
