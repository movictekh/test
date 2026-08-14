import { IconFilePlus, IconPlus, IconRefresh, IconSearch } from '@tabler/icons-react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from '@tanstack/react-router'
import { useCallback, useEffect, useMemo, useState } from 'react'

import { useAuth } from '@/app/auth'
import { SectionLoadingState } from '@/app/loading/SectionLoadingState'
import { hasPermission, PERMISSIONS } from '@/app/permissions'
import type { AppSectionSearch } from '@/routes/app/$section'
import { presentError } from '@/shared/errors'
import { formatCurrency } from '@/shared/lib/formatters'
import { withOptionalSearchValue, withoutSearchKeys } from '@/shared/navigation/search-state'
import { ErrorState, useToast } from '@/shared/ui'
import { EmptyState } from '@/shared/ui/empty-state'
import {
  CompactActionButton,
  CompactPageToolbar,
  ModulePageFrame,
  ModulePageStatus,
} from '@/shared/ui/module-controls'

import {
  canApproveQueueItem,
  canRejectQueueItem,
} from '../approval-queue/approval-queue-capabilities'
import { approvalQueueApi } from '../approval-queue/approval-queue.api'
import { approvalQueueKeys } from '../approval-queue/approval-queue.keys'
import { approvalQueueQueries } from '../approval-queue/approval-queue.queries'
import type { ApprovalQueueItem, ApprovalQueueStatus } from '../approval-queue/approval-queue.types'
import { quotationKeys } from '../quotation/quotation.keys'
import { ApprovalQueueDetailLiveWorkspace } from '../workspaces/ApprovalQueueDetailLiveWorkspace'
import {
  CommercialRegisterHeader,
  CommercialSummaryGrid,
} from '../components/CommercialRegisterChrome'
import '../styles/commercial.css'

function statusClass(status: ApprovalQueueItem['status']) {
  if (status === 'approved') return 'commercial-pill-green'
  if (status === 'rejected') return 'commercial-pill-gray'
  return 'commercial-pill-yellow'
}

function oldestWaiting(days: number) {
  return `${days}d`
}

