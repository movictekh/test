import { IconFilePlus, IconPlus, IconSearch } from '@tabler/icons-react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from '@tanstack/react-router'
import { useCallback, useEffect, useMemo, useState } from 'react'

import { useAuth } from '@/app/auth'
import { hasPermission, PERMISSIONS } from '@/app/permissions'
import type { AppSectionSearch } from '@/routes/app/$section'
import { presentError } from '@/shared/errors'
import { withOptionalSearchValue, withoutSearchKeys } from '@/shared/navigation/search-state'
import { DashboardSkeleton, ErrorState, useToast } from '@/shared/ui'
import { EmptyState } from '@/shared/ui/empty-state'
import {
  CompactActionButton,
  CompactPageToolbar,
  ModulePageFrame,
  ModulePageStatus,
} from '@/shared/ui/module-controls'

import { approvalApi } from '../approvals/approval.api'
import { approvalKeys } from '../approvals/approval.keys'
import { approvalQueries } from '../approvals/approval.queries'
import type { ApprovalRequest, CreateApprovalRequestInput } from '../approvals/approval.types'
import { ApprovalDetailLiveWorkspace } from '../workspaces/ApprovalDetailLiveWorkspace'
import { ApprovalRequestBuilderLiveWorkspace } from '../workspaces/ApprovalRequestBuilderLiveWorkspace'
import '../styles/commercial.css'

function statusClass(status: ApprovalRequest['status']) {
  if (status === 'approved') return 'commercial-pill-green'
  if (status === 'rejected' || status === 'cancelled') {
    return 'commercial-pill-gray'
  }
  return 'commercial-pill-yellow'
}

