export interface WorkflowRuleChoice {
  value: string
  label: string
}

export interface WorkflowRuleCondition {
  field: string
  operator: string
  value: string
}

export interface WorkflowAutomationRule {
  id: number
  name: string
  description: string
  triggerEvent: string
  conditions: WorkflowRuleCondition[]
  actionType: string
  actionConfig: Record<string, unknown>
  active: boolean
  createdByName: string
  executionCount: number
  createdAt: string
}

export interface WorkflowRuleRecipient {
  userId: number
  employeeId: string
  name: string
  email: string
  designation: string
  roleName: string
  branchName: string
}

export interface SaveWorkflowRuleInput {
  id?: number
  name: string
  description: string
  triggerEvent: string
  conditions: WorkflowRuleCondition[]
  actionType: string
  actionConfig: Record<string, unknown>
  active: boolean
}
