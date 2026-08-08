import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import { IconFilePlus, IconPlus } from '@tabler/icons-react'

import { CompactPageToolbar, CompactActionButton, ModulePageFrame, ModulePageStatus } from '@/shared/ui/module-controls'
import { serviceAdministrationQueries } from '@/modules/service-administration/api/service-administration.queries'
import { presentError } from '@/shared/errors'
import { DashboardSkeleton, ErrorState, useToast } from '@/shared/ui'
import { canPerformAction } from '@/app/permissions'
import { useAuth } from '@/app/auth'
import { useDeepLinkedSelection, type AppRecordSearch } from '@/shared/navigation'

import { fulfillmentApi } from '../api/fulfillment.api'
import { fulfillmentKeys } from '../api/fulfillment.keys'
import { fulfillmentQueries } from '../api/fulfillment.queries'
import { DeliverablesScreen } from '../screens/DeliverablesScreen'
import { ExecutionTasksScreen } from '../screens/ExecutionTasksScreen'
import { ServiceOrdersScreen } from '../screens/ServiceOrdersScreen'
import type {
  AddMilestoneInput,
  CreateDeliverableInput,
  AddOrderUpdateInput,
  CreateExecutionTaskInput,
  CreateServiceOrderInput,
  FulfillmentSection,
  UpdateServiceOrderInput,
  UpdateExecutionTaskInput,
} from '../types/fulfillment.types'
import { CreateDeliverableWorkspace } from '../workspaces/CreateDeliverableWorkspace'
import { CreateOrderWorkspace } from '../workspaces/CreateOrderWorkspace'
import { CreateTaskWorkspace } from '../workspaces/CreateTaskWorkspace'
import { DeliverableDetailWorkspace } from '../workspaces/DeliverableDetailWorkspace'
import { OrderControlRoomWorkspace } from '../workspaces/OrderControlRoomWorkspace'
import { TaskDetailWorkspace } from '../workspaces/TaskDetailWorkspace'
import '../styles/fulfillment.css'

const metadata: Record<FulfillmentSection, { title: string; breadcrumb: string }> = {
  'service-orders': {
    title: 'Service Orders',
    breadcrumb: 'Fulfillment / Orders',
  },
  'execution-tasks': {
    title: 'Execution Tasks',
    breadcrumb: 'Fulfillment / Tasks',
  },
  deliverables: { title: 'Deliverables & Documents', breadcrumb: 'Fulfillment / Documents' },
}