export function ApprovalsLivePage({ recordSearch }: { recordSearch: AppSectionSearch }) {
  const { user } = useAuth()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const toast = useToast()

  const page = recordSearch.page ?? 1
  const selectedApprovalId = recordSearch.approval ? Number(recordSearch.approval) : null

  const [builderOpen, setBuilderOpen] = useState(false)
  const [searchDraft, setSearchDraft] = useState(recordSearch.search ?? '')
  const [syncedSearch, setSyncedSearch] = useState(recordSearch.search ?? '')

  const filters = useMemo(
    () => ({
      ...(recordSearch.search ? { search: recordSearch.search } : {}),
      ...(recordSearch.status ? { status: recordSearch.status } : {}),
      ...(recordSearch.actionType ? { actionType: recordSearch.actionType } : {}),
      page,
      limit: 10,
    }),
    [page, recordSearch.actionType, recordSearch.search, recordSearch.status],
  )

  const listQuery = useQuery(approvalQueries.requestList(filters))
  const summaryQuery = useQuery(approvalQueries.summary())
  const actionTypesQuery = useQuery(approvalQueries.actionTypes())

  const detailQuery = useQuery({
    ...approvalQueries.requestDetail(selectedApprovalId ?? 0),
    enabled: Boolean(selectedApprovalId) && hasPermission(user, PERMISSIONS.approvalRequestsView),
  })

  const flowDetailQuery = useQuery({
    ...approvalQueries.flowDetail(detailQuery.data?.flowId ?? 0),
    enabled:
      Boolean(detailQuery.data?.flowId) && hasPermission(user, PERMISSIONS.approvalFlowsView),
  })

  const activeFlowsQuery = useQuery({
    ...approvalQueries.activeFlows(),
    enabled: builderOpen && hasPermission(user, PERMISSIONS.approvalFlowsList),
  })

  const invalidateRequests = async (requestId?: number) => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: approvalKeys.requestLists() }),
      queryClient.invalidateQueries({ queryKey: approvalKeys.summary() }),
      ...(requestId
        ? [
            queryClient.invalidateQueries({
              queryKey: approvalKeys.requestDetail(requestId),
            }),
          ]
        : []),
    ])
  }

  const createMutation = useMutation({
    mutationFn: (input: CreateApprovalRequestInput) => approvalApi.createRequest(input),
    onSuccess: async (request) => {
      await invalidateRequests(request.id)
      setBuilderOpen(false)
      toast.success(`Approval request ${request.approvalRequestId} created`)
      await navigate({
        to: '/app/$section',
        params: { section: 'approvals' },
        search: { approval: String(request.id) },
      })
    },
    onError: (error) => {
      toast.error('Approval request could not be created', {
        description: presentError(error, 'form-submit').message,
      })
    },
  })

  const approveMutation = useMutation({
    mutationFn: ({ requestId, comment }: { requestId: number; comment: string }) =>
      approvalApi.approve(requestId, comment),
    onSuccess: async (request) => {
      await invalidateRequests(request.id)
      toast.success(
        request.status === 'approved'
          ? 'Approval request completed'
          : `Step approved · Now on step ${request.currentStep} of ${request.totalSteps}`,
      )
    },
    onError: async (error) => {
      toast.error('Approval could not be recorded', {
        description: presentError(error, 'background-action').message,
      })
      if (selectedApprovalId) {
        await queryClient.invalidateQueries({
          queryKey: approvalKeys.requestDetail(selectedApprovalId),
        })
      }
    },
  })

  const rejectMutation = useMutation({
    mutationFn: ({ requestId, comment }: { requestId: number; comment: string }) =>
      approvalApi.reject(requestId, comment),
    onSuccess: async (request) => {
      await invalidateRequests(request.id)
      toast.success('Approval request rejected')
    },
    onError: async (error) => {
      toast.error('Rejection could not be recorded', {
        description: presentError(error, 'background-action').message,
      })
      if (selectedApprovalId) {
        await queryClient.invalidateQueries({
          queryKey: approvalKeys.requestDetail(selectedApprovalId),
        })
      }
    },
  })

  const cancelMutation = useMutation({
    mutationFn: (requestId: number) => approvalApi.cancel(requestId),
    onSuccess: async (_data, requestId) => {
      await invalidateRequests(requestId)
      toast.success('Approval request cancelled')
    },
    onError: async (error) => {
      toast.error('Approval request could not be cancelled', {
        description: presentError(error, 'background-action').message,
      })
      if (selectedApprovalId) {
        await queryClient.invalidateQueries({
          queryKey: approvalKeys.requestDetail(selectedApprovalId),
        })
      }
    },
  })

  const setSearch = useCallback(
    (patch: Partial<AppSectionSearch>) => {
      void navigate({
        to: '/app/$section',
        params: { section: 'approvals' },
        search: (previous) => ({
          ...withoutSearchKeys(previous, Object.keys(patch) as Array<keyof AppSectionSearch>),
          ...patch,
          ...(Object.prototype.hasOwnProperty.call(patch, 'page')
            ? patch.page
              ? { page: patch.page }
              : {}
            : Object.keys(patch).some((key) => key !== 'page')
              ? { page: 1 }
              : previous.page
                ? { page: previous.page }
                : {}),
        }),
        replace: true,
      })
    },
    [navigate],
  )

  const setSearchValue = useCallback(
    function <Key extends keyof AppSectionSearch>(
      key: Key,
      value: AppSectionSearch[Key] | '' | null,
    ) {
      void navigate({
        to: '/app/$section',
        params: { section: 'approvals' },
        search: (previous) => ({
          ...withoutSearchKeys(previous, [key]),
          ...withOptionalSearchValue<AppSectionSearch, Key>(key, value),
          page: 1,
        }),
        replace: true,
      })
    },
    [navigate],
  )

  const clearFilters = useCallback(() => {
    setSearchDraft('')
    void navigate({
      to: '/app/$section',
      params: { section: 'approvals' },
      search: (previous) =>
        withoutSearchKeys(previous, ['search', 'status', 'actionType', 'page']),
      replace: true,
    })
  }, [navigate])

  if ((recordSearch.search ?? '') !== syncedSearch) {
    setSyncedSearch(recordSearch.search ?? '')
    setSearchDraft(recordSearch.search ?? '')
  }

  useEffect(() => {
    if (searchDraft === (recordSearch.search ?? '')) return
    const timeoutId = window.setTimeout(() => {
      setSearchValue('search', searchDraft)
    }, 350)
    return () => window.clearTimeout(timeoutId)
  }, [recordSearch.search, searchDraft, setSearchValue])

  if (listQuery.isPending) {
    return (
      <ModulePageStatus title="Approvals" breadcrumb="Commercial flow / Approvals">
        <DashboardSkeleton />
      </ModulePageStatus>
    )
  }

  if (listQuery.isError) {
    const error = presentError(listQuery.error, 'page-load')
    return (
      <ModulePageStatus title="Approvals" breadcrumb="Commercial flow / Approvals">
        <ErrorState
          title={error.title}
          description={error.message}
          onRetry={() => void listQuery.refetch()}
        />
      </ModulePageStatus>
    )
  }

  const canCreate =
    hasPermission(user, PERMISSIONS.approvalRequestsCreate) &&
    hasPermission(user, PERMISSIONS.approvalFlowsList)
  const hasActiveFilters = Boolean(
    recordSearch.search || recordSearch.status || recordSearch.actionType,
  )
  const totalPages = Math.max(1, Math.ceil(listQuery.data.count / 10))
  const currentUserId =
    Number.isFinite(Number(user?.id)) && Number(user?.id) > 0 ? Number(user?.id) : null
  const busy = approveMutation.isPending || rejectMutation.isPending || cancelMutation.isPending

  return (
    <ModulePageFrame
      header={
        <CompactPageToolbar
          title="Approvals"
          breadcrumb="Commercial flow / Approvals"
          secondaryAction={
            <CompactActionButton
              disabled={!hasPermission(user, PERMISSIONS.serviceRequestsCreate)}
              locked={!hasPermission(user, PERMISSIONS.serviceRequestsCreate)}
              onClick={() =>
                void navigate({
                  to: '/app/$section',
                  params: { section: 'service-requests' },
                })
              }
            >
              <IconFilePlus size={14} />
              New Request
            </CompactActionButton>
          }
          primaryAction={
            <CompactActionButton
              tone="primary"
              onClick={() =>
                void navigate({
                  to: '/app/$section',
                  params: { section: 'service-catalogue' },
                })
              }
            >
              <IconPlus size={14} />
              Create Service
            </CompactActionButton>
          }
        />
      }
    >
      <main className="commercial-content">
        <section className="commercial-kgrid commercial-kgrid-4" aria-label="Approval summary">
          {summaryQuery.isPending ? (
            <article className="commercial-kpi">
              <div className="commercial-kpi-label">Loading summary...</div>
            </article>
          ) : summaryQuery.isError ? (
            <article className="commercial-kpi">
              <div className="commercial-kpi-label">Summary unavailable</div>
            </article>
          ) : (
            [
              ['Pending', summaryQuery.data.pending],
              ['Approved', summaryQuery.data.approved],
              ['Rejected', summaryQuery.data.rejected],
              ['Cancelled', summaryQuery.data.cancelled],
            ].map(([label, value]) => (
              <article className="commercial-kpi" key={label}>
                <div className="commercial-kpi-label">{label}</div>
                <div className="commercial-kpi-value">{value}</div>
              </article>
            ))
          )}
        </section>

        <section className="commercial-card">
          <header className="commercial-card-header">
            <div>
              <h2>Approval Request Queue</h2>
              <p>Multi-step operational and business approval requests</p>
            </div>
            <div className="commercial-card-header-actions">
              <span className="commercial-count">{listQuery.data.count} records</span>
              {listQuery.isFetching ? <span className="commercial-count">Refreshing…</span> : null}
              <CompactActionButton
                tone="primary"
                disabled={!canCreate}
                locked={!canCreate}
                onClick={() => setBuilderOpen(true)}
              >
                <IconPlus size={14} />
                New Approval Request
              </CompactActionButton>
            </div>
          </header>

          <div className="commercial-filters">
            <label className="commercial-search">
              <IconSearch size={14} />
              <input
                value={searchDraft}
                onChange={(event) => setSearchDraft(event.target.value)}
                placeholder="Search request ID, title or description"
              />
            </label>

            <select
              value={recordSearch.status ?? ''}
              onChange={(event) => setSearchValue('status', event.target.value)}
            >
              <option value="">All statuses</option>
              <option value="pending">Pending</option>
              <option value="approved">Approved</option>
              <option value="rejected">Rejected</option>
              <option value="cancelled">Cancelled</option>
            </select>

            <select
              value={recordSearch.actionType ?? ''}
              disabled={actionTypesQuery.isPending}
              onChange={(event) => setSearchValue('actionType', event.target.value)}
            >
              <option value="">All approval types</option>
              {(actionTypesQuery.data ?? []).map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>

            {hasActiveFilters ? (
              <button
                type="button"
                className="commercial-btn commercial-btn-small"
                onClick={clearFilters}
              >
                Clear Filters
              </button>
            ) : null}
          </div>

          {listQuery.data.items.length === 0 ? (
            <EmptyState
              title={
                hasActiveFilters
                  ? 'No approval requests match these filters'
                  : 'No approval requests yet'
              }
              description={
                hasActiveFilters
                  ? 'Change or clear the filters to review other approval requests.'
                  : 'Approval requests will appear here when they are created.'
              }
            />
          ) : (
            <div className="commercial-table-wrap">
              <table className="commercial-table">
                <thead>
                  <tr>
                    <th>Request</th>
                    <th>Type</th>
                    <th>Title</th>
                    <th>Requested By</th>
                    <th>Current Step</th>
                    <th>Progress</th>
                    <th>Created</th>
                    <th>Status</th>
                    <th aria-label="Actions" />
                  </tr>
                </thead>
                <tbody>
                  {listQuery.data.items.map((request) => (
                    <tr key={request.id}>
                      <td>
                        <b>{request.approvalRequestId}</b>
                        <small>{request.flowName}</small>
                      </td>
                      <td>{request.actionTypeDisplay}</td>
                      <td>{request.title}</td>
                      <td>{request.createdByName || '—'}</td>
                      <td>
                        {request.status === 'pending'
                          ? request.pendingStepName || `Step ${request.currentStep}`
                          : '—'}
                      </td>
                      <td>
                        {request.status === 'pending'
                          ? `${request.currentStep} / ${request.totalSteps}`
                          : `${request.totalSteps} / ${request.totalSteps}`}
                      </td>
                      <td>{new Date(request.createdAt).toLocaleDateString('en-GB')}</td>
                      <td>
                        <span className={`commercial-pill ${statusClass(request.status)}`}>
                          {request.statusDisplay}
                        </span>
                      </td>
                      <td>
                        <button
                          type="button"
                          className="commercial-btn commercial-btn-small"
                          disabled={!hasPermission(user, PERMISSIONS.approvalRequestsView)}
                          onClick={() =>
                            void navigate({
                              to: '/app/$section',
                              params: { section: 'approvals' },
                              search: (previous) => ({
                                ...previous,
                                approval: String(request.id),
                              }),
                            })
                          }
                        >
                          {request.status === 'pending' ? 'Review' : 'Open'}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <div className="commercial-table-pagination">
            <div className="commercial-table-pagination-summary">
              <span className="commercial-table-pagination-count">
                {listQuery.data.count} records
              </span>
              <span className="commercial-table-pagination-divider" aria-hidden="true" />
              <span>
                Page <b>{page}</b> of <b>{totalPages}</b>
              </span>
            </div>
            <div className="commercial-table-pagination-actions">
              <button
                type="button"
                className="commercial-btn commercial-btn-small"
                disabled={page <= 1}
                onClick={() => setSearch({ page: page - 1 })}
              >
                Previous
              </button>
              <button
                type="button"
                className="commercial-btn commercial-btn-small"
                disabled={page >= totalPages}
                onClick={() => setSearch({ page: page + 1 })}
              >
                Next
              </button>
            </div>
          </div>
        </section>
      </main>

      {builderOpen && activeFlowsQuery.isPending ? (
        <div className="commercial-modal-backdrop">
          <section className="commercial-modal">
            <div className="commercial-empty">Loading approval flows...</div>
          </section>
        </div>
      ) : null}

      {builderOpen && activeFlowsQuery.isError ? (
        <div className="commercial-modal-backdrop">
          <section className="commercial-modal">
            <EmptyState
              title="Approval flows could not be loaded"
              description={presentError(activeFlowsQuery.error, 'section-load').message}
            />
            <footer className="commercial-modal-footer">
              <button
                type="button"
                className="commercial-btn"
                onClick={() => setBuilderOpen(false)}
              >
                Close
              </button>
              <button
                type="button"
                className="commercial-btn commercial-btn-primary"
                onClick={() => void activeFlowsQuery.refetch()}
              >
                Retry
              </button>
            </footer>
          </section>
        </div>
      ) : null}

      {builderOpen && activeFlowsQuery.data && activeFlowsQuery.data.items.length === 0 ? (
        <div className="commercial-modal-backdrop">
          <section className="commercial-modal">
            <EmptyState
              title="No active approval flows"
              description="There are currently no active approval flows available for a new request."
            />
            <footer className="commercial-modal-footer">
              <button
                type="button"
                className="commercial-btn"
                onClick={() => setBuilderOpen(false)}
              >
                Close
              </button>
            </footer>
          </section>
        </div>
      ) : null}

      {builderOpen && activeFlowsQuery.data && activeFlowsQuery.data.items.length > 0 ? (
        <ApprovalRequestBuilderLiveWorkspace
          flows={activeFlowsQuery.data.items}
          saving={createMutation.isPending}
          onClose={() => setBuilderOpen(false)}
          onSubmit={(input) => createMutation.mutate(input)}
        />
      ) : null}

      {selectedApprovalId && detailQuery.isPending ? (
        <div className="commercial-modal-backdrop">
          <section className="commercial-modal">
            <div className="commercial-empty">Loading approval request...</div>
          </section>
        </div>
      ) : null}

      {selectedApprovalId && detailQuery.isError ? (
        <div className="commercial-modal-backdrop">
          <section className="commercial-modal">
            <EmptyState
              title="Approval request could not be opened"
              description={presentError(detailQuery.error, 'section-load').message}
            />
            <footer className="commercial-modal-footer">
              <button
                type="button"
                className="commercial-btn"
                onClick={() =>
                  void navigate({
                    to: '/app/$section',
                    params: { section: 'approvals' },
                    search: (previous) => withoutSearchKeys(previous, ['approval']),
                  })
                }
              >
                Close
              </button>
              <button
                type="button"
                className="commercial-btn commercial-btn-primary"
                onClick={() => void detailQuery.refetch()}
              >
                Retry
              </button>
            </footer>
          </section>
        </div>
      ) : null}

      {detailQuery.data ? (
        <ApprovalDetailLiveWorkspace
          key={`${detailQuery.data.id}-${detailQuery.data.currentStep}-${detailQuery.data.status}`}
          request={detailQuery.data}
          flow={flowDetailQuery.data ?? null}
          currentUserId={currentUserId}
          canApprove={hasPermission(user, PERMISSIONS.approvalRequestsApprove)}
          canReject={hasPermission(user, PERMISSIONS.approvalRequestsReject)}
          canCancel={hasPermission(user, PERMISSIONS.approvalRequestsCancel)}
          saving={busy}
          onClose={() =>
            void navigate({
              to: '/app/$section',
              params: { section: 'approvals' },
              search: (previous) => withoutSearchKeys(previous, ['approval']),
            })
          }
          onApprove={(comment) =>
            approveMutation.mutate({
              requestId: detailQuery.data.id,
              comment,
            })
          }
          onReject={(comment) =>
            rejectMutation.mutate({
              requestId: detailQuery.data.id,
              comment,
            })
          }
          onCancel={() => cancelMutation.mutate(detailQuery.data.id)}
        />
      ) : null}
    </ModulePageFrame>
  )
}
