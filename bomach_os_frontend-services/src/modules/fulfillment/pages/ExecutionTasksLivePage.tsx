import { IconFilePlus, IconPlus, IconRefresh, IconSearch } from '@tabler/icons-react'
import { useMutation, useQueries, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from '@tanstack/react-router'
import { useCallback, useEffect, useMemo, useState } from 'react'

import { useAuth } from '@/app/auth'
import { SectionLoadingState } from '@/app/loading/SectionLoadingState'
import { hasPermission, PERMISSIONS } from '@/app/permissions'
import type { AppSectionSearch } from '@/routes/app/$section'
import { presentError } from '@/shared/errors'
import { withOptionalSearchValue, withoutSearchKeys } from '@/shared/navigation/search-state'
import { ConfirmDialog } from '@/shared/ui/confirm-dialog'
import { ErrorState, useToast } from '@/shared/ui'
import { EmptyState } from '@/shared/ui/empty-state'
import {
  CompactActionButton,
  CompactPageToolbar,
  ModulePageFrame,
  ModulePageStatus,
} from '@/shared/ui/module-controls'

import { executionTaskApi } from '../execution-tasks/execution-task.api'
import { executionTaskKeys } from '../execution-tasks/execution-task.keys'
import { executionTaskQueries } from '../execution-tasks/execution-task.queries'
import {
  executionTaskBoardStatuses,
  executionTaskPriorities,
  type ExecutionTask,
} from '../execution-tasks/execution-task.types'
import { serviceOrderKeys } from '../service-orders/service-order.keys'
import { serviceOrderQueries } from '../service-orders/service-order.queries'
import { CreateExecutionTaskLiveWorkspace } from '../workspaces/CreateExecutionTaskLiveWorkspace'
import { ExecutionTaskDetailLiveWorkspace } from '../workspaces/ExecutionTaskDetailLiveWorkspace'
import '../styles/fulfillment.css'
import '../../commercial/styles/commercial.css'

function label(value: string) {
  return value.replaceAll('_', ' ').replace(/\b\w/g, (letter) => letter.toUpperCase())
}

function priorityClass(priority: ExecutionTask['priority']) {
  if (priority === 'critical') return 'fulfillment-pill-red'
  if (priority === 'high') return 'fulfillment-pill-yellow'
  return 'fulfillment-pill-gray'
}

export function ExecutionTasksLivePage({ recordSearch }: { recordSearch: AppSectionSearch }) {
  const { user } = useAuth()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const toast = useToast()

  const selectedOrderId = recordSearch.order ? Number(recordSearch.order) : null
  const selectedTaskId = recordSearch.task ? Number(recordSearch.task) : null
  const [createOpen, setCreateOpen] = useState(false)
  const [confirmAction, setConfirmAction] = useState<
    | { kind: 'cancel'; orderId: number; taskId: number; taskNumber: string }
    | { kind: 'delete'; orderId: number; taskId: number; taskNumber: string }
    | null
  >(null)
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
    enabled: Boolean(selectedOrderId) && hasPermission(user, PERMISSIONS.employeesList),
    retry: false,
  })

  const boardQueries = useQueries({
    queries: executionTaskBoardStatuses.map((column) => ({
      ...executionTaskQueries.list(selectedOrderId ?? 0, {
        status: column.value,
        ...(recordSearch.priority
          ? { priority: recordSearch.priority as ExecutionTask['priority'] }
          : {}),
        ...(recordSearch.search ? { search: recordSearch.search } : {}),
        page: 1,
        limit: 8,
      }),
      enabled: Boolean(selectedOrderId) && canViewOrders,
    })),
  })

  const cancelledQuery = useQuery({
    ...executionTaskQueries.list(selectedOrderId ?? 0, {
      status: 'cancelled',
      ...(recordSearch.priority
        ? { priority: recordSearch.priority as ExecutionTask['priority'] }
        : {}),
      ...(recordSearch.search ? { search: recordSearch.search } : {}),
      page: 1,
      limit: 10,
    }),
    enabled: Boolean(selectedOrderId) && canViewOrders && recordSearch.status === 'cancelled',
  })

  const taskDetailQuery = useQuery({
    ...executionTaskQueries.detail(selectedOrderId ?? 0, selectedTaskId ?? 0),
    enabled: Boolean(selectedOrderId) && Boolean(selectedTaskId) && canViewOrders,
  })

  const setSearchValue = useCallback(
    function <Key extends keyof AppSectionSearch>(
      key: Key,
      value: AppSectionSearch[Key] | '' | null,
    ) {
      void navigate({
        to: '/app/$section',
        params: { section: 'execution-tasks' },
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

  const invalidateTasks = async (orderId: number, taskId?: number) => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: executionTaskKeys.lists(orderId) }),
      ...(taskId
        ? [queryClient.invalidateQueries({ queryKey: executionTaskKeys.detail(orderId, taskId) })]
        : []),
      queryClient.invalidateQueries({ queryKey: serviceOrderKeys.detail(orderId) }),
      queryClient.invalidateQueries({ queryKey: serviceOrderKeys.lists() }),
    ])
  }

  const createMutation = useMutation({
    mutationFn: ({
      orderId,
      input,
    }: {
      orderId: number
      input: Parameters<typeof executionTaskApi.create>[1]
    }) => {
      if (!orderId) throw new Error('Select a Service Order before creating a Task.')
      return executionTaskApi.create(orderId, input)
    },
    onSuccess: async (task) => {
      await invalidateTasks(task.orderId, task.id)
      setCreateOpen(false)
      toast.success(`Execution Task ${task.taskNumber} created`)
      await navigate({
        to: '/app/$section',
        params: { section: 'execution-tasks' },
        search: (previous) => ({ ...previous, order: String(task.orderId), task: String(task.id) }),
      })
    },
    onError: (error) => {
      toast.error('Execution Task could not be created', {
        description: presentError(error, 'form-submit').message,
      })
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({
      orderId,
      taskId,
      input,
    }: {
      orderId: number
      taskId: number
      input: Parameters<typeof executionTaskApi.update>[2]
    }) => executionTaskApi.update(orderId, taskId, input),
    onSuccess: async (task) => {
      await invalidateTasks(task.orderId, task.id)
      toast.success('Execution Task updated')
    },
    onError: (error) => {
      toast.error('Execution Task could not be updated', {
        description: presentError(error, 'form-submit').message,
      })
    },
  })

  const advanceMutation = useMutation({
    mutationFn: ({ orderId, taskId }: { orderId: number; taskId: number }) =>
      executionTaskApi.advance(orderId, taskId),
    onSuccess: async (task) => {
      await invalidateTasks(task.orderId, task.id)
      toast.success(`Task advanced to ${label(task.status)}`)
    },
    onError: (error) => {
      toast.error('Task could not be advanced', {
        description: presentError(error, 'background-action').message,
      })
    },
  })

  const cancelMutation = useMutation({
    mutationFn: ({ orderId, taskId }: { orderId: number; taskId: number }) =>
      executionTaskApi.cancel(orderId, taskId),
    onSuccess: async (task) => {
      await invalidateTasks(task.orderId, task.id)
      toast.success('Execution Task cancelled')
    },
    onError: (error) => {
      toast.error('Task could not be cancelled', {
        description: presentError(error, 'background-action').message,
      })
    },
  })

  const deleteMutation = useMutation({
    mutationFn: ({ orderId, taskId }: { orderId: number; taskId: number }) =>
      executionTaskApi.remove(orderId, taskId),
    onSuccess: async (_result, variables) => {
      await invalidateTasks(variables.orderId)
      toast.success('Execution Task deleted')
      await navigate({
        to: '/app/$section',
        params: { section: 'execution-tasks' },
        search: (previous) => withoutSearchKeys(previous, ['task']),
        replace: true,
      })
    },
    onError: (error) => {
      toast.error('Task could not be deleted', {
        description: presentError(error, 'background-action').message,
      })
    },
  })

  const refresh = async () => {
    await Promise.all([
      selectedOrderQuery.refetch(),
      ...boardQueries.map((query) => query.refetch()),
      ...(recordSearch.status === 'cancelled' ? [cancelledQuery.refetch()] : []),
    ])
    toast.success('Execution Tasks refreshed')
  }

  const orderOptions = useMemo(() => ordersQuery.data?.items ?? [], [ordersQuery.data?.items])

  const selectedOrder = selectedOrderQuery.data ?? null
  const employeeNames = useMemo(
    () => new Map((employeesQuery.data ?? []).map((employee) => [employee.id, employee.name])),
    [employeesQuery.data],
  )
  const milestoneNames = useMemo(
    () =>
      new Map((selectedOrder?.milestones ?? []).map((milestone) => [milestone.id, milestone.name])),
    [selectedOrder?.milestones],
  )

  const busy =
    createMutation.isPending ||
    updateMutation.isPending ||
    advanceMutation.isPending ||
    cancelMutation.isPending ||
    deleteMutation.isPending
  const boardRefreshing = boardQueries.some((query) => query.isFetching)

  if (!selectedOrderId && canListOrders && ordersQuery.isPending) {
    return <SectionLoadingState section="execution-tasks" />
  }

  if (!selectedOrderId && canListOrders && ordersQuery.isError) {
    const error = presentError(ordersQuery.error, 'page-load')
    return (
      <ModulePageStatus title="Execution Tasks" breadcrumb="Fulfillment / Tasks">
        <ErrorState
          title={error.title}
          description={error.message}
          onRetry={() => void ordersQuery.refetch()}
        />
      </ModulePageStatus>
    )
  }

  return (
    <ModulePageFrame
      header={
        <CompactPageToolbar
          title="Execution Tasks"
          breadcrumb="Fulfillment / Tasks"
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
              disabled={!hasPermission(user, PERMISSIONS.servicesCreate)}
              locked={!hasPermission(user, PERMISSIONS.servicesCreate)}
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
      <main className="fulfillment-content">
        <section className="commercial-card">
          <header className="commercial-card-header">
            <div>
              <h2>Execution Task Board</h2>
              <p>Service delivery work progresses through To Do, In Progress, Review and Done.</p>
            </div>
            <div className="commercial-card-header-actions">
              {boardRefreshing ? <span className="commercial-count">Refreshing…</span> : null}
              <CompactActionButton
                disabled={!selectedOrderId || boardRefreshing}
                onClick={() => void refresh()}
              >
                <IconRefresh size={14} /> Refresh
              </CompactActionButton>
              <CompactActionButton
                tone="primary"
                disabled={!canUpdateOrders}
                locked={!canUpdateOrders}
                onClick={() => setCreateOpen(true)}
              >
                <IconPlus size={14} />
                New Task
              </CompactActionButton>
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
                  params: { section: 'execution-tasks' },
                  search: (previous) => ({
                    ...withoutSearchKeys(previous, ['order', 'task']),
                    ...(orderId ? { order: orderId } : {}),
                  }),
                })
              }}
            >
              <option value="">Select Service Order</option>
              {orderOptions.map((order) => (
                <option key={order.id} value={order.id}>
                  {order.orderNumber} · {order.serviceName}
                </option>
              ))}
            </select>

            <label className="commercial-search">
              <IconSearch size={14} />
              <input
                value={searchDraft}
                disabled={!selectedOrderId}
                onChange={(event) => setSearchDraft(event.target.value)}
                placeholder="Search task number, title or description"
              />
            </label>

            <select
              value={recordSearch.priority ?? ''}
              disabled={!selectedOrderId}
              onChange={(event) => setSearchValue('priority', event.target.value)}
            >
              <option value="">All priorities</option>
              {executionTaskPriorities.map((priority) => (
                <option key={priority.value} value={priority.value}>
                  {priority.label}
                </option>
              ))}
            </select>

            <select
              value={recordSearch.status ?? ''}
              disabled={!selectedOrderId}
              onChange={(event) => setSearchValue('status', event.target.value)}
            >
              <option value="">Active board</option>
              <option value="cancelled">Cancelled tasks</option>
            </select>
          </div>

          {!selectedOrderId ? (
            <EmptyState
              title="Select a Service Order"
              description={
                canListOrders
                  ? 'Select a Service Order to view its tasks and create new work items.'
                  : 'Your account cannot list Service Orders. Open Execution Tasks from a Service Order Control Room or request the orders.list permission.'
              }
            />
          ) : !canViewOrders ? (
            <EmptyState
              title="Service Order access required"
              description="The Service Execution Task API requires orders.view to read Tasks."
            />
          ) : selectedOrderQuery.isPending ? (
            <div className="commercial-empty">Loading Service Order…</div>
          ) : selectedOrderQuery.isError ? (
            <ErrorState
              title="Service Order could not be loaded"
              description={presentError(selectedOrderQuery.error, 'section-load').message}
              onRetry={() => void selectedOrderQuery.refetch()}
            />
          ) : recordSearch.status === 'cancelled' ? (
            cancelledQuery.isPending ? (
              <div className="commercial-empty">Loading cancelled Tasks…</div>
            ) : cancelledQuery.isError ? (
              <ErrorState
                title="Cancelled Tasks could not be loaded"
                description={presentError(cancelledQuery.error, 'section-load').message}
                onRetry={() => void cancelledQuery.refetch()}
              />
            ) : cancelledQuery.data.items.length === 0 ? (
              <EmptyState
                title="No cancelled Tasks"
                description="This Service Order has no cancelled Execution Tasks matching the current filters."
              />
            ) : (
              <div className="commercial-table-wrap">
                <table className="commercial-table">
                  <thead>
                    <tr>
                      <th>Task</th>
                      <th>Milestone</th>
                      <th>Owner</th>
                      <th>Priority</th>
                      <th>Due</th>
                      <th />
                    </tr>
                  </thead>
                  <tbody>
                    {cancelledQuery.data.items.map((task) => (
                      <tr key={task.id}>
                        <td>
                          <b>{task.title}</b>
                          <small>{task.taskNumber}</small>
                        </td>
                        <td>
                          {task.milestoneId
                            ? (milestoneNames.get(task.milestoneId) ??
                              `Milestone #${task.milestoneId}`)
                            : '—'}
                        </td>
                        <td>
                          {task.ownerId
                            ? (employeeNames.get(task.ownerId) ?? `Employee #${task.ownerId}`)
                            : 'Unassigned'}
                        </td>
                        <td>
                          <span className={`fulfillment-pill ${priorityClass(task.priority)}`}>
                            {label(task.priority)}
                          </span>
                        </td>
                        <td>{task.dueDate ?? '—'}</td>
                        <td>
                          <button
                            type="button"
                            className="commercial-btn commercial-btn-small"
                            onClick={() =>
                              void navigate({
                                to: '/app/$section',
                                params: { section: 'execution-tasks' },
                                search: (previous) => ({ ...previous, task: String(task.id) }),
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
            )
          ) : (
            <div className="fulfillment-kanban">
              {executionTaskBoardStatuses.map((column, index) => {
                const query = boardQueries[index]!
                const tasks = query.data?.items ?? []

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
                    ) : tasks.length === 0 ? (
                      <div className="fulfillment-empty fulfillment-empty-column">No tasks</div>
                    ) : (
                      tasks.map((task) => (
                        <button
                          type="button"
                          className="fulfillment-task-card"
                          key={task.id}
                          onClick={() =>
                            void navigate({
                              to: '/app/$section',
                              params: { section: 'execution-tasks' },
                              search: (previous) => ({ ...previous, task: String(task.id) }),
                            })
                          }
                        >
                          <b>{task.title}</b>
                          <small>
                            {task.taskNumber}
                            {task.milestoneId
                              ? ` · ${milestoneNames.get(task.milestoneId) ?? `Milestone #${task.milestoneId}`}`
                              : ''}
                          </small>
                          <small>
                            {task.ownerId
                              ? (employeeNames.get(task.ownerId) ?? `Employee #${task.ownerId}`)
                              : 'Unassigned'}
                            {task.assigneeIds.length
                              ? ` · ${task.assigneeIds.length} assignee${task.assigneeIds.length === 1 ? '' : 's'}`
                              : ''}
                          </small>
                          <div className="fulfillment-task-footer">
                            <span className={`fulfillment-pill ${priorityClass(task.priority)}`}>
                              {label(task.priority)}
                            </span>
                            <span className="fulfillment-row-sub">
                              {task.dueDate ? `Due ${task.dueDate}` : 'No due date'}
                            </span>
                          </div>
                        </button>
                      ))
                    )}
                  </section>
                )
              })}
            </div>
          )}
        </section>
      </main>

      {createOpen ? (
        <CreateExecutionTaskLiveWorkspace
          key={selectedOrder?.id ?? 'new-task'}
          order={selectedOrder}
          orders={ordersQuery.data?.items ?? []}
          employees={employeesQuery.data ?? []}
          saving={createMutation.isPending}
          onClose={() => setCreateOpen(false)}
          onSubmit={(orderId, input) => createMutation.mutate({ orderId, input })}
        />
      ) : null}

      {selectedTaskId && taskDetailQuery.isPending ? (
        <div className="commercial-modal-backdrop">
          <section className="commercial-modal">
            <div className="commercial-empty">Loading Execution Task…</div>
          </section>
        </div>
      ) : null}

      {selectedTaskId && taskDetailQuery.isError ? (
        <div className="commercial-modal-backdrop">
          <section className="commercial-modal">
            <EmptyState
              title="Execution Task could not be opened"
              description={presentError(taskDetailQuery.error, 'section-load').message}
            />
            <footer className="commercial-modal-footer">
              <button
                className="commercial-btn"
                onClick={() =>
                  void navigate({
                    to: '/app/$section',
                    params: { section: 'execution-tasks' },
                    search: (previous) => withoutSearchKeys(previous, ['task']),
                  })
                }
              >
                Close
              </button>
              <button
                className="commercial-btn commercial-btn-primary"
                onClick={() => void taskDetailQuery.refetch()}
              >
                Retry
              </button>
            </footer>
          </section>
        </div>
      ) : null}

      {taskDetailQuery.data && selectedOrder ? (
        <ExecutionTaskDetailLiveWorkspace
          key={`${taskDetailQuery.data.id}-${taskDetailQuery.data.updatedAt}`}
          task={taskDetailQuery.data}
          order={selectedOrder}
          employees={employeesQuery.data ?? []}
          saving={busy}
          canUpdate={canUpdateOrders}
          onClose={() =>
            void navigate({
              to: '/app/$section',
              params: { section: 'execution-tasks' },
              search: (previous) => withoutSearchKeys(previous, ['task']),
            })
          }
          onUpdate={(input) =>
            updateMutation.mutate({
              orderId: selectedOrder.id,
              taskId: taskDetailQuery.data.id,
              input,
            })
          }
          onAdvance={() =>
            advanceMutation.mutate({
              orderId: selectedOrder.id,
              taskId: taskDetailQuery.data.id,
            })
          }
          onCancel={() => {
            setConfirmAction({
              kind: 'cancel',
              orderId: selectedOrder.id,
              taskId: taskDetailQuery.data.id,
              taskNumber: taskDetailQuery.data.taskNumber,
            })
          }}
          onDelete={() => {
            setConfirmAction({
              kind: 'delete',
              orderId: selectedOrder.id,
              taskId: taskDetailQuery.data.id,
              taskNumber: taskDetailQuery.data.taskNumber,
            })
          }}
        />
      ) : null}

      <ConfirmDialog
        open={confirmAction !== null}
        tone={confirmAction?.kind === 'delete' ? 'danger' : 'warning'}
        title={
          confirmAction?.kind === 'delete' ? 'Delete execution task?' : 'Cancel execution task?'
        }
        description={
          confirmAction?.kind === 'delete'
            ? 'This removes the task from the service order and cannot be undone.'
            : 'This will mark the task as cancelled.'
        }
        confirmLabel={confirmAction?.kind === 'delete' ? 'Delete Task' : 'Cancel Task'}
        cancelLabel="Keep Task"
        isConfirming={deleteMutation.isPending || cancelMutation.isPending}
        onCancel={() => setConfirmAction(null)}
        onConfirm={() => {
          if (!confirmAction) return
          if (confirmAction.kind === 'delete') {
            deleteMutation.mutate({
              orderId: confirmAction.orderId,
              taskId: confirmAction.taskId,
            })
          } else {
            cancelMutation.mutate({
              orderId: confirmAction.orderId,
              taskId: confirmAction.taskId,
            })
          }
          setConfirmAction(null)
        }}
      />
    </ModulePageFrame>
  )
}
