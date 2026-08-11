import { IconFilePlus, IconPlus, IconRefresh, IconSearch } from '@tabler/icons-react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from '@tanstack/react-router'
import { useCallback, useEffect, useMemo, useState } from 'react'

import { useAuth } from '@/app/auth'
import { hasPermission, PERMISSIONS } from '@/app/permissions'
import { approvalQueueKeys } from '@/modules/commercial/approval-queue/approval-queue.keys'
import type { AppSectionSearch } from '@/routes/app/$section'
import { presentError } from '@/shared/errors'
import { withOptionalSearchValue, withoutSearchKeys } from '@/shared/navigation/search-state'
import { DashboardSkeleton, ErrorState, useToast } from '@/shared/ui'
import { ConfirmDialog } from '@/shared/ui/confirm-dialog'
import { EmptyState } from '@/shared/ui/empty-state'
import {
  CompactActionButton,
  CompactPageToolbar,
  ModulePageFrame,
  ModulePageStatus,
} from '@/shared/ui/module-controls'

import {
  canDeleteDeliverable,
  canReviewDeliverable,
} from '../deliverables/deliverable-capabilities'
import { deliverableApi } from '../deliverables/deliverable.api'
import { deliverableKeys } from '../deliverables/deliverable.keys'
import { deliverableQueries } from '../deliverables/deliverable.queries'
import {
  deliverableStatuses,
  deliverableTypes,
  type Deliverable,
  type DeliverableStatus,
  type DeliverableType,
} from '../deliverables/deliverable.types'
import { executionTaskQueries } from '../execution-tasks/execution-task.queries'
import { serviceOrderKeys } from '../service-orders/service-order.keys'
import { serviceOrderQueries } from '../service-orders/service-order.queries'
import { CreateDeliverableLiveWorkspace } from '../workspaces/CreateDeliverableLiveWorkspace'
import { DeliverableDetailLiveWorkspace } from '../workspaces/DeliverableDetailLiveWorkspace'
import '../../commercial/styles/commercial.css'
import '../styles/fulfillment.css'

function label(value: string) {
  return value.replaceAll('_', ' ').replace(/\b\w/g, (letter) => letter.toUpperCase())
}

function statusClass(status: DeliverableStatus) {
  if (status === 'approved') return 'fulfillment-pill-green'
  if (status === 'under_review') return 'fulfillment-pill-blue'
  if (status === 'rejected') return 'fulfillment-pill-red'
  if (status === 'superseded') return 'fulfillment-pill-gray'
  return 'fulfillment-pill-yellow'
}

