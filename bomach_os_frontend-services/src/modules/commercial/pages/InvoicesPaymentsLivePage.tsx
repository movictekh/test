import { IconPlus, IconSearch } from '@tabler/icons-react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from '@tanstack/react-router'
import { useCallback, useEffect, useMemo, useState } from 'react'

import { useAuth } from '@/app/auth'
import { hasPermission, PERMISSIONS } from '@/app/permissions'
import type { AppSectionSearch } from '@/routes/app/$section'
import { presentError } from '@/shared/errors'
import { formatCurrency } from '@/shared/lib/formatters'
import { withOptionalSearchValue, withoutSearchKeys } from '@/shared/navigation/search-state'
import { DashboardSkeleton, ErrorState, useToast } from '@/shared/ui'
import { EmptyState } from '@/shared/ui/empty-state'
import {
  CompactActionButton,
  CompactPageToolbar,
  ModulePageFrame,
  ModulePageStatus,
} from '@/shared/ui/module-controls'

import { serviceRequestQueries } from '../api/service-requests.queries'
import { billingApi } from '../billing/billing.api'
import { billingKeys } from '../billing/billing.keys'
import { billingQueries } from '../billing/billing.queries'
import type {
  CreateInvoiceFromQuoteInput,
  Invoice,
  PaymentSubmission,
  PaymentSubmissionStatus,
  RecordPaymentInput,
  ReviewPaymentSubmissionInput,
  UpdateInvoiceInput,
} from '../billing/billing.types'
import { PaymentSubmissionsPanel } from '../components/PaymentSubmissionsPanel'
import { quotationKeys } from '../quotation/quotation.keys'
import { quotationQueries } from '../quotation/quotation.queries'
import type { Quotation } from '../quotation/quotation.types'
import { InvoiceBuilderLiveWorkspace } from '../workspaces/InvoiceBuilderLiveWorkspace'
import { InvoiceDetailLiveWorkspace } from '../workspaces/InvoiceDetailLiveWorkspace'
import '../styles/commercial.css'

function invoiceStatusClass(status: Invoice['status']) {
  if (status === 'paid') return 'commercial-pill-green'
  if (status === 'partially_paid') return 'commercial-pill-yellow'
  if (status === 'overdue' || status === 'cancelled') {
    return 'commercial-pill-gray'
  }
  return 'commercial-pill-blue'
}

