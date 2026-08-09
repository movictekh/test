import { apiClient } from '@/shared/api/api-client'

import {
  mapWorkflowRule,
  mapWorkflowRuleChoice,
  mapWorkflowRuleRecipients,
  mapWorkflowRules,
} from './workflow-rules.mapper'
import type {
  SaveWorkflowRuleInput,
  WorkflowAutomationRule,
  WorkflowRuleChoice,
  WorkflowRuleRecipient,
} from './workflow-rules.types'

function payload(input: SaveWorkflowRuleInput) {
  return {
    name: input.name,
    description: input.description,
    trigger_event: input.triggerEvent,
    conditions: input.conditions,
    action_type: input.actionType,
    action_config: input.actionConfig,
    is_active: input.active,
  }
}

export const workflowRulesApi = {
  async list(): Promise<WorkflowAutomationRule[]> {
    return mapWorkflowRules(await apiClient.get<unknown>('/workflow-rules/?limit=100&offset=0'))
  },

  async triggerChoices(): Promise<WorkflowRuleChoice[]> {
    const response = await apiClient.get<unknown[]>('/workflow-rules/choices/triggers')
    return response.map(mapWorkflowRuleChoice)
  },

  async actionChoices(): Promise<WorkflowRuleChoice[]> {
    const response = await apiClient.get<unknown[]>('/workflow-rules/choices/actions')
    return response.map(mapWorkflowRuleChoice)
  },

  async recipients(search = ''): Promise<WorkflowRuleRecipient[]> {
    const query = new URLSearchParams({
      is_active: 'true',
      limit: '100',
      offset: '0',
    })
    if (search.trim()) query.set('search', search.trim())

    return mapWorkflowRuleRecipients(
      await apiClient.get<unknown>(`/employees/employees?${query.toString()}`),
    )
  },

  async create(input: SaveWorkflowRuleInput): Promise<WorkflowAutomationRule> {
    return mapWorkflowRule(await apiClient.post<unknown>('/workflow-rules/', payload(input)))
  },

  async update(input: SaveWorkflowRuleInput): Promise<WorkflowAutomationRule> {
    if (!input.id) throw new Error('Workflow Rule id is required for update.')

    return mapWorkflowRule(
      await apiClient.put<unknown>(`/workflow-rules/${input.id}`, payload(input)),
    )
  },

  async deactivate(ruleId: number): Promise<void> {
    await apiClient.delete(`/workflow-rules/${ruleId}`)
  },
}
