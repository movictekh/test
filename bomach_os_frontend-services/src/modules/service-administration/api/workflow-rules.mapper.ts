import type {
  WorkflowAutomationRule,
  WorkflowRuleRecipient,
  WorkflowRuleChoice,
  WorkflowRuleCondition,
} from './workflow-rules.types'

type JsonRecord = Record<string, unknown>

function record(value: unknown): JsonRecord {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
    ? (value as JsonRecord)
    : {}
}

function text(value: unknown, fallback = ''): string {
  return typeof value === 'string' ? value : fallback
}

function number(value: unknown, fallback = 0): number {
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : fallback
}

function rows(payload: unknown): unknown[] {
  if (Array.isArray(payload)) return payload
  const root = record(payload)
  if (Array.isArray(root.items)) return root.items
  if (Array.isArray(root.results)) return root.results
  return []
}

export function mapWorkflowRuleChoice(payload: unknown): WorkflowRuleChoice {
  const value = record(payload)
  return {
    value: text(value.value),
    label: text(value.label, text(value.value)),
  }
}

export function mapWorkflowRules(payload: unknown): WorkflowAutomationRule[] {
  return rows(payload).map((item) => {
    const value = record(item)

    return {
      id: number(value.id),
      name: text(value.name),
      description: text(value.description),
      triggerEvent: text(value.trigger_event),
      conditions: Array.isArray(value.conditions)
        ? (value.conditions as WorkflowRuleCondition[])
        : [],
      actionType: text(value.action_type),
      actionConfig: record(value.action_config),
      active: value.is_active === true,
      createdByName: text(value.created_by_name),
      executionCount: number(value.execution_count),
      createdAt: text(value.created_at),
    }
  })
}

export function mapWorkflowRule(payload: unknown): WorkflowAutomationRule {
  const value = record(payload)

  return {
    id: number(value.id),
    name: text(value.name),
    description: text(value.description),
    triggerEvent: text(value.trigger_event),
    conditions: Array.isArray(value.conditions)
      ? (value.conditions as WorkflowRuleCondition[])
      : [],
    actionType: text(value.action_type),
    actionConfig: record(value.action_config),
    active: value.is_active === true,
    createdByName: text(value.created_by_name),
    executionCount: number(value.execution_count),
    createdAt: text(value.created_at),
  }
}

export function mapWorkflowRuleRecipients(payload: unknown): WorkflowRuleRecipient[] {
  return rows(payload).map((item) => {
    const value = record(item)
    const firstName = text(value.first_name)
    const lastName = text(value.last_name)
    const fullName = `${firstName} ${lastName}`.trim()

    return {
      userId: number(value.user_id),
      employeeId: text(value.employee_id),
      name: fullName || text(value.email),
      email: text(value.email),
      designation: text(value.designation),
      roleName: text(value.role_name),
      branchName: text(value.branch_name),
    }
  })
}
