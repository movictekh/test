import { IconFilePlus, IconPlus, IconSearch } from '@tabler/icons-react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from '@tanstack/react-router'
import { useCallback, useEffect, useMemo, useState } from 'react'

import { useAuth } from '@/app/auth'
import { SectionLoadingState } from '@/app/loading/SectionLoadingState'
import { hasPermission, PERMISSIONS } from '@/app/permissions'
import { presentError } from '@/shared/errors'
import { formatCurrency } from '@/shared/lib/formatters'
import type { AppSectionSearch } from '@/routes/app/$section'
import { withOptionalSearchValue, withoutSearchKeys } from '@/shared/navigation/search-state'
import { ErrorState, useToast } from '@/shared/ui'
import { EmptyState } from '@/shared/ui/empty-state'
import {
  CompactActionButton,
  CompactPageToolbar,
  ModulePageFrame,
  ModulePageStatus,
} from '@/shared/ui/module-controls'

import { serviceRequestsApi } from '../api/service-requests.api'
import { serviceRequestKeys } from '../api/service-requests.keys'
import { serviceRequestQueries } from '../api/service-requests.queries'
import type {
  CreateServiceRequestActivityInput,
  CreateServiceRequestAttachmentInput,
  CreateServiceRequestInput,
  UpdateServiceRequestInput,
} from '../api/service-requests.types'
import { CreateServiceRequestLiveWorkspace } from '../workspaces/CreateServiceRequestLiveWorkspace'
import { ServiceRequestDetailWorkspace } from '../workspaces/ServiceRequestDetailWorkspace'
import '../styles/commercial.css'

function statusClass(status: string) {
  if (status === 'rejected') return 'commercial-pill-gray'
  if (status === 'quoted' || status === 'converted') return 'commercial-pill-green'
  if (status === 'awaiting_client' || status === 'site_assessment') {
    return 'commercial-pill-yellow'
  }
  return 'commercial-pill-blue'
}

const REQUEST_SUMMARY_CARDS = [
  ['New / unreviewed', 'newCount'],
  ['Site assessment required', 'siteAssessment'],
  ['Awaiting client information', 'awaitingClient'],
  ['Total Requests', 'total'],
] as const

function withoutRequestSearch(previous: AppSectionSearch) {
  const next = { ...previous }
  delete next.request
  return next
}

