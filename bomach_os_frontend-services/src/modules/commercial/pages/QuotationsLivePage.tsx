import { IconFilePlus, IconPlus, IconSearch } from '@tabler/icons-react'
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

import { serviceRequestKeys } from '../api/service-requests.keys'
import { serviceRequestQueries } from '../api/service-requests.queries'
import type { ServiceRequestDetail } from '../api/service-requests.types'
import { quotationsApi } from '../quotation/quotation.api'
import { quotationKeys } from '../quotation/quotation.keys'
import { quotationQueries } from '../quotation/quotation.queries'
import type {
  CreateQuotationInput,
  Quotation,
  UpdateQuotationInput,
} from '../quotation/quotation.types'
import { QuotationBuilderLiveWorkspace } from '../workspaces/QuotationBuilderLiveWorkspace'
import { QuotationDetailLiveWorkspace } from '../workspaces/QuotationDetailLiveWorkspace'
import '../styles/commercial.css'

function statusClass(status: string) {
  if (status === 'accepted') return 'commercial-pill-green'
  if (status === 'rejected' || status === 'expired') {
    return 'commercial-pill-gray'
  }
  if (status === 'awaiting_approval') return 'commercial-pill-yellow'
  return 'commercial-pill-blue'
}

export function QuotationsLivePage({ recordSearch }: { recordSearch: AppSectionSearch }) {
  const { user } = useAuth()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const toast = useToast()
  const page = recordSearch.page ?? 1

  const selectedQuoteId = recordSearch.quotation ? Number(recordSearch.quotation) : null
  const sourceRequestId = recordSearch.request ? Number(recordSearch.request) : null

  const [builderMode, setBuilderMode] = useState<'create' | 'edit' | 'revision' | null>(
    sourceRequestId ? 'create' : null,
  )
  const [builderRequest, setBuilderRequest] = useState<ServiceRequestDetail | null>(null)
  const [builderQuote, setBuilderQuote] = useState<Quotation | null>(null)
  const [builderRequestLoading, setBuilderRequestLoading] = useState(false)
  const [searchDraft, setSearchDraft] = useState(recordSearch.search ?? '')
  const [syncedSearch, setSyncedSearch] = useState(recordSearch.search ?? '')

  const filters = useMemo(
    () => ({
      ...(recordSearch.search ? { search: recordSearch.search } : {}),
      ...(recordSearch.status ? { status: recordSearch.status } : {}),
      page,
      limit: 10,
    }),
    [page, recordSearch.search, recordSearch.status],
  )

  const listQuery = useQuery(quotationQueries.list(filters))
  const searchListQuery = useQuery({
    ...quotationQueries.list({
      ...(recordSearch.status ? { status: recordSearch.status } : {}),
      page: 1,
      limit: 200,
    }),
    enabled: Boolean(recordSearch.search),
  })
  const summaryQuery = useQuery(quotationQueries.summary())
  const detailQuery = useQuery({
    ...quotationQueries.detail(selectedQuoteId ?? 0),
    enabled: Boolean(selectedQuoteId) && hasPermission(user, PERMISSIONS.quotesView),
  })

  const handoffRequestQuery = useQuery({
    ...serviceRequestQueries.detail(sourceRequestId ?? 0),
    enabled: Boolean(sourceRequestId),
  })

  const eligibleRequestListQuery = useQuery({
    ...serviceRequestQueries.list({ page: 1, limit: 100 }),
    enabled: builderMode === 'create' && !sourceRequestId,
  })

  const eligibleRequests = useMemo(
    () =>
      eligibleRequestListQuery.data?.items.filter(
        (request) =>
          !request.quoteId && request.status !== 'converted' && request.status !== 'rejected',
      ) ?? [],
    [eligibleRequestListQuery.data?.items],
  )

  const invalidate = async (quoteId?: number, requestId?: number) => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: quotationKeys.lists() }),
      queryClient.invalidateQueries({ queryKey: quotationKeys.summary() }),
      ...(quoteId
        ? [
            queryClient.invalidateQueries({
              queryKey: quotationKeys.detail(quoteId),
            }),
          ]
        : []),
      ...(requestId
        ? [
            queryClient.invalidateQueries({
              queryKey: serviceRequestKeys.detail(requestId),
            }),
            queryClient.invalidateQueries({
              queryKey: serviceRequestKeys.lists(),
            }),
          ]
        : []),
    ])
  }

  const closeBuilder = () => {
    setBuilderMode(null)
    setBuilderRequest(null)
    setBuilderQuote(null)
    if (sourceRequestId) {
      void navigate({
        to: '/app/$section',
        params: { section: 'quotations' },
        search: (previous) => withoutSearchKeys(previous, ['request']),
        replace: true,
      })
    }
  }

  const createMutation = useMutation({
    mutationFn: (input: CreateQuotationInput) => quotationsApi.create(input),
    onSuccess: async (quote, input) => {
      await invalidate(quote.id, input.serviceRequestId)
      closeBuilder()
      toast.success(
        builderMode === 'revision'
          ? `Revision ${quote.quoteNumber} submitted`
          : `Quotation ${quote.quoteNumber} submitted for approval`,
      )
      await navigate({
        to: '/app/$section',
        params: { section: 'quotations' },
        search: { quotation: String(quote.id) },
      })
    },
    onError: async (error) => {
      toast.error('Quotation could not be created', {
        description: presentError(error, 'form-submit').message,
      })
      await queryClient.invalidateQueries({
        queryKey: serviceRequestKeys.lists(),
      })
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({ quoteId, input }: { quoteId: number; input: UpdateQuotationInput }) =>
      quotationsApi.update(quoteId, input),
    onSuccess: async (quote) => {
      await invalidate(quote.id, quote.serviceRequestId ?? undefined)
      closeBuilder()
      toast.success('Quotation updated')
    },
    onError: async (error) => {
      toast.error('Quotation could not be updated', {
        description: presentError(error, 'background-action').message,
      })
      if (selectedQuoteId) {
        await queryClient.invalidateQueries({
          queryKey: quotationKeys.detail(selectedQuoteId),
        })
      }
    },
  })

  const approveMutation = useMutation({
    mutationFn: (quoteId: number) => quotationsApi.approve(quoteId),
    onSuccess: async (quote) => {
      await invalidate(quote.id, quote.serviceRequestId ?? undefined)
      toast.success('Quotation approved')
    },
    onError: async (error) => {
      toast.error('Quotation could not be approved', {
        description: presentError(error, 'background-action').message,
      })
      if (selectedQuoteId) {
        await queryClient.invalidateQueries({
          queryKey: quotationKeys.detail(selectedQuoteId),
        })
      }
    },
  })

  const setSearch = useCallback(
    (patch: Partial<AppSectionSearch>) => {
      void navigate({
        to: '/app/$section',
        params: { section: 'quotations' },
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
        params: { section: 'quotations' },
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
      params: { section: 'quotations' },
      search: (previous) => withoutSearchKeys(previous, ['search', 'status', 'page']),
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

  const beginDirectCreate = async () => {
    setBuilderMode('create')
    setBuilderQuote(null)
    setBuilderRequestLoading(true)
    const result = await eligibleRequestListQuery.refetch()
    const eligible =
      result.data?.items.filter(
        (request) =>
          !request.quoteId && request.status !== 'converted' && request.status !== 'rejected',
      ) ?? []
    const first = eligible[0]
    if (!first) {
      setBuilderRequest(null)
      setBuilderRequestLoading(false)
      return
    }
    try {
      const detail = await queryClient.fetchQuery(serviceRequestQueries.detail(first.id))
      setBuilderRequest(detail)
    } finally {
      setBuilderRequestLoading(false)
    }
  }

  const selectBuilderRequest = async (requestId: number) => {
    if (!requestId || builderRequest?.id === requestId) return
    setBuilderRequestLoading(true)
    try {
      const detail = await queryClient.fetchQuery(serviceRequestQueries.detail(requestId))
      setBuilderRequest(detail)
    } finally {
      setBuilderRequestLoading(false)
    }
  }

  if (listQuery.isPending || (recordSearch.search && searchListQuery.isPending)) {
    return <SectionLoadingState section="quotations" />
  }

  if (listQuery.isError) {
    const error = presentError(listQuery.error, 'page-load')
    return (
      <ModulePageStatus title="Quotations & Proposals" breadcrumb="Commercial flow / Offers">
        <ErrorState
          title={error.title}
          description={error.message}
          onRetry={() => void listQuery.refetch()}
        />
      </ModulePageStatus>
    )
  }

  if (searchListQuery.isError) {
    const error = presentError(searchListQuery.error, 'page-load')
    return (
      <ModulePageStatus title="Quotations & Proposals" breadcrumb="Commercial flow / Offers">
        <ErrorState
          title={error.title}
          description={error.message}
          onRetry={() => void searchListQuery.refetch()}
        />
      </ModulePageStatus>
    )
  }

  const sourceRequest = handoffRequestQuery.data ?? null
  const activeBuilderRequest = builderRequest ?? sourceRequest
  const hasActiveFilters = Boolean(recordSearch.search) || Boolean(recordSearch.status)
  const normalizedSearch = (recordSearch.search ?? '').trim().toLowerCase()
  const searchSourceItems = searchListQuery.data?.items ?? []
  const filteredQuotes = normalizedSearch
    ? searchSourceItems.filter((quote) =>
        [
          quote.quoteNumber,
          quote.clientName,
          quote.serviceName,
          quote.statusDisplay,
          quote.requiredApproverRoleName,
          quote.validUntil,
        ].some((value) => value.toLowerCase().includes(normalizedSearch)),
      )
    : listQuery.data.items
  const displayedCount = normalizedSearch ? filteredQuotes.length : listQuery.data.count
  const displayedQuotes = normalizedSearch ? filteredQuotes : listQuery.data.items
  const totalPages = Math.max(1, Math.ceil(displayedCount / 10))

  return (
    <ModulePageFrame
      header={
        <CompactPageToolbar
          title="Quotations & Proposals"
          breadcrumb="Commercial flow / Offers"
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
        <section className="commercial-kgrid commercial-kgrid-4" aria-label="Quotation summary">
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
              ['Awaiting approval', summaryQuery.data.awaitingApproval],
              ['Sent to clients', summaryQuery.data.sent],
              ['Accepted', summaryQuery.data.accepted],
              ['Acceptance rate', `${summaryQuery.data.acceptanceRate}%`],
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
              <h2>Quotations & Proposals</h2>
              <p>Live version-controlled scope, pricing, terms and approvals</p>
            </div>
            <div className="commercial-card-header-actions">
              <span className="commercial-count">{displayedCount} records</span>
              {listQuery.isFetching || searchListQuery.isFetching ? (
                <span className="commercial-count">Refreshing…</span>
              ) : null}
              <CompactActionButton
                tone="primary"
                disabled={!hasPermission(user, PERMISSIONS.quotesCreate)}
                locked={!hasPermission(user, PERMISSIONS.quotesCreate)}
                onClick={() => void beginDirectCreate()}
              >
                <IconPlus size={14} />
                Build Quote
              </CompactActionButton>
            </div>
          </header>

          <div className="commercial-filters">
            <label className="commercial-search">
              <IconSearch size={14} />
              <input
                value={searchDraft}
                onChange={(event) => setSearchDraft(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key !== 'Enter') return
                  event.preventDefault()
                  if (searchDraft === (recordSearch.search ?? '')) return
                  setSearchValue('search', searchDraft)
                }}
                placeholder="Search quote, client or service"
              />
            </label>
            <select
              value={recordSearch.status ?? ''}
              onChange={(event) => setSearchValue('status', event.target.value)}
            >
              <option value="">All statuses</option>
              <option value="awaiting_approval">Awaiting Approval</option>
              <option value="sent">Sent</option>
              <option value="accepted">Accepted</option>
              <option value="rejected">Rejected</option>
              <option value="expired">Expired</option>
            </select>
          </div>

          {displayedQuotes.length === 0 ? (
            <EmptyState
              title={
                hasActiveFilters ? 'No quotations match the current filters' : 'No quotations yet'
              }
              description={
                hasActiveFilters
                  ? 'Try adjusting or clearing the search and status filters to see matching quotations.'
                  : 'Build a quotation from an eligible Service Request.'
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
                    <th>Quote</th>
                    <th>Client</th>
                    <th>Service</th>
                    <th>Version</th>
                    <th>Total</th>
                    <th>Valid Until</th>
                    <th>Status</th>
                    <th>Approver</th>
                    <th aria-label="Actions" />
                  </tr>
                </thead>
                <tbody>
                  {displayedQuotes.map((quote) => (
                    <tr key={quote.id}>
                      <td>
                        <b>{quote.quoteNumber}</b>
                        <small>{new Date(quote.createdAt).toLocaleDateString('en-GB')}</small>
                      </td>
                      <td>{quote.clientName}</td>
                      <td>{quote.serviceName}</td>
                      <td>v{quote.version}</td>
                      <td>
                        <b>{formatCurrency(quote.amount)}</b>
                      </td>
                      <td>{quote.validUntil}</td>
                      <td>
                        <span className={`commercial-pill ${statusClass(quote.status)}`}>
                          {quote.statusDisplay}
                        </span>
                      </td>
                      <td>{quote.requiredApproverRoleName || '—'}</td>
                      <td>
                        <button
                          type="button"
                          className="commercial-btn commercial-btn-small"
                          disabled={!hasPermission(user, PERMISSIONS.quotesView)}
                          onClick={() =>
                            void navigate({
                              to: '/app/$section',
                              params: { section: 'quotations' },
                              search: (previous) => ({
                                ...previous,
                                quotation: String(quote.id),
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
              <span className="commercial-table-pagination-count">
                {listQuery.data.count} record{listQuery.data.count === 1 ? '' : 's'}
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

      {sourceRequestId && handoffRequestQuery.isPending ? (
        <div className="commercial-modal-backdrop">
          <section className="commercial-modal">
            <div className="commercial-empty">Loading source request...</div>
          </section>
        </div>
      ) : null}

      {builderMode === 'create' &&
      !activeBuilderRequest &&
      !sourceRequestId &&
      !eligibleRequestListQuery.isFetching ? (
        <div className="commercial-modal-backdrop">
          <section className="commercial-modal">
            <EmptyState
              title="No service requests are ready for quotation"
              description="Requests that are already quoted, converted, or closed are excluded from this list."
            />
            <footer className="commercial-modal-footer">
              <button type="button" className="commercial-btn" onClick={closeBuilder}>
                Close
              </button>
            </footer>
          </section>
        </div>
      ) : null}

      {builderMode && activeBuilderRequest ? (
        <QuotationBuilderLiveWorkspace
          mode={builderMode}
          request={activeBuilderRequest}
          {...(builderQuote ? { quote: builderQuote } : {})}
          {...(builderMode === 'create' && !sourceRequestId ? { eligibleRequests } : {})}
          requestSelectionLocked={Boolean(sourceRequestId) || builderMode !== 'create'}
          requestSelectionLoading={builderRequestLoading}
          saving={createMutation.isPending || updateMutation.isPending}
          onClose={closeBuilder}
          onRequestChange={(requestId) => void selectBuilderRequest(requestId)}
          onCreate={(input) => createMutation.mutate(input)}
          onUpdate={(input) => {
            if (!builderQuote) return
            updateMutation.mutate({ quoteId: builderQuote.id, input })
          }}
        />
      ) : null}

      {selectedQuoteId && detailQuery.isPending && !builderMode ? (
        <div className="commercial-modal-backdrop">
          <section className="commercial-modal">
            <div className="commercial-empty">Loading quotation...</div>
          </section>
        </div>
      ) : null}

      {selectedQuoteId && detailQuery.isError && !builderMode ? (
        <div className="commercial-modal-backdrop">
          <section className="commercial-modal">
            <EmptyState
              title="Quotation could not be opened"
              description={presentError(detailQuery.error, 'section-load').message}
            />
            <footer className="commercial-modal-footer">
              <button
                type="button"
                className="commercial-btn"
                onClick={() =>
                  void navigate({
                    to: '/app/$section',
                    params: { section: 'quotations' },
                    search: (previous) => withoutSearchKeys(previous, ['quotation']),
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

      {detailQuery.data && !builderMode ? (
        <QuotationDetailLiveWorkspace
          quotation={detailQuery.data}
          saving={approveMutation.isPending || updateMutation.isPending}
          canApprove={hasPermission(user, PERMISSIONS.quotesApprove)}
          canEdit={hasPermission(user, PERMISSIONS.quotesUpdate)}
          canRevise={hasPermission(user, PERMISSIONS.quotesCreate)}
          onClose={() =>
            void navigate({
              to: '/app/$section',
              params: { section: 'quotations' },
              search: (previous) => withoutSearchKeys(previous, ['quotation']),
            })
          }
          onEdit={() => {
            const requestId = detailQuery.data.serviceRequestId
            if (!requestId) return
            void queryClient.fetchQuery(serviceRequestQueries.detail(requestId)).then((request) => {
              setBuilderRequest(request)
              setBuilderQuote(detailQuery.data)
              setBuilderMode('edit')
            })
          }}
          onApprove={() => approveMutation.mutate(detailQuery.data.id)}
          onRevise={() => {
            const requestId = detailQuery.data.serviceRequestId
            if (!requestId) return
            void queryClient.fetchQuery(serviceRequestQueries.detail(requestId)).then((request) => {
              setBuilderRequest(request)
              setBuilderQuote(detailQuery.data)
              setBuilderMode('revision')
            })
          }}
          onCreateInvoice={() =>
            void navigate({
              to: '/app/$section',
              params: { section: 'invoices-payments' },
              search: { quotation: String(detailQuery.data.id) },
            })
          }
        />
      ) : null}
    </ModulePageFrame>
  )
}
