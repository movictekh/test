import type { ApprovalRequestFilters } from './approval.types'

export const approvalKeys = {
  all: ['commercial', 'approvals'] as const,
  requestLists: () => [...approvalKeys.all, 'requests', 'list'] as const,
  requestList: (filters: ApprovalRequestFilters) =>
    [...approvalKeys.requestLists(), filters] as const,
  requestDetails: () => [...approvalKeys.all, 'requests', 'detail'] as const,
  requestDetail: (id: number) => [...approvalKeys.requestDetails(), id] as const,
  summary: () => [...approvalKeys.all, 'summary'] as const,
  flowLists: () => [...approvalKeys.all, 'flows', 'list'] as const,
  activeFlows: () => [...approvalKeys.flowLists(), 'active'] as const,
  flowDetails: () => [...approvalKeys.all, 'flows', 'detail'] as const,
  flowDetail: (id: number) => [...approvalKeys.flowDetails(), id] as const,
  actionTypes: () => [...approvalKeys.all, 'action-types'] as const,
}
