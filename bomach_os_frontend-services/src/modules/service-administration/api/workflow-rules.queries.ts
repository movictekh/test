import { queryOptions } from '@tanstack/react-query'

import { workflowRulesApi } from './workflow-rules.api'

export const workflowRuleKeys = {
  all: ['service-administration', 'workflow-rules'] as const,
  list: () => [...workflowRuleKeys.all, 'list'] as const,
  triggers: () => [...workflowRuleKeys.all, 'choices', 'triggers'] as const,
  actions: () => [...workflowRuleKeys.all, 'choices', 'actions'] as const,
  recipients: (search: string) => [...workflowRuleKeys.all, 'recipients', { search }] as const,
}

export const workflowRuleQueries = {
  list: () =>
    queryOptions({
      queryKey: workflowRuleKeys.list(),
      queryFn: () => workflowRulesApi.list(),
      staleTime: 30_000,
    }),

  triggers: () =>
    queryOptions({
      queryKey: workflowRuleKeys.triggers(),
      queryFn: () => workflowRulesApi.triggerChoices(),
      staleTime: 5 * 60_000,
    }),

  actions: () =>
    queryOptions({
      queryKey: workflowRuleKeys.actions(),
      queryFn: () => workflowRulesApi.actionChoices(),
      staleTime: 5 * 60_000,
    }),

  recipients: (search = '') =>
    queryOptions({
      queryKey: workflowRuleKeys.recipients(search),
      queryFn: () => workflowRulesApi.recipients(search),
      staleTime: 60_000,
    }),
}
