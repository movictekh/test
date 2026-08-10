import { queryOptions } from '@tanstack/react-query'
import { approvalApi } from './approval.api'
import { approvalKeys } from './approval.keys'
import type { ApprovalRequestFilters } from './approval.types'

export const approvalQueries = {
  requestList: (filters: ApprovalRequestFilters) =>
    queryOptions({
      queryKey: approvalKeys.requestList(filters),
      queryFn: () => approvalApi.listRequests(filters),
      placeholderData: (previousData) => previousData,
      staleTime: 15_000,
    }),
  requestDetail: (id: number) =>
    queryOptions({
      queryKey: approvalKeys.requestDetail(id),
      queryFn: () => approvalApi.requestDetail(id),
      staleTime: 10_000,
    }),
  summary: () =>
    queryOptions({
      queryKey: approvalKeys.summary(),
      queryFn: () => approvalApi.summary(),
      staleTime: 20_000,
    }),
  activeFlows: () =>
    queryOptions({
      queryKey: approvalKeys.activeFlows(),
      queryFn: () => approvalApi.activeFlows(),
      staleTime: 60_000,
    }),
  flowDetail: (id: number) =>
    queryOptions({
      queryKey: approvalKeys.flowDetail(id),
      queryFn: () => approvalApi.flowDetail(id),
      staleTime: 60_000,
    }),
  actionTypes: () =>
    queryOptions({
      queryKey: approvalKeys.actionTypes(),
      queryFn: () => approvalApi.actionTypes(),
      staleTime: 300_000,
    }),
}