export function InvoicesPaymentsLivePage({ recordSearch }: { recordSearch: AppSectionSearch }) {
  const { user } = useAuth()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const toast = useToast()

  const page = recordSearch.page ?? 1
  const selectedInvoiceId = recordSearch.invoice ? Number(recordSearch.invoice) : null
  const sourceQuotationId = recordSearch.quotation ? Number(recordSearch.quotation) : null

  const [activeTab, setActiveTab] = useState<'invoices' | 'submissions'>('invoices')
  const [builderOpen, setBuilderOpen] = useState(Boolean(sourceQuotationId))
  const [builderQuotation, setBuilderQuotation] = useState<Quotation | null>(null)
  const [builderQuotationLoading, setBuilderQuotationLoading] = useState(false)
  const [submissionStatus, setSubmissionStatus] = useState<PaymentSubmissionStatus | ''>('pending')
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

  const listQuery = useQuery(billingQueries.list(filters))
  const summaryQuery = useQuery(billingQueries.summary())

  const detailQuery = useQuery({
    ...billingQueries.detail(selectedInvoiceId ?? 0),
    enabled: Boolean(selectedInvoiceId) && hasPermission(user, PERMISSIONS.serviceInvoicesView),
  })

  const paymentsQuery = useQuery({
    ...billingQueries.payments(selectedInvoiceId ?? 0),
    enabled: Boolean(selectedInvoiceId) && hasPermission(user, PERMISSIONS.paymentsList),
  })

  const clientsQuery = useQuery({
    ...serviceRequestQueries.clients(),
    enabled: hasPermission(user, PERMISSIONS.clientsList),
    retry: false,
  })

  const handoffQuotationQuery = useQuery({
    ...quotationQueries.detail(sourceQuotationId ?? 0),
    enabled: Boolean(sourceQuotationId),
  })

  const eligibleQuotesQuery = useQuery({
    ...billingQueries.eligibleQuotes(),
    enabled: builderOpen && !sourceQuotationId,
  })

  const submissionsQuery = useQuery({
    ...billingQueries.submissions(submissionStatus),
    enabled: activeTab === 'submissions' && hasPermission(user, PERMISSIONS.paymentsList),
  })

  const clientNames = useMemo(
    () => new Map((clientsQuery.data ?? []).map((client) => [client.id, client.name])),
    [clientsQuery.data],
  )

  const enrichInvoice = (invoice: Invoice): Invoice => ({
    ...invoice,
    clientName: clientNames.get(invoice.clientId) ?? invoice.clientName,
  })

  const closeBuilder = () => {
    setBuilderOpen(false)
    setBuilderQuotation(null)
    if (sourceQuotationId) {
      void navigate({
        to: '/app/$section',
        params: { section: 'invoices-payments' },
        search: (previous) => withoutSearchKeys(previous, ['quotation']),
        replace: true,
      })
    }
  }

  const invalidateInvoices = async (invoiceId?: number, quoteId?: number | null) => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: billingKeys.invoiceLists() }),
      queryClient.invalidateQueries({ queryKey: billingKeys.summary() }),
      queryClient.invalidateQueries({ queryKey: billingKeys.allInvoices() }),
      queryClient.invalidateQueries({ queryKey: billingKeys.eligibleQuotes() }),
      ...(invoiceId
        ? [
            queryClient.invalidateQueries({
              queryKey: billingKeys.invoiceDetail(invoiceId),
            }),
            queryClient.invalidateQueries({
              queryKey: billingKeys.payments(invoiceId),
            }),
          ]
        : []),
      ...(quoteId
        ? [
            queryClient.invalidateQueries({
              queryKey: quotationKeys.detail(quoteId),
            }),
            queryClient.invalidateQueries({
              queryKey: quotationKeys.lists(),
            }),
          ]
        : []),
    ])
  }

  const createInvoiceMutation = useMutation({
    mutationFn: (input: CreateInvoiceFromQuoteInput) => billingApi.createFromQuote(input),
    onSuccess: async (invoice, input) => {
      await invalidateInvoices(invoice.id, input.quoteId)
      closeBuilder()
      toast.success(`Invoice ${invoice.invoiceNumber} created`, {
        description: 'The invoice is in Draft. Review it, then send it to the client.',
      })
      await navigate({
        to: '/app/$section',
        params: { section: 'invoices-payments' },
        search: { invoice: String(invoice.id) },
      })
    },
    onError: async (error) => {
      toast.error('Invoice could not be created', {
        description: presentError(error, 'form-submit').message,
      })
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: billingKeys.eligibleQuotes() }),
        queryClient.invalidateQueries({ queryKey: billingKeys.allInvoices() }),
      ])
    },
  })

  const updateInvoiceMutation = useMutation({
    mutationFn: ({ invoiceId, input }: { invoiceId: number; input: UpdateInvoiceInput }) =>
      billingApi.update(invoiceId, input),
    onSuccess: async (invoice) => {
      await invalidateInvoices(invoice.id, invoice.quoteId)
      toast.success('Invoice updated')
    },
    onError: async (error) => {
      toast.error('Invoice could not be updated', {
        description: presentError(error, 'background-action').message,
      })
      if (selectedInvoiceId) {
        await queryClient.invalidateQueries({
          queryKey: billingKeys.invoiceDetail(selectedInvoiceId),
        })
      }
    },
  })

  const sendInvoiceMutation = useMutation({
    mutationFn: (invoice: Invoice) => billingApi.send(invoice.id, invoice.paymentInstructions),
    onSuccess: async (invoice) => {
      await invalidateInvoices(invoice.id, invoice.quoteId)
      toast.success(invoice.status === 'sent' ? 'Invoice sent to client' : 'Invoice updated')
    },
    onError: async (error) => {
      toast.error('Invoice could not be sent', {
        description: presentError(error, 'background-action').message,
      })
      if (selectedInvoiceId) {
        await queryClient.invalidateQueries({
          queryKey: billingKeys.invoiceDetail(selectedInvoiceId),
        })
      }
    },
  })

  const cancelInvoiceMutation = useMutation({
    mutationFn: (invoiceId: number) => billingApi.cancel(invoiceId),
    onSuccess: async (invoice) => {
      await invalidateInvoices(invoice.id, invoice.quoteId)
      toast.success('Invoice cancelled')
    },
    onError: async (error) => {
      toast.error('Invoice could not be cancelled', {
        description: presentError(error, 'background-action').message,
      })
      if (selectedInvoiceId) {
        await queryClient.invalidateQueries({
          queryKey: billingKeys.invoiceDetail(selectedInvoiceId),
        })
      }
    },
  })

  const recordPaymentMutation = useMutation({
    mutationFn: (
      input: Omit<RecordPaymentInput, 'createdById'> & {
        createdById: number
      },
    ) => billingApi.recordPayment(input),
    onSuccess: async (payment) => {
      const invoice = await billingApi.detail(payment.invoiceId)
      await invalidateInvoices(invoice.id, invoice.quoteId)
      toast.success('Payment recorded', {
        description: `${formatCurrency(payment.amount)} confirmed against ${invoice.invoiceNumber}.`,
      })
    },
    onError: async (error) => {
      toast.error('Payment could not be recorded', {
        description: presentError(error, 'form-submit').message,
      })
      if (selectedInvoiceId) {
        await Promise.all([
          queryClient.invalidateQueries({
            queryKey: billingKeys.invoiceDetail(selectedInvoiceId),
          }),
          queryClient.invalidateQueries({
            queryKey: billingKeys.payments(selectedInvoiceId),
          }),
        ])
      }
    },
  })

  const reviewSubmissionMutation = useMutation({
    mutationFn: ({
      submission,
      input,
    }: {
      submission: PaymentSubmission
      input: ReviewPaymentSubmissionInput
    }) => billingApi.reviewPaymentSubmission(submission.id, input),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({
          queryKey: billingKeys.submissions(submissionStatus),
        }),
        queryClient.invalidateQueries({ queryKey: billingKeys.invoiceLists() }),
        queryClient.invalidateQueries({ queryKey: billingKeys.summary() }),
        queryClient.invalidateQueries({ queryKey: billingKeys.allInvoices() }),
      ])
      toast.success('Payment submission reviewed')
    },
    onError: (error) => {
      toast.error('Payment submission could not be reviewed', {
        description: presentError(error, 'background-action').message,
      })
    },
  })

  const setSearch = useCallback(
    (patch: Partial<AppSectionSearch>) => {
      void navigate({
        to: '/app/$section',
        params: { section: 'invoices-payments' },
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
        params: { section: 'invoices-payments' },
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
      params: { section: 'invoices-payments' },
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
    setBuilderOpen(true)
    setBuilderQuotationLoading(true)
    try {
      const result = await eligibleQuotesQuery.refetch()
      const first = result.data?.[0]
      setBuilderQuotation(first ?? null)
    } finally {
      setBuilderQuotationLoading(false)
    }
  }

  const selectBuilderQuotation = async (quotationId: number) => {
    if (!quotationId || builderQuotation?.id === quotationId) return
    setBuilderQuotationLoading(true)
    try {
      const quotation = await queryClient.fetchQuery(quotationQueries.detail(quotationId))
      setBuilderQuotation(quotation)
    } finally {
      setBuilderQuotationLoading(false)
    }
  }

  if (listQuery.isPending) {
    return (
      <ModulePageStatus title="Invoices & Payments" breadcrumb="Commercial flow / Billing">
        <DashboardSkeleton />
      </ModulePageStatus>
    )
  }

  if (listQuery.isError) {
    const error = presentError(listQuery.error, 'page-load')
    return (
      <ModulePageStatus title="Invoices & Payments" breadcrumb="Commercial flow / Billing">
        <ErrorState
          title={error.title}
          description={error.message}
          onRetry={() => void listQuery.refetch()}
        />
      </ModulePageStatus>
    )
  }

  const enrichedInvoices = listQuery.data.items.map(enrichInvoice)
  const detailInvoice = detailQuery.data ? enrichInvoice(detailQuery.data) : null
  const sourceQuotation = handoffQuotationQuery.data ?? null
  const activeBuilderQuotation = builderQuotation ?? sourceQuotation
  const eligibleQuotes = eligibleQuotesQuery.data ?? []
  const hasActiveFilters = Boolean(recordSearch.search) || Boolean(recordSearch.status)
  const totalPages = Math.max(1, Math.ceil(listQuery.data.count / 10))

  return (
    <ModulePageFrame
      header={
        <CompactPageToolbar
          title="Invoices & Payments"
          breadcrumb="Commercial flow / Billing"
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
              <IconPlus size={14} />
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
        <section className="commercial-kgrid commercial-kgrid-4" aria-label="Invoice summary">
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
              ['Total invoiced', formatCurrency(summaryQuery.data.totalInvoiced)],
              ['Paid', formatCurrency(summaryQuery.data.paid)],
              ['Outstanding', formatCurrency(summaryQuery.data.outstanding)],
              ['Overdue', summaryQuery.data.overdue],
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
              <h2>Invoices & Payment Review</h2>
              <p>Track issued invoices, payment confirmations, balances, and follow-up actions.</p>
            </div>
            <div className="commercial-card-header-actions">
              <span className="commercial-count">
                {listQuery.data.count} invoice{listQuery.data.count === 1 ? '' : 's'}
              </span>
              {listQuery.isFetching ? <span className="commercial-count">Refreshing…</span> : null}
              <CompactActionButton
                tone="primary"
                disabled={!hasPermission(user, PERMISSIONS.serviceInvoicesCreate)}
                locked={!hasPermission(user, PERMISSIONS.serviceInvoicesCreate)}
                onClick={() => void beginDirectCreate()}
              >
                <IconPlus size={14} />
                New Invoice
              </CompactActionButton>
            </div>
          </header>

          <div className="commercial-tabs" role="tablist">
            <button
              type="button"
              className={`commercial-tab ${activeTab === 'invoices' ? 'is-active' : ''}`}
              onClick={() => setActiveTab('invoices')}
            >
              Invoice Register
            </button>
            <button
              type="button"
              className={`commercial-tab ${activeTab === 'submissions' ? 'is-active' : ''}`}
              disabled={!hasPermission(user, PERMISSIONS.paymentsList)}
              onClick={() => setActiveTab('submissions')}
            >
              Payment Confirmations
            </button>
          </div>

          {activeTab === 'invoices' ? (
            <>
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
                    placeholder="Search invoice number"
                  />
                </label>

                <select
                  value={recordSearch.status ?? ''}
                  onChange={(event) => setSearchValue('status', event.target.value)}
                >
                  <option value="">All statuses</option>
                  <option value="draft">Draft</option>
                  <option value="sent">Sent</option>
                  <option value="viewed">Viewed</option>
                  <option value="partially_paid">Partially Paid</option>
                  <option value="paid">Paid</option>
                  <option value="overdue">Overdue</option>
                  <option value="cancelled">Cancelled</option>
                </select>
              </div>

              {enrichedInvoices.length === 0 ? (
                <EmptyState
                  title={
                    hasActiveFilters ? 'No invoices match the current filters' : 'No invoices yet'
                  }
                  description={
                    hasActiveFilters
                      ? 'Try adjusting or clearing the search and status filters to see matching invoices.'
                      : 'Create an invoice from an accepted quotation to start billing and payment tracking.'
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
                        <th>Invoice</th>
                        <th>Client</th>
                        <th>Service</th>
                        <th>Total</th>
                        <th>Paid</th>
                        <th>Balance</th>
                        <th>Due</th>
                        <th>Status</th>
                        <th aria-label="Actions" />
                      </tr>
                    </thead>
                    <tbody>
                      {enrichedInvoices.map((invoice) => (
                        <tr key={invoice.id}>
                          <td>
                            <b>{invoice.invoiceNumber}</b>
                            <small>{invoice.paymentSchedule || '—'}</small>
                          </td>
                          <td>{invoice.clientName || `Client #${invoice.clientId}`}</td>
                          <td>{invoice.serviceName}</td>
                          <td>{formatCurrency(invoice.totalAmount)}</td>
                          <td>{formatCurrency(invoice.amountPaid)}</td>
                          <td>
                            <b>{formatCurrency(invoice.balance)}</b>
                          </td>
                          <td>{invoice.dueDate}</td>
                          <td>
                            <span
                              className={`commercial-pill ${invoiceStatusClass(invoice.status)}`}
                            >
                              {invoice.status.replaceAll('_', ' ')}
                            </span>
                          </td>
                          <td>
                            <button
                              type="button"
                              className="commercial-btn commercial-btn-small"
                              disabled={!hasPermission(user, PERMISSIONS.serviceInvoicesView)}
                              onClick={() =>
                                void navigate({
                                  to: '/app/$section',
                                  params: {
                                    section: 'invoices-payments',
                                  },
                                  search: (previous) => ({
                                    ...previous,
                                    invoice: String(invoice.id),
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
            </>
          ) : (
            <PaymentSubmissionsPanel
              submissions={submissionsQuery.data?.items ?? []}
              status={submissionStatus}
              loading={submissionsQuery.isPending}
              error={
                submissionsQuery.isError
                  ? presentError(submissionsQuery.error, 'section-load').message
                  : ''
              }
              onRetry={() => void submissionsQuery.refetch()}
              saving={reviewSubmissionMutation.isPending}
              canReview={hasPermission(user, PERMISSIONS.paymentsCreate)}
              onStatusChange={setSubmissionStatus}
              onReview={(submission, input) =>
                reviewSubmissionMutation.mutate({ submission, input })
              }
            />
          )}
        </section>
      </main>

      {sourceQuotationId && handoffQuotationQuery.isPending ? (
        <div className="commercial-modal-backdrop">
          <section className="commercial-modal">
            <div className="commercial-empty">Loading accepted quotation...</div>
          </section>
        </div>
      ) : null}

      {sourceQuotationId && handoffQuotationQuery.isError ? (
        <div className="commercial-modal-backdrop">
          <section className="commercial-modal">
            <EmptyState
              title="Quotation could not be loaded"
              description={presentError(handoffQuotationQuery.error, 'section-load').message}
            />
            <footer className="commercial-modal-footer">
              <button type="button" className="commercial-btn" onClick={closeBuilder}>
                Close
              </button>
              <button
                type="button"
                className="commercial-btn commercial-btn-primary"
                onClick={() => void handoffQuotationQuery.refetch()}
              >
                Retry
              </button>
            </footer>
          </section>
        </div>
      ) : null}

      {builderOpen &&
      !activeBuilderQuotation &&
      !sourceQuotationId &&
      !eligibleQuotesQuery.isFetching ? (
        <div className="commercial-modal-backdrop">
          <section className="commercial-modal">
            <EmptyState
              title="No quotations are ready for invoicing"
              description="All accepted quotations already have invoices, or there are no accepted quotations available yet."
            />
            <footer className="commercial-modal-footer">
              <button type="button" className="commercial-btn" onClick={closeBuilder}>
                Close
              </button>
            </footer>
          </section>
        </div>
      ) : null}

      {builderOpen && activeBuilderQuotation ? (
        <InvoiceBuilderLiveWorkspace
          key={activeBuilderQuotation.id}
          quotation={activeBuilderQuotation}
          eligibleQuotations={
            sourceQuotationId
              ? [activeBuilderQuotation]
              : eligibleQuotes.length > 0
                ? eligibleQuotes
                : [activeBuilderQuotation]
          }
          quotationSelectionLocked={Boolean(sourceQuotationId)}
          quotationSelectionLoading={builderQuotationLoading}
          saving={createInvoiceMutation.isPending}
          onSelectQuotation={(quotationId) => void selectBuilderQuotation(quotationId)}
          onClose={closeBuilder}
          onSubmit={(input) => createInvoiceMutation.mutate(input)}
        />
      ) : null}

      {selectedInvoiceId && detailQuery.isPending && !builderOpen ? (
        <div className="commercial-modal-backdrop">
          <section className="commercial-modal">
            <div className="commercial-empty">Loading invoice...</div>
          </section>
        </div>
      ) : null}

      {selectedInvoiceId && detailQuery.isError && !builderOpen ? (
        <div className="commercial-modal-backdrop">
          <section className="commercial-modal">
            <EmptyState
              title="Invoice could not be opened"
              description={presentError(detailQuery.error, 'section-load').message}
            />
            <footer className="commercial-modal-footer">
              <button
                type="button"
                className="commercial-btn"
                onClick={() =>
                  void navigate({
                    to: '/app/$section',
                    params: { section: 'invoices-payments' },
                    search: (previous) => withoutSearchKeys(previous, ['invoice']),
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

      {detailInvoice && !builderOpen ? (
        <InvoiceDetailLiveWorkspace
          invoice={detailInvoice}
          payments={paymentsQuery.data?.items ?? []}
          paymentsLoading={paymentsQuery.isPending}
          paymentsError={
            paymentsQuery.isError ? presentError(paymentsQuery.error, 'section-load').message : ''
          }
          canViewPayments={hasPermission(user, PERMISSIONS.paymentsList)}
          onRetryPayments={() => void paymentsQuery.refetch()}
          saving={
            updateInvoiceMutation.isPending ||
            sendInvoiceMutation.isPending ||
            cancelInvoiceMutation.isPending ||
            recordPaymentMutation.isPending
          }
          canUpdate={hasPermission(user, PERMISSIONS.serviceInvoicesUpdate)}
          canRecordPayment={hasPermission(user, PERMISSIONS.paymentsCreate)}
          canCreateServiceOrder={hasPermission(user, PERMISSIONS.ordersCreate)}
          canViewServiceOrder={hasPermission(user, PERMISSIONS.ordersView)}
          onCreateServiceOrder={() =>
            void navigate({
              to: '/app/$section',
              params: { section: 'service-orders' },
              search: { invoice: String(detailInvoice.id) },
            })
          }
          onOpenServiceOrder={() => {
            if (!detailInvoice.orderId) return
            void navigate({
              to: '/app/$section',
              params: { section: 'service-orders' },
              search: { order: String(detailInvoice.orderId) },
            })
          }}
          onClose={() =>
            void navigate({
              to: '/app/$section',
              params: { section: 'invoices-payments' },
              search: (previous) => withoutSearchKeys(previous, ['invoice']),
            })
          }
          onUpdate={(input) =>
            updateInvoiceMutation.mutate({
              invoiceId: detailInvoice.id,
              input,
            })
          }
          onSend={() => sendInvoiceMutation.mutate(detailInvoice)}
          onCancel={() => cancelInvoiceMutation.mutate(detailInvoice.id)}
          onRecordPayment={(input) => {
            const createdById = Number(user?.id)
            if (!Number.isFinite(createdById) || createdById <= 0) {
              toast.error('Payment could not be recorded', {
                description: 'The signed-in backend user ID is unavailable.',
              })
              return
            }
            recordPaymentMutation.mutate({
              ...input,
              createdById,
            })
          }}
        />
      ) : null}
    </ModulePageFrame>
  )
}
