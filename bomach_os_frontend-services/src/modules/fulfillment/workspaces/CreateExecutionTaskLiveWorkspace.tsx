import { useForm } from '@tanstack/react-form'
import { useEffect, useState } from 'react'

import type {
  EmployeeOption,
  ServiceOrder,
  ServiceOrderMilestone,
} from '../service-orders/service-order.types'
import type {
  CreateExecutionTaskInput,
  ExecutionTaskPriority,
} from '../execution-tasks/execution-task.types'
import { executionTaskPriorities } from '../execution-tasks/execution-task.types'
import { validateExecutionTaskCreate } from '../execution-tasks/execution-task.validation'
import { TaskModalShell } from './TaskModalShell'

type CreateExecutionTaskFormValues = {
  milestoneId: number
  title: string
  description: string
  instructions: string
  acceptanceCriteria: string
  ownerId: number
  assigneeIds: number[]
  dueDate: string
  priority: ExecutionTaskPriority
  evidenceRequired: boolean
}

function getDefaultMilestoneId(order: ServiceOrder | null) {
  if (!order) return 0
  const activeMilestones = order.milestones.filter((milestone) => milestone.status === 'active')
  return activeMilestones.length === 1 ? (activeMilestones[0]?.id ?? 0) : 0
}

function assigneeLabel(employee: EmployeeOption) {
  return `${employee.name}${employee.designation ? ` · ${employee.designation}` : ''}`
}