export function ApprovalsLivePage({ recordSearch }: { recordSearch: AppSectionSearch }) {
  const { user } = useAuth()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const toast = useToast()

  const page = recordSearch.page ?? 1
  const status: ApprovalQueueStatus =
    recordSearch.status === 'approved' || recordSearch.status === 'rejected'
      ? recordSearch.status
      : 'pending'

  const statusChoices = useMemo(
    () => [
      { value: 'pending', label: 'Pending' },
      { value: 'approved', label: 'Approved' },
      { value: 'rejected', label: 'Rejected' },
    ],
    [],
  )

  const [selectedItem, setSelectedItem] = useState<ApprovalQueueItem | null>(null)
  const [searchDraft, setSearchDraft] = useState(recordSearch.search ?? '')
  const [syncedSearch, setSyncedSearch] = useState(recordSearch.search ?? '')

  const filters = useMemo(
    () => ({
      status,
      ...(recordSearch.search ? { search: recordSearch.search } : {}),
      ...(recordSearch.source ? { source: recordSearch.source } : {}),
      ...(recordSearch.highValue ? { highValue: true } : {}),
      page,
      limit: 10,
    }),
    [page, recordSearch.highValue, recordSearch.search, recordSearch.source, status],
  )

  const listQuery = useQuery(approvalQueueQueries.list(filters))
  const statsQuery = useQuery(approvalQueueQueries.stats())
  const choicesQuery = useQuery(approvalQueueQueries.choices())

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

  const setHighValue = useCallback(
    (checked: boolean) => {
      void navigate({
        to: '/app/$section',
        params: { section: 'approvals' },
        search: (previous) => ({
          ...withoutSearchKeys(previous, ['highValue']),
          ...(checked ? { highValue: true } : {}),
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
        withoutSearchKeys(previous, ['search', 'status', 'source', 'highValue', 'page']),
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

  const invalidateQueue = async (item?: ApprovalQueueItem) => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: approvalQueueKeys.lists() }),
      queryClient.invalidateQueries({ queryKey: approvalQueueKeys.stats() }),
      ...(item?.source === 'quotation'
        ? [
            queryClient.invalidateQueries({
              queryKey: quotationKeys.lists(),
            }),
          ]
        : []),
    ])
  }

  const approveMutation = useMutation({
    mutationFn: (item: ApprovalQueueItem) => approvalQueueApi.approve(item),
    onSuccess: async (_result, item) => {
      await invalidateQueue(item)
      setSelectedItem(null)
      toast.success(
        item.source === 'quotation'
          ? 'Quotation approved and sent'
          : `${item.sourceDisplay} approved`,
      )
    },
    onError: async (error) => {
      toast.error('Approval could not be completed', {
        description: presentError(error, 'background-action').message,
      })
      await invalidateQueue(selectedItem ?? undefined)
    },
  })

  const rejectMutation = useMutation({
    mutationFn: ({ item, reason }: { item: ApprovalQueueItem; reason: string }) =>
      approvalQueueApi.reject(item, reason),
    onSuccess: async (_result, { item }) => {
      await invalidateQueue(item)
      setSelectedItem(null)
      toast.success(`${item.sourceDisplay} rejected`)
    },
    onError: async (error) => {
      toast.error('Rejection could not be completed', {
        description: presentError(error, 'background-action').message,
      })
      await invalidateQueue(selectedItem ?? undefined)
    },
  })

  const refresh = async () => {
    await Promise.all([listQuery.refetch(), statsQuery.refetch(), choicesQuery.refetch()])
    toast.success('Approval queue refreshed')
  }

  if (listQuery.isPending) {
    return <SectionLoadingState section="approvals" />
  }

  if (listQuery.isError) {
    const error = presentError(listQuery.error, 'page-load')
    return (
      <ModulePageStatus title="Approvals" breadcrumb="Governance / Approvals">
        <ErrorState
          title={error.title}
          description={error.message}
          onRetry={() => void listQuery.refetch()}
        />
      </ModulePageStatus>
    )
  }

  const totalPages = Math.max(1, Math.ceil(listQuery.data.count / 10))
  const hasActiveFilters = Boolean(
    recordSearch.search || recordSearch.source || recordSearch.highValue || recordSearch.status,
  )
  const saving = approveMutation.isPending || rejectMutation.isPending

  return (
    <ModulePageFrame
      header={
        <CompactPageToolbar
          title="Approvals"
          breadcrumb="Governance / Approvals"
          secondaryAction={
            <CompactActionButton
              disabled={!hasPermission(user, PERMISSIONS.serviceRequestsCreate)}
              locked={!hasPermission(user, PERMISSIONS.serviceRequestsCreate)}
              onClick={() =>
                void navigate({
                  to: '/app/$section',
                  params: { section: 'service-requests' },
                  search: { create: 'request' },
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
        <CommercialSummaryGrid
          ariaLabel="Approval summary"
          loading={statsQuery.isPending}
          error={statsQuery.isError}
          items={
            statsQuery.data
              ? [
                  { label: 'Pending approvals', value: statsQuery.data.pendingCount },
                  { label: 'High-value approvals', value: statsQuery.data.highValueCount },
                  {
                    label: 'Oldest waiting',
                    value: oldestWaiting(statsQuery.data.oldestWaitingDays),
                  },
                  { label: 'Approval SLA', value: `${statsQuery.data.slaPercent}%` },
                ]
              : []
          }
        />

        <section className="commercial-card">
          <CommercialRegisterHeader
            title="Approval & Escalation Queue"
            description="Review operational approvals across quotations, deliverables, and expenses."
            countLabel={`${listQuery.data.count} record${listQuery.data.count === 1 ? '' : 's'}`}
            refreshing={listQuery.isFetching || statsQuery.isFetching}
            action={
              <CompactActionButton
                onClick={() => void refresh()}
                disabled={listQuery.isFetching || statsQuery.isFetching}
              >
                <IconRefresh size={14} />
                Refresh
              </CompactActionButton>
            }
          />

          <div className="commercial-filters">
            <label className="commercial-search">
              <IconSearch size={14} />
              <input
                value={searchDraft}
                onChange={(event) => setSearchDraft(event.target.value)}
                placeholder="Search reference, subject, requester or approver"
              />
            </label>

            <select
              value={status}
              onChange={(event) => setSearchValue('status', event.target.value)}
            >
              {statusChoices.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>

            <select
              value={recordSearch.source ?? ''}
              onChange={(event) => setSearchValue('source', event.target.value)}
            >
              <option value="">All approval types</option>
              {(choicesQuery.data?.sources ?? []).map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>

            <select
              value={recordSearch.highValue ? 'high' : ''}
              onChange={(event) => setHighValue(event.target.value === 'high')}
            >
              <option value="">All values</option>
              <option value="high">High value only</option>
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
                hasActiveFilters ? 'No approvals match these filters' : 'No approvals are waiting'
              }
              description={
                hasActiveFilters
                  ? 'Change or clear the filters to review other approvals.'
                  : 'Operational approvals will appear here when action is required.'
              }
            />
          ) : (
            <div className="commercial-table-wrap">
              <table className="commercial-table">
                <thead>
                  <tr>
                    <th>Approval</th>
                    <th>Type</th>
                    <th>Subject</th>
                    <th>Requester</th>
                    <th>Approver</th>
                    <th>Amount</th>
                    <th>Created</th>
                    <th>Status</th>
                    <th aria-label="Actions" />
                  </tr>
                </thead>
                <tbody>
                  {listQuery.data.items.map((item) => (
                    <tr key={item.id}>
                      <td>
                        <b>{item.refNumber}</b>
                        <small>{item.id}</small>
                      </td>
                      <td>{item.sourceDisplay}</td>
                      <td>{item.subject}</td>
                      <td>{item.requesterName || '—'}</td>
                      <td>{item.approverName || '—'}</td>
                      <td>
                        <b>{item.amount == null ? '—' : formatCurrency(item.amount)}</b>
                      </td>
                      <td>{new Date(item.createdAt).toLocaleDateString('en-GB')}</td>
                      <td>
                        <span className={`commercial-pill ${statusClass(item.status)}`}>
                          {item.status.charAt(0).toUpperCase() + item.status.slice(1)}
                        </span>
                      </td>
                      <td>
                        <button
                          type="button"
                          className="commercial-btn commercial-btn-small"
                          onClick={() => setSelectedItem(item)}
                        >
                          {item.status === 'pending' ? 'Review' : 'Open'}
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

      {selectedItem ? (
        <ApprovalQueueDetailLiveWorkspace
          key={selectedItem.id}
          item={selectedItem}
          canApprove={canApproveQueueItem(user, selectedItem)}
          canReject={canRejectQueueItem(user, selectedItem)}
          saving={saving}
          onClose={() => setSelectedItem(null)}
          onApprove={() => approveMutation.mutate(selectedItem)}
          onReject={(reason) => rejectMutation.mutate({ item: selectedItem, reason })}
        />
      ) : null}
    </ModulePageFrame>
  )
}
