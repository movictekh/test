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