export function CreateExecutionTaskLiveWorkspace({
  order,
  orders,
  employees,
  saving,
  onClose,
  onSubmit,
}: {
  order: ServiceOrder | null
  orders: ServiceOrder[]
  employees: EmployeeOption[]
  saving: boolean
  onClose: () => void
  onSubmit: (orderId: number, input: CreateExecutionTaskInput) => void
}) {
  const [selectedOrderId, setSelectedOrderId] = useState(order?.id ?? 0)
  const [pendingAssigneeId, setPendingAssigneeId] = useState(0)
  const [error, setError] = useState('')
  const activeOrder = order ?? orders.find((item) => item.id === selectedOrderId) ?? null

  const defaultMilestoneId = getDefaultMilestoneId(activeOrder)

  const defaultValues: CreateExecutionTaskFormValues = {
    milestoneId: defaultMilestoneId,
    title: '',
    description: '',
    instructions: '',
    acceptanceCriteria: '',
    ownerId: 0,
    assigneeIds: [],
    dueDate: '',
    priority: 'normal',
    evidenceRequired: false,
  }

  const form = useForm({
    defaultValues,
    onSubmit: ({ value }) => {
      if (!activeOrder) {
        setError('Select a Service Order before creating a Task.')
        return
      }

      const input: CreateExecutionTaskInput = {
        milestoneId: value.milestoneId || null,
        title: value.title.trim(),
        description: value.description.trim(),
        instructions: value.instructions.trim(),
        acceptanceCriteria: value.acceptanceCriteria.trim(),
        ownerId: value.ownerId || null,
        assigneeIds: value.assigneeIds,
        dueDate: value.dueDate || null,
        priority: value.priority,
        evidenceRequired: value.evidenceRequired,
      }

      const validationError = validateExecutionTaskCreate(input)
      setError(validationError)
      if (validationError) return

      onSubmit(activeOrder.id, input)
    },
  })

  useEffect(() => {
    if (!activeOrder) return
    form.setFieldValue('milestoneId', getDefaultMilestoneId(activeOrder))
  }, [activeOrder, form])

  const selectedAssigneeIds = form.state.values.assigneeIds
  const milestoneOptions: ServiceOrderMilestone[] = [...(activeOrder?.milestones ?? [])].sort(
    (left, right) => left.sortOrder - right.sortOrder || left.id - right.id,
  )
  const availableAssignees = employees.filter((employee) => !selectedAssigneeIds.includes(employee.id))

  return (
    <TaskModalShell
      as="form"
      ariaLabel="Create Execution Task"
      title="Create Execution Task"
      subtitle={
        activeOrder
          ? `${activeOrder.orderNumber} · ${activeOrder.serviceName}`
          : 'Select a Service Order to continue'
      }
      className="commercial-task-create-modal"
      bodyClassName="commercial-task-create-body"
      onClose={onClose}
      onSubmit={(event) => {
        event.preventDefault()
        void form.handleSubmit()
      }}
      footer={
        <>
          <button type="button" className="commercial-btn" disabled={saving} onClick={onClose}>
            Cancel
          </button>
          <button
            type="submit"
            className="commercial-btn commercial-btn-primary"
            disabled={saving}
          >
            {saving ? 'Creating...' : 'Create Task'}
          </button>
        </>
      }
    >
          <section className="commercial-form-section commercial-task-context">
            <div className="commercial-form-section-heading commercial-task-context-heading">
              <div>
                <h3>Task Context</h3>
                <p>Choose the service order first when needed. Milestones stay optional.</p>
              </div>
            </div>

            {activeOrder ? (
              <div className="fulfillment-order-key-grid commercial-task-context-grid">
                <div className="fulfillment-order-key-card">
                  <span className="commercial-field-label">Service Order</span>
                  <b>{activeOrder.orderNumber}</b>
                </div>
                <div className="fulfillment-order-key-card">
                  <span className="commercial-field-label">Service</span>
                  <b>{activeOrder.serviceName}</b>
                </div>
              </div>
            ) : (
              <div className="commercial-form-grid commercial-task-context-picker">
                <label className="commercial-field commercial-field--full">
                  <span>Service Order *</span>
                  <select
                    autoFocus
                    required
                    value={selectedOrderId}
                    onChange={(event) => {
                      const nextOrderId = Number(event.target.value)
                      setSelectedOrderId(nextOrderId)
                    }}
                  >
                    <option value={0}>Select a Service Order</option>
                    {[...orders]
                      .sort((left, right) => left.orderNumber.localeCompare(right.orderNumber))
                      .map((item) => (
                        <option key={item.id} value={item.id}>
                          {item.orderNumber} · {item.serviceName}
                        </option>
                      ))}
                  </select>
                </label>
              </div>
            )}
          </section>

          {error ? <div className="commercial-notice commercial-notice-red">{error}</div> : null}

          <section className="commercial-form-section">
            <div className="commercial-form-grid">
              <form.Field name="title">
                {(field) => (
                  <label className="commercial-field commercial-field--full">
                    <span>Task title *</span>
                    <input
                      autoFocus={Boolean(order)}
                      required
                      value={field.state.value}
                      onChange={(event) => field.handleChange(event.target.value)}
                      placeholder="e.g. Capture field coordinates"
                    />
                  </label>
                )}
              </form.Field>

              <form.Field name="ownerId">
                {(field) => (
                  <label className="commercial-field">
                    <span>Owner</span>
                    <select
                      value={field.state.value}
                      onChange={(event) => field.handleChange(Number(event.target.value))}
                    >
                      <option value={0}>Unassigned</option>
                      {employees.map((employee) => (
                        <option key={employee.id} value={employee.id}>
                          {employee.name}
                          {employee.designation ? ` · ${employee.designation}` : ''}
                        </option>
                      ))}
                    </select>
                  </label>
                )}
              </form.Field>

              <form.Field name="milestoneId">
                {(field) => (
                  <label className="commercial-field">
                    <span>Milestone</span>
                    <select
                      value={field.state.value}
                      onChange={(event) => field.handleChange(Number(event.target.value))}
                      disabled={!activeOrder}
                    >
                      <option value={0}>No milestone</option>
                      {milestoneOptions.map((milestone) => (
                        <option key={milestone.id} value={milestone.id}>
                          {milestone.name} · {milestone.status.replaceAll('_', ' ')}
                        </option>
                      ))}
                    </select>
                  </label>
                )}
              </form.Field>

              <form.Field name="dueDate">
                {(field) => (
                  <label className="commercial-field">
                    <span>Due date</span>
                    <input
                      type="date"
                      value={field.state.value}
                      onChange={(event) => field.handleChange(event.target.value)}
                    />
                  </label>
                )}
              </form.Field>

              <form.Field name="priority">
                {(field) => (
                  <label className="commercial-field">
                    <span>Priority</span>
                    <select
                      value={field.state.value}
                      onChange={(event) =>
                        field.handleChange(event.target.value as typeof field.state.value)
                      }
                    >
                      {executionTaskPriorities.map((priority) => (
                        <option key={priority.value} value={priority.value}>
                          {priority.label}
                        </option>
                      ))}
                    </select>
                  </label>
                )}
              </form.Field>

              <form.Field name="assigneeIds">
                {(field) => (
                  <label className="commercial-field commercial-field--full">
                    <span>Assignees</span>
                    <div className="commercial-assignee-picker">
                      <select
                        value={pendingAssigneeId}
                        onChange={(event) => {
                          const nextId = Number(event.target.value)
                          if (!nextId || field.state.value.includes(nextId)) return
                          field.handleChange([...field.state.value, nextId])
                          setPendingAssigneeId(0)
                        }}
                        disabled={availableAssignees.length === 0}
                      >
                        <option value={0}>
                          {availableAssignees.length > 0
                            ? 'Add a team member'
                            : 'No more team members available'}
                        </option>
                        {availableAssignees.map((employee) => (
                          <option key={employee.id} value={employee.id}>
                            {assigneeLabel(employee)}
                          </option>
                        ))}
                      </select>

                      {field.state.value.length > 0 ? (
                        <div className="commercial-assignee-chips">
                          {field.state.value.map((employeeId) => {
                            const employee = employees.find((item) => item.id === employeeId)
                            if (!employee) return null
                            return (
                              <span key={employee.id} className="commercial-assignee-chip">
                                <b>{employee.name}</b>
                                <small>{employee.designation || 'Team member'}</small>
                                <button
                                  type="button"
                                  onClick={() =>
                                    field.handleChange(
                                      field.state.value.filter((value) => value !== employee.id),
                                    )
                                  }
                                  aria-label={`Remove ${employee.name}`}
                                >
                                  ×
                                </button>
                              </span>
                            )
                          })}
                        </div>
                      ) : (
                        <small>Pick team members one at a time. Selected people appear below.</small>
                      )}
                    </div>
                  </label>
                )}
              </form.Field>

              <form.Field name="description">
                {(field) => (
                  <label className="commercial-field commercial-field--full">
                    <span>Description</span>
                    <textarea
                      value={field.state.value}
                      onChange={(event) => field.handleChange(event.target.value)}
                      placeholder="What work does this task cover?"
                    />
                  </label>
                )}
              </form.Field>

              <form.Field name="instructions">
                {(field) => (
                  <label className="commercial-field commercial-field--full">
                    <span>Instructions</span>
                    <textarea
                      value={field.state.value}
                      onChange={(event) => field.handleChange(event.target.value)}
                      placeholder="Execution instructions for the assigned team."
                    />
                  </label>
                )}
              </form.Field>

              <form.Field name="acceptanceCriteria">
                {(field) => (
                  <label className="commercial-field commercial-field--full">
                    <span>Acceptance criteria</span>
                    <textarea
                      value={field.state.value}
                      onChange={(event) => field.handleChange(event.target.value)}
                      placeholder="What must be true before the task can be accepted?"
                    />
                  </label>
                )}
              </form.Field>

              <form.Field name="evidenceRequired">
                {(field) => (
                  <label className="commercial-check">
                    <input
                      type="checkbox"
                      checked={field.state.value}
                      onChange={(event) => field.handleChange(event.target.checked)}
                    />
                    <span>
                      <b>Evidence required</b>
                      <small>Optional. Saves with the task record.</small>
                    </span>
                  </label>
                )}
              </form.Field>
            </div>
          </section>

    </TaskModalShell>
  )
}
