import { IconFilePlus, IconPlus, IconRefresh, IconSearch } from '@tabler/icons-react'
import { useMutation, useQueries, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from '@tanstack/react-router'
import { useCallback, useEffect, useMemo, useState } from 'react'

import { useAuth } from '@/app/auth'
import { hasPermission, PERMISSIONS } from '@/app/permissions'
import { serviceRequestQueries } from '@/modules/commercial/api/service-requests.queries'
import { billingKeys } from '@/modules/commercial/billing/billing.keys'
import { billingQueries } from '@/modules/commercial/billing/billing.queries'
import type { Invoice } from '@/modules/commercial/billing/billing.types'
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

import { serviceOrderApi } from '../service-orders/service-order.api'
import { serviceOrderKeys } from '../service-orders/service-order.keys'
import { serviceOrderQueries } from '../service-orders/service-order.queries'
import {
  allOrderStatuses,
  operationalOrderStatuses,
  type ServiceOrder,
} from '../service-orders/service-order.types'
import { CreateServiceOrderLiveWorkspace } from '../workspaces/CreateServiceOrderLiveWorkspace'
import { OrderControlRoomLiveWorkspace } from '../workspaces/OrderControlRoomLiveWorkspace'
import '../styles/fulfillment.css'
import '../../commercial/styles/commercial.css'

function statusLabel(status: string) {
  return status.replaceAll('_', ' ').replace(/\b\w/g, (letter) => letter.toUpperCase())
}

function statusClass(status: ServiceOrder['orderStatus']) {
  if (status === 'completed') return 'commercial-pill-green'
  if (status === 'cancelled' || status === 'on_hold') return 'commercial-pill-gray'
  if (status === 'quality_review' || status === 'awaiting_client') return 'commercial-pill-yellow'
  return 'commercial-pill-blue'
}

export function ServiceOrdersLivePage({ recordSearch }: { recordSearch: AppSectionSearch }) {
  const { user } = useAuth()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const toast = useToast()

  const page = recordSearch.page ?? 1
  const selectedOrderId = recordSearch.order ? Number(recordSearch.order) : null
  const sourceInvoiceId = recordSearch.invoice ? Number(recordSearch.invoice) : null

  const [builderOpen, setBuilderOpen] = useState(Boolean(sourceInvoiceId))
  const [builderInvoice, setBuilderInvoice] = useState<Invoice | null>(null)
  const [builderInvoiceLoading, setBuilderInvoiceLoading] = useState(false)
  const [searchDraft, setSearchDraft] = useState(recordSearch.search ?? '')
  const [syncedSearch, setSyncedSearch] = useState(recordSearch.search ?? '')

  const registerFilters = useMemo(
    () => ({
      ...(recordSearch.search ? { search: recordSearch.search } : {}),
      ...(recordSearch.status ? { orderStatus: recordSearch.status } : {}),
      ...(recordSearch.paymentStatus ? { paymentStatus: recordSearch.paymentStatus } : {}),
      page,
      limit: 10,
    }),
    [page, recordSearch.paymentStatus, recordSearch.search, recordSearch.status],
  )

  const listQuery = useQuery(serviceOrderQueries.list(registerFilters))
  const boardQueries = useQueries({
    queries: operationalOrderStatuses.map((status) =>
      serviceOrderQueries.list({
        orderStatus: status.value,
        ...(recordSearch.search ? { search: recordSearch.search } : {}),
        ...(recordSearch.paymentStatus ? { paymentStatus: recordSearch.paymentStatus } : {}),
        page: 1,
        limit: 8,
      }),
    ),
  })

  const detailQuery = useQuery({
    ...serviceOrderQueries.detail(selectedOrderId ?? 0),
    enabled: Boolean(selectedOrderId) && hasPermission(user, PERMISSIONS.ordersView),
  })

  const linkedInvoiceQuery = useQuery({
    ...billingQueries.detail(detailQuery.data?.invoiceId ?? 0),
    enabled:
      Boolean(detailQuery.data?.invoiceId) && hasPermission(user, PERMISSIONS.serviceInvoicesView),
  })

  const employeesQuery = useQuery({
    ...serviceOrderQueries.employees(),
    enabled: hasPermission(user, PERMISSIONS.employeesList),
    retry: false,
  })

  const clientsQuery = useQuery({
    ...serviceRequestQueries.clients(),
    enabled: hasPermission(user, PERMISSIONS.clientsList),
    retry: false,
  })

  const handoffInvoiceQuery = useQuery({
    ...billingQueries.detail(sourceInvoiceId ?? 0),
    enabled: Boolean(sourceInvoiceId),
  })

  const allInvoicesQuery = useQuery({
    ...billingQueries.allInvoices(),
    enabled: builderOpen && !sourceInvoiceId,
  })

  const eligibleInvoices = useMemo(
    () =>
      (allInvoicesQuery.data ?? []).filter(
        (invoice) =>
          Boolean(invoice.activationThresholdMetAt) &&
          !invoice.orderId &&
          invoice.status !== 'cancelled',
      ),
    [allInvoicesQuery.data],
  )

  const clientNames = useMemo(
    () => new Map((clientsQuery.data ?? []).map((client) => [client.id, client.name])),
    [clientsQuery.data],
  )
  const employeeNames = useMemo(
    () => new Map((employeesQuery.data ?? []).map((employee) => [employee.id, employee.name])),
    [employeesQuery.data],
  )

  const setSearch = useCallback(
    (patch: Partial<AppSectionSearch>) => {
      void navigate({
        to: '/app/$section',
        params: { section: 'service-orders' },
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
        params: { section: 'service-orders' },
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

  if ((recordSearch.search ?? '') !== syncedSearch) {
    setSyncedSearch(recordSearch.search ?? '')
    setSearchDraft(recordSearch.search ?? '')
  }

  useEffect(() => {
    if (searchDraft === (recordSearch.search ?? '')) return
    const timeoutId = window.setTimeout(() => setSearchValue('search', searchDraft), 350)
    return () => window.clearTimeout(timeoutId)
  }, [recordSearch.search, searchDraft, setSearchValue])

  const invalidateOrders = async (orderId?: number, invoiceId?: number | null) => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: serviceOrderKeys.lists() }),
      ...(orderId
        ? [queryClient.invalidateQueries({ queryKey: serviceOrderKeys.detail(orderId) })]
        : []),
      queryClient.invalidateQueries({ queryKey: billingKeys.invoiceLists() }),
      queryClient.invalidateQueries({ queryKey: billingKeys.allInvoices() }),
      ...(invoiceId
        ? [queryClient.invalidateQueries({ queryKey: billingKeys.invoiceDetail(invoiceId) })]
        : []),
    ])
  }

  const createMutation = useMutation({
    mutationFn: (input: Parameters<typeof serviceOrderApi.createFromInvoice>[0]) =>
      serviceOrderApi.createFromInvoice(input),
    onSuccess: async (order) => {
      await invalidateOrders(order.id, order.invoiceId)
      setBuilderOpen(false)
      setBuilderInvoice(null)
      toast.success(`Service Order ${order.orderNumber} created`)
      await navigate({
        to: '/app/$section',
        params: { section: 'service-orders' },
        search: { order: String(order.id) },
      })
    },
    onError: async (error) => {
      toast.error('Service Order could not be created', {
        description: presentError(error, 'form-submit').message,
      })
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: billingKeys.allInvoices() }),
        queryClient.invalidateQueries({ queryKey: serviceOrderKeys.lists() }),
      ])
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({
      orderId,
      input,
    }: {
      orderId: number
      input: Parameters<typeof serviceOrderApi.update>[1]
    }) => serviceOrderApi.update(orderId, input),
    onSuccess: async (order) => {
      await invalidateOrders(order.id, order.invoiceId)
      toast.success('Order controls updated')
    },
    onError: async (error) => {
      toast.error('Order could not be updated', {
        description: presentError(error, 'background-action').message,
      })
      if (selectedOrderId)
        await queryClient.invalidateQueries({ queryKey: serviceOrderKeys.detail(selectedOrderId) })
    },
  })

  const completeMutation = useMutation({
    mutationFn: ({ orderId, milestoneId }: { orderId: number; milestoneId: number }) =>
      serviceOrderApi.completeMilestone(orderId, milestoneId),
    onSuccess: async (order) => {
      await invalidateOrders(order.id, order.invoiceId)
      toast.success(
        order.orderStatus === 'completed'
          ? 'Service Order completed'
          : `Stage advanced to ${order.stage}`,
      )
    },
    onError: async (error) => {
      toast.error('Stage could not be advanced', {
        description: presentError(error, 'background-action').message,
      })
      if (selectedOrderId)
        await queryClient.invalidateQueries({ queryKey: serviceOrderKeys.detail(selectedOrderId) })
    },
  })

  const activityMutation = useMutation({
    mutationFn: ({
      orderId,
      input,
    }: {
      orderId: number
      input: Parameters<typeof serviceOrderApi.addActivity>[1]
    }) => serviceOrderApi.addActivity(orderId, input),
    onSuccess: async (_activity, variables) => {
      await invalidateOrders(variables.orderId, detailQuery.data?.invoiceId)
      toast.success('Order update recorded')
    },
    onError: (error) => {
      toast.error('Order update could not be recorded', {
        description: presentError(error, 'form-submit').message,
      })
    },
  })

  const milestoneMutation = useMutation({
    mutationFn: ({
      orderId,
      input,
    }: {
      orderId: number
      input: Parameters<typeof serviceOrderApi.addMilestone>[1]
    }) => serviceOrderApi.addMilestone(orderId, input),
    onSuccess: async (_milestone, variables) => {
      await invalidateOrders(variables.orderId, detailQuery.data?.invoiceId)
      toast.success('Milestone added')
    },
    onError: (error) => {
      toast.error('Milestone could not be added', {
        description: presentError(error, 'form-submit').message,
      })
    },
  })

  const closeBuilder = () => {
    setBuilderOpen(false)
    setBuilderInvoice(null)
    if (sourceInvoiceId) {
      void navigate({
        to: '/app/$section',
        params: { section: 'service-orders' },
        search: (previous) => withoutSearchKeys(previous, ['invoice']),
        replace: true,
      })
    }
  }

  const selectBuilderInvoice = async (invoiceId: number) => {
    if (!invoiceId || builderInvoice?.id === invoiceId) return
    setBuilderInvoiceLoading(true)
    try {
      setBuilderInvoice(await queryClient.fetchQuery(billingQueries.detail(invoiceId)))
    } finally {
      setBuilderInvoiceLoading(false)
    }
  }

  const refresh = async () => {
    await Promise.all([listQuery.refetch(), ...boardQueries.map((query) => query.refetch())])
    toast.success('Service Orders refreshed')
  }

  if (listQuery.isPending) {
    return (
      <ModulePageStatus title="Service Orders" breadcrumb="Fulfillment / Orders">
        <DashboardSkeleton />
      </ModulePageStatus>
    )
  }
  if (listQuery.isError) {
    const error = presentError(listQuery.error, 'page-load')
    return (
      <ModulePageStatus title="Service Orders" breadcrumb="Fulfillment / Orders">
        <ErrorState
          title={error.title}
          description={error.message}
          onRetry={() => void listQuery.refetch()}
        />
      </ModulePageStatus>
    )
  }

  const sourceInvoice = handoffInvoiceQuery.data ?? null
  const activeBuilderInvoice =
    builderInvoice ??
    sourceInvoice ??
    (builderOpen && !sourceInvoiceId ? (eligibleInvoices[0] ?? null) : null)
  const builderInvoices = sourceInvoiceId
    ? activeBuilderInvoice
      ? [activeBuilderInvoice]
      : []
    : eligibleInvoices.length > 0
      ? eligibleInvoices
      : activeBuilderInvoice
        ? [activeBuilderInvoice]
        : []
  const totalPages = Math.max(1, Math.ceil(listQuery.data.count / 10))
  const hasActiveFilters = Boolean(
    recordSearch.search || recordSearch.status || recordSearch.paymentStatus,
  )
  const boardRefreshing = boardQueries.some((query) => query.isFetching)
  const busy =
    createMutation.isPending ||
    updateMutation.isPending ||
    completeMutation.isPending ||
    activityMutation.isPending ||
    milestoneMutation.isPending

  return (
    <ModulePageFrame
      header={
        <CompactPageToolbar
          title="Service Orders"
          breadcrumb="Fulfillment / Orders"
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
              Add New Request
            </CompactActionButton>
          }
          primaryAction={
            <CompactActionButton
              tone="primary"
              disabled={!hasPermission(user, PERMISSIONS.servicesCreate)}
              locked={!hasPermission(user, PERMISSIONS.servicesCreate)}
              onClick={() => {
                void navigate({
                  to: '/app/$section',
                  params: { section: 'service-catalogue' },
                })
              }}
            >
              <IconPlus size={14} />
              Create Service
            </CompactActionButton>
          }
        />
      }
    >
      <main className="fulfillment-content">
        <section className="commercial-card">
          <header className="commercial-card-header">
            <div>
              <h2>Operational Order Board</h2>
              <p>Mobilisation, active execution, quality review, client checkpoints and holds.</p>
            </div>
            <div className="commercial-card-header-actions">
              {boardRefreshing ? <span className="commercial-count">Refreshing…</span> : null}
              <CompactActionButton disabled={boardRefreshing} onClick={() => void refresh()}>
                <IconRefresh size={14} /> Refresh
              </CompactActionButton>
            </div>
          </header>

          <div className="commercial-filters">
            <label className="commercial-search">
              <IconSearch size={14} />
              <input
                value={searchDraft}
                onChange={(event) => setSearchDraft(event.target.value)}
                placeholder="Search order, client or service"
              />
            </label>
            <select
              value={recordSearch.paymentStatus ?? ''}
              onChange={(event) => setSearchValue('paymentStatus', event.target.value)}
            >
              <option value="">All payment statuses</option>
              <option value="unpaid">Unpaid</option>
              <option value="partial">Partial</option>
              <option value="paid">Paid</option>
            </select>
          </div>

          <div className="fulfillment-kanban" id="orderBoard">
            {operationalOrderStatuses.map((column, index) => {
              const query = boardQueries[index]!
              const items = query.data?.items ?? []
              return (
                <section className="fulfillment-column" key={column.value}>
                  <div className="fulfillment-column-header">
                    <span>{column.label}</span>
                    <span>{query.data?.count ?? 0}</span>
                  </div>
                  {query.isPending ? (
                    <div className="fulfillment-empty fulfillment-empty-column">Loading…</div>
                  ) : query.isError ? (
                    <button
                      type="button"
                      className="commercial-btn commercial-btn-small"
                      onClick={() => void query.refetch()}
                    >
                      Retry
                    </button>
                  ) : items.length === 0 ? (
                    <div className="fulfillment-empty fulfillment-empty-column">No orders</div>
                  ) : (
                    items.map((order) => (
                      <button
                        type="button"
                        key={order.id}
                        className="fulfillment-task-card fulfillment-order-card"
                        disabled={!hasPermission(user, PERMISSIONS.ordersView)}
                        onClick={() =>
                          void navigate({
                            to: '/app/$section',
                            params: { section: 'service-orders' },
                            search: (previous) => ({ ...previous, order: String(order.id) }),
                          })
                        }
                      >
                        <b>{clientNames.get(order.clientId) ?? `Client #${order.clientId}`}</b>
                        <small>
                          {order.serviceName} · {order.orderNumber}
                        </small>
                        <div className="fulfillment-progress">
                          <i style={{ width: `${order.progress}%` }} />
                        </div>
                        <div className="fulfillment-task-footer">
                          <span className="fulfillment-pill fulfillment-pill-blue">
                            {order.progress}%
                          </span>
                          <span className="fulfillment-row-sub">
                            {order.dueDate
                              ? `Due ${order.dueDate}`
                              : statusLabel(order.paymentStatus)}
                          </span>
                        </div>
                      </button>
                    ))
                  )}
                </section>
              )
            })}
          </div>
        </section>

        <section className="commercial-card">
          <header className="commercial-card-header">
            <div>
              <h2>Service Order Register</h2>
              <p>Complete paginated record of Service Orders.</p>
            </div>
            <div className="commercial-card-header-actions">
              <span className="commercial-count">{listQuery.data.count} records</span>
              <CompactActionButton
                tone="primary"
                disabled={
                  !hasPermission(user, PERMISSIONS.ordersCreate) ||
                  !hasPermission(user, PERMISSIONS.serviceInvoicesList)
                }
                locked={
                  !hasPermission(user, PERMISSIONS.ordersCreate) ||
                  !hasPermission(user, PERMISSIONS.serviceInvoicesList)
                }
                onClick={() => {
                  setBuilderOpen(true)
                  setBuilderInvoice(null)
                }}
              >
                <IconPlus size={14} />
                Create Order
              </CompactActionButton>
              {boardRefreshing ? <span className="commercial-count">Refreshing…</span> : null}
            </div>
          </header>

          <div className="commercial-filters">
            <select
              value={recordSearch.status ?? ''}
              onChange={(event) => setSearchValue('status', event.target.value)}
            >
              <option value="">All order statuses</option>
              {allOrderStatuses.map((status) => (
                <option key={status.value} value={status.value}>
                  {status.label}
                </option>
              ))}
            </select>
            {hasActiveFilters ? (
              <button
                type="button"
                className="commercial-btn commercial-btn-small"
                onClick={() => {
                  setSearchDraft('')
                  void navigate({
                    to: '/app/$section',
                    params: { section: 'service-orders' },
                    search: (previous) =>
                      withoutSearchKeys(previous, ['search', 'status', 'paymentStatus', 'page']),
                    replace: true,
                  })
                }}
              >
                Clear Filters
              </button>
            ) : null}
          </div>

          {listQuery.data.items.length === 0 ? (
            <EmptyState
              title={
                hasActiveFilters ? 'No Service Orders match these filters' : 'No Service Orders yet'
              }
              description={
                hasActiveFilters
                  ? 'Change or clear the filters to review other Orders.'
                  : 'Eligible paid or partially paid invoices can be mobilised into Service Orders.'
              }
            />
          ) : (
            <div className="commercial-table-wrap">
              <table className="commercial-table">
                <thead>
                  <tr>
                    <th>Order</th>
                    <th>Client</th>
                    <th>Service</th>
                    <th>Stage</th>
                    <th>Progress</th>
                    <th>Owner</th>
                    <th>Due</th>
                    <th>Payment</th>
                    <th>Status</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {listQuery.data.items.map((order) => (
                    <tr key={order.id}>
                      <td>
                        <b>{order.orderNumber}</b>
                        <small>{formatCurrency(order.amount)}</small>
                      </td>
                      <td>{clientNames.get(order.clientId) ?? `Client #${order.clientId}`}</td>
                      <td>{order.serviceName}</td>
                      <td>{order.stage || '—'}</td>
                      <td>
                        <b>{order.progress}%</b>
                      </td>
                      <td>
                        {order.assignedToId
                          ? (employeeNames.get(order.assignedToId) ??
                            `Employee #${order.assignedToId}`)
                          : 'Unassigned'}
                      </td>
                      <td>{order.dueDate ?? '—'}</td>
                      <td>{statusLabel(order.paymentStatus)}</td>
                      <td>
                        <span className={`commercial-pill ${statusClass(order.orderStatus)}`}>
                          {statusLabel(order.orderStatus)}
                        </span>
                      </td>
                      <td>
                        <button
                          type="button"
                          className="commercial-btn commercial-btn-small"
                          disabled={!hasPermission(user, PERMISSIONS.ordersView)}
                          onClick={() =>
                            void navigate({
                              to: '/app/$section',
                              params: { section: 'service-orders' },
                              search: (previous) => ({ ...previous, order: String(order.id) }),
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

      {sourceInvoiceId && handoffInvoiceQuery.isPending ? (
        <div className="commercial-modal-backdrop">
          <section className="commercial-modal">
            <div className="commercial-empty">Loading invoice…</div>
          </section>
        </div>
      ) : null}
      {sourceInvoiceId && handoffInvoiceQuery.isError ? (
        <div className="commercial-modal-backdrop">
          <section className="commercial-modal">
            <EmptyState
              title="Invoice could not be loaded"
              description={presentError(handoffInvoiceQuery.error, 'section-load').message}
            />
            <footer className="commercial-modal-footer">
              <button className="commercial-btn" onClick={closeBuilder}>
                Close
              </button>
              <button
                className="commercial-btn commercial-btn-primary"
                onClick={() => void handoffInvoiceQuery.refetch()}
              >
                Retry
              </button>
            </footer>
          </section>
        </div>
      ) : null}

      {builderOpen && !sourceInvoiceId && allInvoicesQuery.isPending ? (
        <div className="commercial-modal-backdrop">
          <section className="commercial-modal">
            <div className="commercial-empty">Loading eligible invoices…</div>
          </section>
        </div>
      ) : null}
      {builderOpen && !activeBuilderInvoice && !sourceInvoiceId && !allInvoicesQuery.isPending ? (
        <div className="commercial-modal-backdrop">
          <section className="commercial-modal">
            <EmptyState
              title="No invoices are ready for mobilisation"
              description="An invoice becomes eligible after its required payment threshold is met and before a Service Order has been created."
            />
            <footer className="commercial-modal-footer">
              <button className="commercial-btn" onClick={closeBuilder}>
                Close
              </button>
            </footer>
          </section>
        </div>
      ) : null}

      {builderOpen && activeBuilderInvoice ? (
        <CreateServiceOrderLiveWorkspace
          key={activeBuilderInvoice.id}
          invoice={activeBuilderInvoice}
          eligibleInvoices={builderInvoices}
          employees={employeesQuery.data ?? []}
          invoiceSelectionLocked={Boolean(sourceInvoiceId)}
          invoiceSelectionLoading={builderInvoiceLoading}
          saving={createMutation.isPending}
          onSelectInvoice={(invoiceId) => void selectBuilderInvoice(invoiceId)}
          onClose={closeBuilder}
          onSubmit={(input) => createMutation.mutate(input)}
        />
      ) : null}

      {selectedOrderId && detailQuery.isPending ? (
        <div className="commercial-modal-backdrop">
          <section className="commercial-modal">
            <div className="commercial-empty">Loading Service Order…</div>
          </section>
        </div>
      ) : null}
      {selectedOrderId && detailQuery.isError ? (
        <div className="commercial-modal-backdrop">
          <section className="commercial-modal">
            <EmptyState
              title="Service Order could not be opened"
              description={presentError(detailQuery.error, 'section-load').message}
            />
            <footer className="commercial-modal-footer">
              <button
                className="commercial-btn"
                onClick={() =>
                  void navigate({
                    to: '/app/$section',
                    params: { section: 'service-orders' },
                    search: (previous) => withoutSearchKeys(previous, ['order']),
                  })
                }
              >
                Close
              </button>
              <button
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
        <OrderControlRoomLiveWorkspace
          key={`${detailQuery.data.id}-${detailQuery.data.updatedAt}`}
          order={detailQuery.data}
          clientName={
            clientNames.get(detailQuery.data.clientId) ?? `Client #${detailQuery.data.clientId}`
          }
          assignedEmployeeName={
            detailQuery.data.assignedToId
              ? (employeeNames.get(detailQuery.data.assignedToId) ??
                `Employee #${detailQuery.data.assignedToId}`)
              : 'Unassigned'
          }
          invoiceNumber={
            linkedInvoiceQuery.data?.invoiceNumber ??
            (detailQuery.data.invoiceId ? `Invoice #${detailQuery.data.invoiceId}` : '—')
          }
          employees={employeesQuery.data ?? []}
          saving={busy}
          canUpdate={hasPermission(user, PERMISSIONS.ordersUpdate)}
          onClose={() =>
            void navigate({
              to: '/app/$section',
              params: { section: 'service-orders' },
              search: (previous) => withoutSearchKeys(previous, ['order']),
            })
          }
          onUpdate={(input) => updateMutation.mutate({ orderId: detailQuery.data.id, input })}
          onCompleteMilestone={(milestoneId) =>
            completeMutation.mutate({ orderId: detailQuery.data.id, milestoneId })
          }
          onAddActivity={(input) =>
            activityMutation.mutate({ orderId: detailQuery.data.id, input })
          }
          onAddMilestone={(input) =>
            milestoneMutation.mutate({ orderId: detailQuery.data.id, input })
          }
          onOpenTasks={() =>
            void navigate({
              to: '/app/$section',
              params: { section: 'execution-tasks' },
              search: { order: String(detailQuery.data.id) },
            })
          }
          onOpenDeliverables={() =>
            void navigate({
              to: '/app/$section',
              params: { section: 'deliverables' },
              search: { order: String(detailQuery.data.id) },
            })
          }
        />
      ) : null}
    </ModulePageFrame>
  )
}