export function ServiceRequestsLivePage({ recordSearch }: { recordSearch: AppSectionSearch }) {
  const { user } = useAuth()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const toast = useToast()
  const [createOpen, setCreateOpen] = useState(false)
  const [searchDraft, setSearchDraft] = useState(recordSearch.search ?? '')
  const [syncedSearch, setSyncedSearch] = useState(recordSearch.search ?? '')

  const selectedRequestId = recordSearch.request ? Number(recordSearch.request) : null
  const page = recordSearch.page ?? 1

  const filters = useMemo(
    () => ({
      ...(recordSearch.search ? { search: recordSearch.search } : {}),
      ...(recordSearch.status ? { status: recordSearch.status } : {}),
      ...(recordSearch.priority ? { priority: recordSearch.priority } : {}),
      ...(recordSearch.branch ? { branchId: Number(recordSearch.branch) } : {}),
      ...(recordSearch.service ? { serviceId: Number(recordSearch.service) } : {}),
      page,
      limit: 10,
    }),
    [
      page,
      recordSearch.branch,
      recordSearch.priority,
      recordSearch.search,
      recordSearch.service,
      recordSearch.status,
    ],
  )

  const listQuery = useQuery(serviceRequestQueries.list(filters))
  const summaryQuery = useQuery(serviceRequestQueries.summary())
  const choicesQuery = useQuery(serviceRequestQueries.choices())
  const clientsQuery = useQuery(serviceRequestQueries.clients())
  const servicesQuery = useQuery(serviceRequestQueries.services())

  const employeesQuery = useQuery({
    ...serviceRequestQueries.employees(),
    enabled: hasPermission(user, PERMISSIONS.employeesList),
  })

  const detailQuery = useQuery({
    ...serviceRequestQueries.detail(selectedRequestId ?? 0),
    enabled: Boolean(selectedRequestId) && hasPermission(user, PERMISSIONS.serviceRequestsView),
  })

  const invalidate = async (requestId?: number) => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: serviceRequestKeys.lists() }),
      queryClient.invalidateQueries({ queryKey: serviceRequestKeys.summary() }),
      ...(requestId
        ? [
            queryClient.invalidateQueries({
              queryKey: serviceRequestKeys.detail(requestId),
            }),
          ]
        : []),
    ])
  }

  const createMutation = useMutation({
    mutationFn: async ({
      input,
      attachments,
    }: {
      input: CreateServiceRequestInput
      attachments: CreateServiceRequestAttachmentInput[]
    }) => {
      const request = await serviceRequestsApi.create(input)
      const attachmentFailures: CreateServiceRequestAttachmentInput[] = []

      for (const attachment of attachments) {
        try {
          await serviceRequestsApi.addAttachment(request.id, attachment)
        } catch {
          attachmentFailures.push(attachment)
        }
      }

      return { request, attachmentFailures }
    },
    onSuccess: async ({ request, attachmentFailures }) => {
      await invalidate(request.id)
      setCreateOpen(false)
      toast.success(`Request ${request.requestNumber} created`)
      if (attachmentFailures.length > 0) {
        toast.warning('Some documents could not be attached', {
          description: 'Open the request to retry the failed documents.',
        })
      }
      await navigate({
        to: '/app/$section',
        params: { section: 'service-requests' },
        search: (previous) => ({
          ...previous,
          request: String(request.id),
        }),
      })
    },
    onError: (error) => {
      const presented = presentError(error, 'form-submit')
      toast.error('Service Request could not be created', {
        description: presented.message,
      })
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({ requestId, input }: { requestId: number; input: UpdateServiceRequestInput }) =>
      serviceRequestsApi.update(requestId, input),
    onSuccess: async (request) => {
      await invalidate(request.id)
      toast.success('Service Request updated')
    },
    onError: (error) => {
      toast.error('Service Request could not be updated', {
        description: presentError(error, 'background-action').message,
      })
    },
  })

  const activityMutation = useMutation({
    mutationFn: ({
      requestId,
      input,
    }: {
      requestId: number
      input: CreateServiceRequestActivityInput
    }) => serviceRequestsApi.addActivity(requestId, input),
    onSuccess: async (_, variables) => {
      await invalidate(variables.requestId)
      toast.success('Activity recorded')
    },
    onError: (error) => {
      toast.error('Activity could not be recorded', {
        description: presentError(error, 'background-action').message,
      })
    },
  })

  const attachmentMutation = useMutation({
    mutationFn: ({
      requestId,
      input,
    }: {
      requestId: number
      input: CreateServiceRequestAttachmentInput
    }) => serviceRequestsApi.addAttachment(requestId, input),
    onSuccess: async (_, variables) => {
      await invalidate(variables.requestId)
      toast.success('Attachment added')
    },
    onError: (error) => {
      toast.error('Attachment could not be added', {
        description: presentError(error, 'background-action').message,
      })
    },
  })

  const setSearch = useCallback(
    (patch: Partial<AppSectionSearch>) => {
      void navigate({
        to: '/app/$section',
        params: { section: 'service-requests' },
        search: (previous) => ({
          ...withoutSearchKeys(previous, Object.keys(patch) as Array<keyof AppSectionSearch>),
          ...patch,
          page:
            patch.page ??
            (Object.keys(patch).some((key) => key !== 'page') ? 1 : (previous.page ?? 1)),
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
        params: { section: 'service-requests' },
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
      params: { section: 'service-requests' },
      search: (previous) =>
        withoutSearchKeys(previous, ['search', 'status', 'priority', 'branch', 'service', 'page']),
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

  if (
    listQuery.isPending ||
    choicesQuery.isPending ||
    clientsQuery.isPending ||
    servicesQuery.isPending
  ) {
    return <SectionLoadingState section="service-requests" />
  }

  if (listQuery.isError || choicesQuery.isError || clientsQuery.isError || servicesQuery.isError) {
    const error = listQuery.error ?? choicesQuery.error ?? clientsQuery.error ?? servicesQuery.error
    const presented = presentError(error, 'page-load')

    return (
      <ModulePageStatus title="Service Requests" breadcrumb="Commercial flow / Requests">
        <ErrorState
          title={presented.title}
          description={presented.message}
          onRetry={() => {
            void listQuery.refetch()
            void choicesQuery.refetch()
            void clientsQuery.refetch()
            void servicesQuery.refetch()
          }}
        />
      </ModulePageStatus>
    )
  }

  const requests = listQuery.data.items
  const choices = choicesQuery.data
  const services = servicesQuery.data
  const hasActiveFilters =
    Boolean(recordSearch.search) ||
    Boolean(recordSearch.status) ||
    Boolean(recordSearch.priority) ||
    Boolean(recordSearch.branch) ||
    Boolean(recordSearch.service)
  const totalPages = Math.max(1, Math.ceil(listQuery.data.count / 10))
  const recordCountLabel = `${listQuery.data.count} ${listQuery.data.count === 1 ? 'request' : 'requests'}`
  const branches = Array.from(
    new Map(
      services.flatMap((service) =>
        service.activeBranches.map((branch) => [branch.id, branch] as const),
      ),
    ).values(),
  )

  return (
    <ModulePageFrame
      header={
        <CompactPageToolbar
          title="Service Requests"
          breadcrumb="Commercial flow / Requests"
          secondaryAction={
            <CompactActionButton
              disabled={!hasPermission(user, PERMISSIONS.serviceRequestsCreate)}
              locked={!hasPermission(user, PERMISSIONS.serviceRequestsCreate)}
              onClick={() => setCreateOpen(true)}
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
        <section className="commercial-kgrid commercial-kgrid-4" aria-label="Request summary">
          {summaryQuery.isPending ? (
            <article className="commercial-kpi">
              <div className="commercial-kpi-label">Loading summary...</div>
            </article>
          ) : summaryQuery.isError ? (
            <article className="commercial-kpi">
              <div className="commercial-kpi-label">Summary unavailable</div>
              <div className="commercial-kpi-note">The request register is still available.</div>
            </article>
          ) : (
            REQUEST_SUMMARY_CARDS.map(([label, key]) => (
              <article className="commercial-kpi" key={label}>
                <div className="commercial-kpi-label">{label}</div>
                <div className="commercial-kpi-value">{summaryQuery.data[key]}</div>
              </article>
            ))
          )}
        </section>

        <section className="commercial-card">
          <header className="commercial-card-header">
            <div>
              <h2>Service Request Register</h2>
              <p>Live commercial requests across your current workspace</p>
            </div>
            <div className="commercial-card-header-actions">
              <span className="commercial-count">{recordCountLabel}</span>
              {listQuery.isFetching ? <span className="commercial-count">Refreshing…</span> : null}
              <CompactActionButton
                tone="primary"
                disabled={!hasPermission(user, PERMISSIONS.serviceRequestsCreate)}
                locked={!hasPermission(user, PERMISSIONS.serviceRequestsCreate)}
                onClick={() => setCreateOpen(true)}
              >
                <IconFilePlus size={14} />
                New Request
              </CompactActionButton>
            </div>
          </header>

          <div className="commercial-filters">
            <label className="commercial-search">
              <IconSearch size={14} aria-hidden="true" />
              <input
                value={searchDraft}
                onChange={(event) => setSearchDraft(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key !== 'Enter') return
                  event.preventDefault()
                  if (searchDraft === (recordSearch.search ?? '')) return
                  setSearchValue('search', searchDraft)
                }}
                placeholder="Search request, client, service or contact"
              />
            </label>

            <select
              value={recordSearch.status ?? ''}
              onChange={(event) => setSearchValue('status', event.target.value)}
            >
              <option value="">All statuses</option>
              {choices.statuses.map((item) => (
                <option key={item.value} value={item.value}>
                  {item.label}
                </option>
              ))}
            </select>

            <select
              value={recordSearch.priority ?? ''}
              onChange={(event) => setSearchValue('priority', event.target.value)}
            >
              <option value="">All priorities</option>
              {choices.priorities.map((item) => (
                <option key={item.value} value={item.value}>
                  {item.label}
                </option>
              ))}
            </select>

            <select
              value={recordSearch.branch ?? ''}
              onChange={(event) => setSearchValue('branch', event.target.value)}
            >
              <option value="">All branches</option>
              {branches.map((branch) => (
                <option key={branch.id} value={branch.id}>
                  {branch.name}
                </option>
              ))}
            </select>

            <select
              value={recordSearch.service ?? ''}
              onChange={(event) => setSearchValue('service', event.target.value)}
            >
              <option value="">All services</option>
              {services.map((service) => (
                <option key={service.id} value={service.id}>
                  {service.name}
                </option>
              ))}
            </select>
          </div>

          {requests.length === 0 ? (
            <EmptyState
              title={
                hasActiveFilters
                  ? 'No service requests match the current filters'
                  : 'No service requests yet'
              }
              description={
                hasActiveFilters
                  ? 'Try adjusting or clearing the search and filter settings to bring matching requests back into view.'
                  : 'Service requests will appear here after the first request is created.'
              }
              action={
                hasActiveFilters ? (
                  <button type="button" className="commercial-btn" onClick={clearFilters}>
                    Clear filters
                  </button>
                ) : undefined
              }
            />
          ) : (
            <div className="commercial-table-wrap">
              <table className="commercial-table">
                <thead>
                  <tr>
                    <th>Request</th>
                    <th>Client</th>
                    <th>Service</th>
                    <th>Source</th>
                    <th>Estimate</th>
                    <th>Status</th>
                    <th>Owner</th>
                    <th>Next</th>
                    <th aria-label="Actions" />
                  </tr>
                </thead>
                <tbody>
                  {requests.map((request) => (
                    <tr key={request.id}>
                      <td>
                        <b>{request.requestNumber}</b>
                        <small>
                          {new Date(request.createdAt).toLocaleDateString('en-GB')} ·{' '}
                          {request.branchName || 'No branch'}
                        </small>
                      </td>
                      <td>
                        <b>{request.clientName}</b>
                        <small>{request.customerType}</small>
                      </td>
                      <td>
                        <b>{request.serviceName}</b>
                        <small>{request.subserviceName || '—'}</small>
                      </td>
                      <td>{request.source}</td>
                      <td>
                        <b>{formatCurrency(request.estimatedValue || request.budget || 0)}</b>
                      </td>
                      <td>
                        <span className={`commercial-pill ${statusClass(request.status)}`}>
                          {request.statusDisplay}
                        </span>
                      </td>
                      <td>{request.ownerName || 'Unassigned'}</td>
                      <td>
                        <span
                          className="commercial-table-truncate commercial-table-truncate--next"
                          title={request.nextAction || '—'}
                        >
                          {request.nextAction || '—'}
                        </span>
                      </td>
                      <td>
                        <button
                          type="button"
                          className="commercial-btn commercial-btn-small"
                          disabled={!hasPermission(user, PERMISSIONS.serviceRequestsView)}
                          onClick={() =>
                            void navigate({
                              to: '/app/$section',
                              params: { section: 'service-requests' },
                              search: (previous) => ({
                                ...previous,
                                request: String(request.id),
                              }),
                            })
                          }
                        >
                          Open
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
              <span className="commercial-table-pagination-count">{recordCountLabel}</span>
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

      {createOpen ? (
        <CreateServiceRequestLiveWorkspace
          clients={clientsQuery.data}
          services={services}
          choices={choices}
          saving={createMutation.isPending}
          onClose={() => setCreateOpen(false)}
          onSubmit={(input, attachments) => createMutation.mutateAsync({ input, attachments })}
        />
      ) : null}

      {selectedRequestId && detailQuery.isPending ? (
        <div className="commercial-modal-backdrop">
          <section className="commercial-modal">
            <div className="commercial-empty">Loading Request 360...</div>
          </section>
        </div>
      ) : null}

      {selectedRequestId && detailQuery.isError ? (
        <div className="commercial-modal-backdrop">
          <section className="commercial-modal">
            <EmptyState
              title="Request could not be opened"
              description={presentError(detailQuery.error, 'section-load').message}
            />
            <footer className="commercial-modal-footer">
              <button
                type="button"
                className="commercial-btn"
                onClick={() =>
                  void navigate({
                    to: '/app/$section',
                    params: { section: 'service-requests' },
                    search: (previous) => withoutRequestSearch(previous),
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
        <ServiceRequestDetailWorkspace
          request={detailQuery.data}
          choices={choices}
          employees={employeesQuery.data ?? []}
          saving={updateMutation.isPending}
          activitySaving={activityMutation.isPending}
          attachmentSaving={attachmentMutation.isPending}
          onClose={() =>
            void navigate({
              to: '/app/$section',
              params: { section: 'service-requests' },
              search: (previous) => withoutRequestSearch(previous),
            })
          }
          onUpdate={(input) =>
            updateMutation.mutate({
              requestId: detailQuery.data.id,
              input,
            })
          }
          onActivity={(input) =>
            activityMutation.mutate({
              requestId: detailQuery.data.id,
              input,
            })
          }
          onAttachment={(input) =>
            attachmentMutation.mutate({
              requestId: detailQuery.data.id,
              input,
            })
          }
          onPrepareQuotation={() =>
            void navigate({
              to: '/app/$section',
              params: { section: 'quotations' },
              search: { request: String(detailQuery.data.id) },
            })
          }
        />
      ) : null}
    </ModulePageFrame>
  )
}
