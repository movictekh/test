import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from '@tanstack/react-router'
import { useMemo, useState } from 'react'
import { IconUserScreen } from '@tabler/icons-react'

import {
  CompactPageToolbar,
  PrototypeButton,
} from '@/modules/service-administration/components/ServiceAdministrationUi'
import { serviceAdministrationQueries } from '@/modules/service-administration/api/service-administration.queries'
import { presentError } from '@/shared/errors'
import { DashboardSkeleton, ErrorState, useToast } from '@/shared/ui'

import { fulfillmentApi } from '../api/fulfillment.api'
import { fulfillmentKeys } from '../api/fulfillment.keys'
import { fulfillmentQueries } from '../api/fulfillment.queries'
import { ExecutionTasksScreen } from '../screens/ExecutionTasksScreen'
import { ServiceOrdersScreen } from '../screens/ServiceOrdersScreen'
import type {
  AddMilestoneInput,
  AddOrderUpdateInput,
  CreateExecutionTaskInput,
  CreateServiceOrderInput,
  FulfillmentSection,
  UpdateServiceOrderInput,
  UpdateExecutionTaskInput,
} from '../types/fulfillment.types'
import { CreateOrderWorkspace } from '../workspaces/CreateOrderWorkspace'
import { CreateTaskWorkspace } from '../workspaces/CreateTaskWorkspace'
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
}

export function FulfillmentSectionPage({ section }: { section: FulfillmentSection }) {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const toast = useToast()

  const query = useQuery(fulfillmentQueries.workspace())
  const serviceQuery = useQuery(serviceAdministrationQueries.workspace())

  const [createOrderOpen, setCreateOrderOpen] = useState(false)
  const [createTaskOpen, setCreateTaskOpen] = useState(false)
  const [selectedOrderId, setSelectedOrderId] = useState<string | null>(null)
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null)

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

  const selectedTaskOrder = useMemo(() => {
    if (!selectedTask || !query.data) return null
    return query.data.orders.find((order) => order.id === selectedTask.orderId) ?? null
  }, [query.data, selectedTask])

  if (query.isPending || serviceQuery.isPending) {
    return <DashboardSkeleton />
  }

  if (query.isError || serviceQuery.isError) {
    const sourceError = query.error ?? serviceQuery.error
    const e = presentError(sourceError, 'page-load')

    return (
      <ErrorState
        title={e.title}
        description={e.message}
        onRetry={() => {
          void query.refetch()
          void serviceQuery.refetch()
        }}
      />
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
    updateTask.isPending

  return (
    <>
      <CompactPageToolbar
        title={page.title}
        breadcrumb={page.breadcrumb}
        secondaryAction={
          <PrototypeButton onClick={() => void navigate({ to: '/portal/dashboard' })}>
            <IconUserScreen size={14} />
            Client Portal
          </PrototypeButton>
        }
      />

      {section === 'service-orders' ? (
        <ServiceOrdersScreen
          orders={query.data.orders}
          onCreateOrder={() => setCreateOrderOpen(true)}
          onOpenOrder={(order) => setSelectedOrderId(order.id)}
        />
      ) : (
        <ExecutionTasksScreen
          tasks={query.data.tasks}
          onCreateTask={() => setCreateTaskOpen(true)}
          onOpenTask={(task) => setSelectedTaskId(task.id)}
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

      {selectedTask ? (
        <TaskDetailWorkspace
          task={selectedTask}
          {...(selectedTaskOrder ? { order: selectedTaskOrder } : {})}
          saving={updateTask.isPending}
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
          onFutureAction={(action) => {
            toast.success(action, {
              description:
                action === 'Add Deliverable'
                  ? 'The control is retained for UI-3.03 Deliverables.'
                  : 'The prototype action is retained and connects in its owning phase.',
            })
          }}
        />
      ) : null}
    </>
  )
}