export function FulfillmentSectionPage({
  section,
  recordSearch,
}: {
  section: FulfillmentSection
  recordSearch?: AppRecordSearch
}) {
  const queryClient = useQueryClient()
  const { user } = useAuth()
  const toast = useToast()

  const query = useQuery(fulfillmentQueries.workspace())
  const serviceQuery = useQuery(serviceAdministrationQueries.workspace())

  const [createOrderOpen, setCreateOrderOpen] = useState(false)
  const [createTaskOpen, setCreateTaskOpen] = useState(false)
  const [selectedOrderId, setSelectedOrderId] = useDeepLinkedSelection(recordSearch?.order)
  const [selectedTaskId, setSelectedTaskId] = useDeepLinkedSelection(recordSearch?.task)
  const [createDeliverableOrderId, setCreateDeliverableOrderId] = useState<string | null>(null)
  const [selectedDeliverableId, setSelectedDeliverableId] = useDeepLinkedSelection(
    recordSearch?.deliverable,
  )

  const updateCache = (workspace: NonNullable<typeof query.data>) => {
    queryClient.setQueryData(fulfillmentKeys.workspace(), workspace)
  }

  const createOrder = useMutation({
    mutationFn: (input: CreateServiceOrderInput) => fulfillmentApi.createOrder(input),
    onSuccess: (workspace) => {
      updateCache(workspace)
      setCreateOrderOpen(false)
      toast.success('Service order created')
    },
    onError: (error) => {
      const e = presentError(error, 'form-submit')
      toast.error('Service order could not be created', {
        description: e.message,
      })
    },
  })

  const updateOrder = useMutation({
    mutationFn: ({ orderId, input }: { orderId: string; input: UpdateServiceOrderInput }) =>
      fulfillmentApi.updateOrder(orderId, input),
    onSuccess: (workspace) => {
      updateCache(workspace)
      toast.success('Order updated')
    },
  })

  const advanceOrder = useMutation({
    mutationFn: (orderId: string) => fulfillmentApi.advanceOrder(orderId),
    onSuccess: (workspace) => {
      updateCache(workspace)
      toast.success('Order stage advanced')
    },
  })

  const addOrderUpdate = useMutation({
    mutationFn: (input: AddOrderUpdateInput) => fulfillmentApi.addOrderUpdate(input),
    onSuccess: (workspace) => {
      updateCache(workspace)
      toast.success('Order update recorded')
    },
  })

  const addMilestone = useMutation({
    mutationFn: (input: AddMilestoneInput) => fulfillmentApi.addMilestone(input),
    onSuccess: (workspace) => {
      updateCache(workspace)
      toast.success('Milestone added')
    },
  })

  const createTask = useMutation({
    mutationFn: (input: CreateExecutionTaskInput) => fulfillmentApi.createTask(input),
    onSuccess: (workspace) => {
      updateCache(workspace)
      setCreateTaskOpen(false)
      toast.success('Execution task created')
    },
    onError: (error) => {
      const e = presentError(error, 'form-submit')
      toast.error('Task could not be created', { description: e.message })
    },
  })

  const createDeliverable = useMutation({
    mutationFn: (input: CreateDeliverableInput) => fulfillmentApi.createDeliverable(input),
    onSuccess: (workspace) => {
      updateCache(workspace)
      setCreateDeliverableOrderId(null)
      toast.success('Deliverable added')
    },
  })
  const decideDeliverable = useMutation({
    mutationFn: ({
      deliverableId,
      action,
    }: {
      deliverableId: string
      action: 'approve' | 'reject'
    }) => fulfillmentApi.decideDeliverable(deliverableId, { action }),
    onSuccess: (workspace) => {
      updateCache(workspace)
      toast.success('Deliverable updated')
    },
  })

  const updateTask = useMutation({
    mutationFn: ({ taskId, input }: { taskId: string; input: UpdateExecutionTaskInput }) =>
      fulfillmentApi.updateTask(taskId, input),
    onSuccess: (workspace) => {
      updateCache(workspace)
      toast.success('Task updated')
    },
    onError: (error) => {
      const e = presentError(error, 'background-action')
      toast.error('Task could not be updated', { description: e.message })
    },
  })

  const selectedOrder = useMemo(() => {
    if (!selectedOrderId || !query.data) return null
    return query.data.orders.find((order) => order.id === selectedOrderId) ?? null
  }, [query.data, selectedOrderId])

  const selectedTask = useMemo(() => {
    if (!selectedTaskId || !query.data) return null
    return query.data.tasks.find((task) => task.id === selectedTaskId) ?? null
  }, [query.data, selectedTaskId])

  const selectedDeliverable = useMemo(() => {
    if (!selectedDeliverableId || !query.data) return null
    return query.data.deliverables.find((item) => item.id === selectedDeliverableId) ?? null
  }, [query.data, selectedDeliverableId])

  const selectedTaskOrder = useMemo(() => {
    if (!selectedTask || !query.data) return null
    return query.data.orders.find((order) => order.id === selectedTask.orderId) ?? null
  }, [query.data, selectedTask])

  if (query.isPending || serviceQuery.isPending) {
    return (
      <ModulePageStatus title={metadata[section].title} breadcrumb={metadata[section].breadcrumb}>
        <DashboardSkeleton />
      </ModulePageStatus>
    )
  }

  if (query.isError || serviceQuery.isError) {
    const sourceError = query.error ?? serviceQuery.error
    const e = presentError(sourceError, 'page-load')

    return (
      <ModulePageStatus title={metadata[section].title} breadcrumb={metadata[section].breadcrumb}>
        <ErrorState
          title={e.title}
          description={e.message}
          onRetry={() => {
            void query.refetch()
            void serviceQuery.refetch()
          }}
        />
      </ModulePageStatus>
    )
  }

  const services = serviceQuery.data.services
    .filter((service) => service.status === 'active')
    .map((service) => ({
      name: service.name,
      division: service.division,
      workflowStages: service.workflowStages ?? [],
    }))

  const page = metadata[section]
  const busy =
    createOrder.isPending ||
    updateOrder.isPending ||
    advanceOrder.isPending ||
    addOrderUpdate.isPending ||
    addMilestone.isPending ||
    createTask.isPending ||
    createDeliverable.isPending ||
    decideDeliverable.isPending ||
    updateTask.isPending

  const canUpdateOrder = canPerformAction(user, 'orderUpdate')
  const canUpdateTask = canPerformAction(user, 'taskUpdate')
  const canUpdateDeliverable = canPerformAction(user, 'deliverableUpdate')
  const canApproveDeliverable = canPerformAction(user, 'deliverableApprove')
  const canCreatePrimary =
    section === 'service-orders'
      ? canUpdateOrder
      : section === 'execution-tasks'
        ? canUpdateTask
        : canUpdateDeliverable

  const primaryLabel =
    section === 'service-orders'
      ? 'Create Order'
      : section === 'execution-tasks'
        ? 'New Task'
        : 'Add Deliverable'

  return (
    <>
      <ModulePageFrame
        header={
          <CompactPageToolbar
        title={page.title}
        breadcrumb={page.breadcrumb}
        primaryAction={
          <CompactActionButton
            tone="primary"
            disabled={!canCreatePrimary}
            locked={!canCreatePrimary}
            onClick={() => {
              if (!canCreatePrimary) return
              if (section === 'service-orders') setCreateOrderOpen(true)
              if (section === 'execution-tasks') setCreateTaskOpen(true)
              if (section === 'deliverables') setCreateDeliverableOrderId('')
            }}
          >
            {section === 'deliverables' ? <IconFilePlus size={14} /> : <IconPlus size={14} />}{' '}
            {primaryLabel}
          </CompactActionButton>
        }
          />
        }
      >

      {section === 'service-orders' ? (
        <ServiceOrdersScreen
          orders={query.data.orders}
          onOpenOrder={(order) => setSelectedOrderId(order.id)}
        />
      ) : section === 'execution-tasks' ? (
        <ExecutionTasksScreen
          tasks={query.data.tasks}
          onOpenTask={(task) => setSelectedTaskId(task.id)}
        />
      ) : (
        <DeliverablesScreen
          deliverables={query.data.deliverables}
          onOpen={(item) => setSelectedDeliverableId(item.id)}
        />
      )}

      {createOrderOpen ? (
        <CreateOrderWorkspace
          services={services}
          saving={createOrder.isPending}
          onClose={() => setCreateOrderOpen(false)}
          onSubmit={(draft) => {
            const selectedService = services.find((service) => service.name === draft.service)

            createOrder.mutate({
              ...draft,
              division: selectedService?.division ?? 'Service Operations',
              paymentReady: false,
              workflowStages: selectedService?.workflowStages.length
                ? selectedService.workflowStages
                : ['Order Setup', 'Execution', 'Review', 'Handover'],
            })
          }}
        />
      ) : null}

      {createTaskOpen ? (
        <CreateTaskWorkspace
          saving={createTask.isPending}
          onClose={() => setCreateTaskOpen(false)}
          onSubmit={(input) => createTask.mutate(input)}
        />
      ) : null}

      {createDeliverableOrderId !== null ? (
        <CreateDeliverableWorkspace
          initialOrderId={createDeliverableOrderId}
          saving={createDeliverable.isPending}
          onClose={() => setCreateDeliverableOrderId(null)}
          onSubmit={(input) => createDeliverable.mutate(input)}
        />
      ) : null}
      {selectedDeliverable ? (
        <DeliverableDetailWorkspace
          deliverable={selectedDeliverable}
          saving={decideDeliverable.isPending}
          canApprove={canApproveDeliverable}
          onClose={() => setSelectedDeliverableId(null)}
          onApprove={() =>
            decideDeliverable.mutate({ deliverableId: selectedDeliverable.id, action: 'approve' })
          }
          onReject={() =>
            decideDeliverable.mutate({ deliverableId: selectedDeliverable.id, action: 'reject' })
          }
        />
      ) : null}

      {selectedTask ? (
        <TaskDetailWorkspace
          task={selectedTask}
          {...(selectedTaskOrder ? { order: selectedTaskOrder } : {})}
          saving={updateTask.isPending}
          canEdit={canUpdateTask}
          onClose={() => setSelectedTaskId(null)}
          onUpdate={(input) =>
            updateTask.mutate({
              taskId: selectedTask.id,
              input,
            })
          }
        />
      ) : null}

      {selectedOrder ? (
        <OrderControlRoomWorkspace
          key={selectedOrder.id}
          order={selectedOrder}
          relatedTasks={query.data.tasks.filter((task) => task.orderId === selectedOrder.id)}
          saving={busy}
          canEditOrder={canUpdateOrder}
          canCreateTask={canUpdateTask}
          canCreateDeliverable={canUpdateDeliverable}
          onClose={() => setSelectedOrderId(null)}
          onSave={(input) =>
            updateOrder.mutate({
              orderId: selectedOrder.id,
              input,
            })
          }
          onAdvance={() => advanceOrder.mutate(selectedOrder.id)}
          onAddUpdate={(input) => addOrderUpdate.mutate(input)}
          onAddMilestone={(input) => addMilestone.mutate(input)}
          onCreateTask={(input) => createTask.mutate(input)}
          onAddDeliverable={() => setCreateDeliverableOrderId(selectedOrder.id)}
          onRequestClientApproval={() =>
            toast.success('Request Client Approval', {
              description: 'Client approval requests are not connected in this frontend yet.',
            })
          }
          onRecordFeedback={() =>
            toast.success('Record Feedback', {
              description: 'Feedback recording from the Order Control Room is not connected yet.',
            })
          }
        />
      ) : null}
      </ModulePageFrame>
    </>
  )
}