export function DeliverablesLivePage({ recordSearch }: { recordSearch: AppSectionSearch }) {
  const { user } = useAuth()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const toast = useToast()

  const selectedOrderId = recordSearch.order ? Number(recordSearch.order) : null
  const selectedDeliverableId = recordSearch.deliverable ? Number(recordSearch.deliverable) : null
  const page = recordSearch.page ?? 1
  const pageSize = 12

  const [createOpen, setCreateOpen] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState<Deliverable | null>(null)
  const [searchDraft, setSearchDraft] = useState(recordSearch.search ?? '')
  const [syncedSearch, setSyncedSearch] = useState(recordSearch.search ?? '')

  const canListOrders = hasPermission(user, PERMISSIONS.ordersList)
  const canViewOrders = hasPermission(user, PERMISSIONS.ordersView)
  const canUpdateOrders = hasPermission(user, PERMISSIONS.ordersUpdate)

  const ordersQuery = useQuery({
    ...serviceOrderQueries.list({ page: 1, limit: 100 }),
    enabled: canListOrders,
  })

  const selectedOrderQuery = useQuery({
    ...serviceOrderQueries.detail(selectedOrderId ?? 0),
    enabled: Boolean(selectedOrderId) && canViewOrders,
  })

  const employeesQuery = useQuery({
    ...serviceOrderQueries.employees(),
    enabled: (Boolean(selectedOrderId) || createOpen) && hasPermission(user, PERMISSIONS.employeesList),
    retry: false,
  })

  const listQuery = useQuery({
    ...deliverableQueries.list(selectedOrderId ?? 0, {
      ...(recordSearch.status ? { status: recordSearch.status as DeliverableStatus } : {}),
      ...(recordSearch.deliverableType
        ? { deliverableType: recordSearch.deliverableType as DeliverableType }
        : {}),
      ...(recordSearch.clientVisible === 'true'
        ? { clientVisible: true }
        : recordSearch.clientVisible === 'false'
          ? { clientVisible: false }
          : {}),
      ...(recordSearch.search ? { search: recordSearch.search } : {}),
      page,
      limit: pageSize,
    }),
    enabled: Boolean(selectedOrderId) && canViewOrders,
  })

  const tasksQuery = useQuery({
    ...executionTaskQueries.list(selectedOrderId ?? 0, { page: 1, limit: 100 }),
    enabled: Boolean(selectedOrderId) && canViewOrders,
  })

  const detailQuery = useQuery({
    ...deliverableQueries.detail(selectedOrderId ?? 0, selectedDeliverableId ?? 0),
    enabled: Boolean(selectedOrderId) && Boolean(selectedDeliverableId) && canViewOrders,
  })

  const setSearchValue = useCallback(
    function <Key extends keyof AppSectionSearch>(
      key: Key,
      value: AppSectionSearch[Key] | '' | null,
    ) {
      void navigate({
        to: '/app/$section',
        params: { section: 'deliverables' },
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

  const invalidateDeliverables = async (orderId: number, deliverableId?: number) => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: deliverableKeys.lists(orderId) }),
      ...(deliverableId
        ? [queryClient.invalidateQueries({ queryKey: deliverableKeys.detail(orderId, deliverableId) })]
        : []),
      queryClient.invalidateQueries({ queryKey: serviceOrderKeys.detail(orderId) }),
      queryClient.invalidateQueries({ queryKey: serviceOrderKeys.lists() }),
      queryClient.invalidateQueries({ queryKey: approvalQueueKeys.all }),
    ])
  }

  const createMutation = useMutation({
    mutationFn: ({ orderId, input }: { orderId: number; input: Parameters<typeof deliverableApi.create>[1] }) =>
      deliverableApi.create(orderId, input),
    onSuccess: async (deliverable) => {
      await invalidateDeliverables(deliverable.orderId, deliverable.id)
      setCreateOpen(false)
      toast.success(`Deliverable ${deliverable.deliverableNumber} added`)
      await navigate({
        to: '/app/$section',
        params: { section: 'deliverables' },
        search: (previous) => ({
          ...previous,
          order: String(deliverable.orderId),
          deliverable: String(deliverable.id),
        }),
      })
    },
    onError: (error) => {
      toast.error('Deliverable could not be added', {
        description: presentError(error, 'form-submit').message,
      })
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({
      orderId,
      deliverableId,
      input,
    }: {
      orderId: number
      deliverableId: number
      input: Parameters<typeof deliverableApi.update>[2]
    }) => deliverableApi.update(orderId, deliverableId, input),
    onSuccess: async (deliverable) => {
      await invalidateDeliverables(deliverable.orderId, deliverable.id)
      toast.success('Deliverable updated')
    },
    onError: (error) => {
      toast.error('Deliverable could not be updated', {
        description: presentError(error, 'form-submit').message,
      })
    },
  })

  const approveMutation = useMutation({
    mutationFn: ({ orderId, deliverableId }: { orderId: number; deliverableId: number }) =>
      deliverableApi.approve(orderId, deliverableId),
    onSuccess: async (deliverable) => {
      await invalidateDeliverables(deliverable.orderId, deliverable.id)
      toast.success('Deliverable approved')
    },
    onError: (error) => {
      toast.error('Deliverable could not be approved', {
        description: presentError(error, 'background-action').message,
      })
    },
  })

  const rejectMutation = useMutation({
    mutationFn: ({
      orderId,
      deliverableId,
      reason,
    }: {
      orderId: number
      deliverableId: number
      reason: string
    }) => deliverableApi.reject(orderId, deliverableId, reason),
    onSuccess: async (deliverable) => {
      await invalidateDeliverables(deliverable.orderId, deliverable.id)
      toast.success('Deliverable rejected')
    },
    onError: (error) => {
      toast.error('Deliverable could not be rejected', {
        description: presentError(error, 'background-action').message,
      })
    },
  })

  const deleteMutation = useMutation({
    mutationFn: ({ orderId, deliverableId }: { orderId: number; deliverableId: number }) =>
      deliverableApi.remove(orderId, deliverableId),
    onSuccess: async (_response, variables) => {
      await invalidateDeliverables(variables.orderId)
      setDeleteTarget(null)
      toast.success('Deliverable deleted')
      await navigate({
        to: '/app/$section',
        params: { section: 'deliverables' },
        search: (previous) => withoutSearchKeys(previous, ['deliverable']),
        replace: true,
      })
    },
    onError: (error) => {
      toast.error('Deliverable could not be deleted', {
        description: presentError(error, 'background-action').message,
      })
    },
  })

  const refresh = async () => {
    await Promise.all([selectedOrderQuery.refetch(), listQuery.refetch(), tasksQuery.refetch()])
    toast.success('Deliverables refreshed')
  }

  const orderOptions = useMemo(() => ordersQuery.data?.items ?? [], [ordersQuery.data?.items])
  const selectedOrder = selectedOrderQuery.data ?? null
  const employeeNames = useMemo(
    () => new Map((employeesQuery.data ?? []).map((employee) => [employee.id, employee.name])),
    [employeesQuery.data],
  )
  const taskNames = useMemo(
    () => new Map((tasksQuery.data?.items ?? []).map((task) => [task.id, `${task.taskNumber} · ${task.title}`])),
    [tasksQuery.data?.items],
  )
  const milestoneNames = useMemo(
    () => new Map((selectedOrder?.milestones ?? []).map((milestone) => [milestone.id, milestone.name])),
    [selectedOrder?.milestones],
  )

  const totalPages = Math.max(1, Math.ceil((listQuery.data?.count ?? 0) / pageSize))
  const busy =
    createMutation.isPending ||
    updateMutation.isPending ||
    approveMutation.isPending ||
    rejectMutation.isPending ||
    deleteMutation.isPending
  const hasFilters = Boolean(
    recordSearch.search || recordSearch.status || recordSearch.deliverableType || recordSearch.clientVisible,
  )

  if (!selectedOrderId && canListOrders && ordersQuery.isPending) {
    return <ModulePageStatus title="Deliverables & Documents" breadcrumb="Fulfillment / Documents"><DashboardSkeleton /></ModulePageStatus>
  }

  if (!selectedOrderId && canListOrders && ordersQuery.isError) {
    const error = presentError(ordersQuery.error, 'page-load')
    return <ModulePageStatus title="Deliverables & Documents" breadcrumb="Fulfillment / Documents"><ErrorState title={error.title} description={error.message} onRetry={() => void ordersQuery.refetch()} /></ModulePageStatus>
  }

  return (
    <ModulePageFrame
      header={
        <CompactPageToolbar
          title="Deliverables & Documents"
          breadcrumb="Fulfillment / Documents"
          secondaryAction={
            <CompactActionButton
              disabled={!hasPermission(user, PERMISSIONS.serviceRequestsCreate)}
              locked={!hasPermission(user, PERMISSIONS.serviceRequestsCreate)}
              onClick={() => void navigate({ to: '/app/$section', params: { section: 'service-requests' } })}
            >
              <IconFilePlus size={14} /> New Request
            </CompactActionButton>
          }
          primaryAction={
            <CompactActionButton
              tone="primary"
              disabled={!hasPermission(user, PERMISSIONS.servicesCreate)}
              locked={!hasPermission(user, PERMISSIONS.servicesCreate)}
              onClick={() => void navigate({ to: '/app/$section', params: { section: 'service-catalogue' } })}
            >
              <IconPlus size={14} /> Create Service
            </CompactActionButton>
          }
        />
      }
    >
      <main className="fulfillment-content">
        <section className="commercial-card">
          <header className="commercial-card-header">
            <div>
              <h2>Deliverables & Document Inbox</h2>
              <p>Reports, drawings, plans, certificates and approval-controlled outputs.</p>
            </div>
            <div className="commercial-card-header-actions">
              {listQuery.isFetching ? <span className="commercial-count">Refreshing…</span> : null}
              <CompactActionButton disabled={!selectedOrderId || listQuery.isFetching} onClick={() => void refresh()}><IconRefresh size={14} /> Refresh</CompactActionButton>
              <CompactActionButton tone="primary" disabled={!canUpdateOrders || (!selectedOrder && !canListOrders)} locked={!canUpdateOrders} onClick={() => setCreateOpen(true)}><IconPlus size={14} /> Add Deliverable</CompactActionButton>
            </div>
          </header>

          <div className="commercial-filters">
            <select
              value={selectedOrderId ?? ''}
              disabled={!canListOrders || ordersQuery.isPending}
              onChange={(event) => {
                const orderId = event.target.value
                setCreateOpen(false)
                void navigate({
                  to: '/app/$section',
                  params: { section: 'deliverables' },
                  search: (previous) => ({
                    ...withoutSearchKeys(previous, ['order', 'deliverable', 'page']),
                    ...(orderId ? { order: orderId } : {}),
                  }),
                })
              }}
            >
              <option value="">Select Service Order</option>
              {orderOptions.map((order) => <option key={order.id} value={order.id}>{order.orderNumber} · {order.serviceName}</option>)}
            </select>

            <label className="commercial-search"><IconSearch size={14} /><input value={searchDraft} disabled={!selectedOrderId} onChange={(event) => setSearchDraft(event.target.value)} placeholder="Search number, title or description" /></label>

            <select value={recordSearch.deliverableType ?? ''} disabled={!selectedOrderId} onChange={(event) => setSearchValue('deliverableType', event.target.value)}>
              <option value="">All types</option>
              {deliverableTypes.map((type) => <option key={type.value} value={type.value}>{type.label}</option>)}
            </select>

            <select value={recordSearch.status ?? ''} disabled={!selectedOrderId} onChange={(event) => setSearchValue('status', event.target.value)}>
              <option value="">All statuses</option>
              {deliverableStatuses.map((status) => <option key={status.value} value={status.value}>{status.label}</option>)}
            </select>

            <select value={recordSearch.clientVisible ?? ''} disabled={!selectedOrderId} onChange={(event) => setSearchValue('clientVisible', event.target.value)}>
              <option value="">All visibility</option>
              <option value="true">Client Visible</option>
              <option value="false">Internal Only</option>
            </select>

            {hasFilters ? <button type="button" className="commercial-btn commercial-btn-small" onClick={() => { setSearchDraft(''); void navigate({ to: '/app/$section', params: { section: 'deliverables' }, search: (previous) => withoutSearchKeys(previous, ['search','status','deliverableType','clientVisible','page']), replace: true }) }}>Clear Filters</button> : null}
          </div>

          {!selectedOrderId ? (
            <EmptyState title="Select a Service Order" description={canListOrders ? 'Select an Order to review its Deliverables. The backend does not yet expose a global Service Deliverable inbox endpoint.' : 'Open Deliverables from a Service Order Control Room or request Service Order list access.'} />
          ) : !canViewOrders ? (
            <EmptyState title="Service Order access required" description="The Service Deliverable API requires orders.view to read Deliverables." />
          ) : selectedOrderQuery.isPending || listQuery.isPending ? (
            <div className="commercial-empty">Loading Deliverables…</div>
          ) : selectedOrderQuery.isError || listQuery.isError ? (
            <ErrorState title="Deliverables could not be loaded" description={presentError(selectedOrderQuery.error ?? listQuery.error, 'section-load').message} onRetry={() => void refresh()} />
          ) : listQuery.data.items.length === 0 ? (
            <EmptyState title={hasFilters ? 'No Deliverables match these filters' : 'No Deliverables yet'} description={hasFilters ? 'Change or clear the filters to review other Deliverables.' : 'Add the first report, drawing, plan, certificate or handover output for this Service Order.'} />
          ) : (
            <div className="commercial-table-wrap">
              <table className="commercial-table">
                <thead><tr><th>Deliverable</th><th>Milestone / Task</th><th>Type</th><th>Version</th><th>Owner</th><th>Client Visible</th><th>Date</th><th>Status</th><th /></tr></thead>
                <tbody>
                  {listQuery.data.items.map((deliverable) => (
                    <tr key={deliverable.id}>
                      <td><b>{deliverable.title}</b><small>{deliverable.deliverableNumber}</small></td>
                      <td><b>{deliverable.milestoneId ? milestoneNames.get(deliverable.milestoneId) ?? `Milestone #${deliverable.milestoneId}` : 'No milestone'}</b><small>{deliverable.taskId ? taskNames.get(deliverable.taskId) ?? `Task #${deliverable.taskId}` : 'No task link'}</small></td>
                      <td>{label(deliverable.deliverableType)}</td>
                      <td>{deliverable.version}</td>
                      <td>{deliverable.ownerId ? employeeNames.get(deliverable.ownerId) ?? `Employee #${deliverable.ownerId}` : 'Unassigned'}</td>
                      <td>{deliverable.clientVisible ? 'Yes' : 'No'}</td>
                      <td>{deliverable.createdAt.slice(0, 10) || '—'}</td>
                      <td><span className={`fulfillment-pill ${statusClass(deliverable.status)}`}>{label(deliverable.status)}</span></td>
                      <td><button type="button" className="commercial-btn commercial-btn-small" onClick={() => void navigate({ to: '/app/$section', params: { section: 'deliverables' }, search: (previous) => ({ ...previous, deliverable: String(deliverable.id) }) })}>Open</button></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {selectedOrderId && listQuery.data ? <div className="commercial-table-pagination"><div className="commercial-table-pagination-summary"><span className="commercial-table-pagination-count">{listQuery.data.count} record{listQuery.data.count === 1 ? '' : 's'}</span><span className="commercial-table-pagination-divider" aria-hidden="true" /><span>Page <b>{page}</b> of <b>{totalPages}</b></span></div><div className="commercial-table-pagination-actions"><button type="button" className="commercial-btn commercial-btn-small" disabled={page <= 1} onClick={() => setSearchValue('page', page - 1)}>Previous</button><button type="button" className="commercial-btn commercial-btn-small" disabled={page >= totalPages} onClick={() => setSearchValue('page', page + 1)}>Next</button></div></div> : null}
        </section>
      </main>

      {createOpen ? <CreateDeliverableLiveWorkspace initialOrder={selectedOrder} orders={orderOptions} employees={employeesQuery.data ?? []} saving={createMutation.isPending} onClose={() => setCreateOpen(false)} onSubmit={(orderId, input) => createMutation.mutate({ orderId, input })} /> : null}

      {selectedDeliverableId && detailQuery.isPending ? <div className="commercial-modal-backdrop"><section className="commercial-modal"><div className="commercial-empty">Loading Deliverable…</div></section></div> : null}

      {selectedDeliverableId && detailQuery.isError ? <div className="commercial-modal-backdrop"><section className="commercial-modal"><EmptyState title="Deliverable could not be opened" description={presentError(detailQuery.error, 'section-load').message} /><footer className="commercial-modal-footer"><button className="commercial-btn" onClick={() => void navigate({ to: '/app/$section', params: { section: 'deliverables' }, search: (previous) => withoutSearchKeys(previous, ['deliverable']) })}>Close</button><button className="commercial-btn commercial-btn-primary" onClick={() => void detailQuery.refetch()}>Retry</button></footer></section></div> : null}

      {detailQuery.data && selectedOrder ? <DeliverableDetailLiveWorkspace key={`${detailQuery.data.id}-${detailQuery.data.updatedAt}`} deliverable={detailQuery.data} order={selectedOrder} tasks={tasksQuery.data?.items ?? []} employees={employeesQuery.data ?? []} saving={busy} canUpdate={canUpdateOrders} onClose={() => void navigate({ to: '/app/$section', params: { section: 'deliverables' }, search: (previous) => withoutSearchKeys(previous, ['deliverable']) })} onUpdate={(input) => updateMutation.mutate({ orderId: selectedOrder.id, deliverableId: detailQuery.data.id, input })} onApprove={() => { if (!canReviewDeliverable(detailQuery.data.status)) return; approveMutation.mutate({ orderId: selectedOrder.id, deliverableId: detailQuery.data.id }) }} onReject={(reason) => { if (!canReviewDeliverable(detailQuery.data.status)) return; rejectMutation.mutate({ orderId: selectedOrder.id, deliverableId: detailQuery.data.id, reason }) }} onDelete={() => { if (!canDeleteDeliverable(detailQuery.data.status)) return; setDeleteTarget(detailQuery.data) }} /> : null}

      <ConfirmDialog
        open={Boolean(deleteTarget)}
        title="Delete Deliverable?"
        description={
          deleteTarget
            ? `${deleteTarget.deliverableNumber} will be removed from this Service Order.`
            : ''
        }
        confirmLabel="Delete Deliverable"
        tone="danger"
        isConfirming={deleteMutation.isPending}
        onCancel={() => setDeleteTarget(null)}
        onConfirm={async () => {
          if (!deleteTarget) return
          await deleteMutation.mutateAsync({
            orderId: deleteTarget.orderId,
            deliverableId: deleteTarget.id,
          })
        }}
      />
    </ModulePageFrame>
  )
}
