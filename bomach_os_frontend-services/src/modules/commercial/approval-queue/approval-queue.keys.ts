import type { ApprovalQueueFilters } from './approval-queue.types'

export const approvalQueueKeys = {
  all: ['commercial', 'approval-queue'] as const,
  lists: () => [...approvalQueueKeys.all, 'list'] as const,
  list: (filters: ApprovalQueueFilters) => [...approvalQueueKeys.lists(), filters] as const,
  stats: () => [...approvalQueueKeys.all, 'stats'] as const,
  choices: () => [...approvalQueueKeys.all, 'choices'] as const,
}
