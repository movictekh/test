import { useForm } from '@tanstack/react-form'
import { useState } from 'react'

import { CompactActionButton } from '@/shared/ui/module-controls'

import type {
  ExecutionTask,
  UpdateExecutionTaskInput,
} from '../execution-tasks/execution-task.types'
import { executionTaskPriorities } from '../execution-tasks/execution-task.types'
import { validateExecutionTaskUpdate } from '../execution-tasks/execution-task.validation'
import type { EmployeeOption, ServiceOrder } from '../service-orders/service-order.types'
import { TaskModalShell } from './TaskModalShell'

function label(value: string) {
  return value.replaceAll('_', ' ').replace(/\b\w/g, (letter) => letter.toUpperCase())
}

function statusClass(status: ExecutionTask['status']) {
  if (status === 'done') return 'fulfillment-pill-green'
  if (status === 'review') return 'fulfillment-pill-purple'
  if (status === 'in_progress') return 'fulfillment-pill-blue'
  if (status === 'cancelled') return 'fulfillment-pill-gray'
  return 'fulfillment-pill-yellow'
}

function priorityClass(priority: ExecutionTask['priority']) {
  if (priority === 'critical') return 'fulfillment-pill-red'
  if (priority === 'high') return 'fulfillment-pill-yellow'
  return 'fulfillment-pill-gray'
}

function lifecycleLabel(status: ExecutionTask['status']) {
  if (status === 'to_do') return 'Start Task'
  if (status === 'in_progress') return 'Submit for Review'
  if (status === 'review') return 'Complete Task'
  return ''
}

export function ExecutionTaskDetailLiveWorkspace({
  task,
  order,
  employees,
  saving,
  canUpdate,
  onClose,
  onUpdate,
  onAdvance,
  onCancel,
  onDelete,
}: {
  task: ExecutionTask
  order: ServiceOrder
  employees: EmployeeOption[]
  saving: boolean
  canUpdate: boolean
  onClose: () => void
  onUpdate: (input: UpdateExecutionTaskInput) => void
  onAdvance: () => void
  onCancel: () => void
  onDelete: () => void
}) {
  const [editing, setEditing] = useState(false)
  const [error, setError] = useState('')
  const milestone = order.milestones.find((item) => item.id === task.milestoneId) ?? null
  const employeeNames = new Map(employees.map((employee) => [employee.id, employee.name]))
  const ownerName = task.ownerId
    ? (employeeNames.get(task.ownerId) ?? `Employee #${task.ownerId}`)
    : 'Unassigned'
  const assigneeNames = task.assigneeIds.map((id) => employeeNames.get(id) ?? `Employee #${id}`)

  const form = useForm({
    defaultValues: {
      milestoneId: task.milestoneId ?? 0,
      title: task.title,
      description: task.description,
      instructions: task.instructions,
      acceptanceCriteria: task.acceptanceCriteria,
      ownerId: task.ownerId ?? 0,
      assigneeIds: task.assigneeIds,
      dueDate: task.dueDate ?? '',
      priority: task.priority,
      evidenceRequired: task.evidenceRequired,
    },
    onSubmit: ({ value }) => {
      const input: UpdateExecutionTaskInput = {
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

      const validationError = validateExecutionTaskUpdate(input)
      setError(validationError)
      if (validationError) return

      onUpdate(input)
      setEditing(false)
    },
  })

  const headerMeta = (
    <span className={`fulfillment-pill ${statusClass(task.status)}`}>{label(task.status)}</span>
  )
  const canEditTask = canUpdate && task.status !== 'done'

  const footer = !editing ? (
    <CompactActionButton type="button" onClick={onClose}>
      Close
    </CompactActionButton>
  ) : null

  return (
    <TaskModalShell
      ariaLabel={`Execution Task ${task.taskNumber}`}
      title={`Execution Task — ${task.taskNumber}`}
      subtitle={`${order.orderNumber} · ${order.serviceName}${milestone ? ` · ${milestone.name}` : ''}`}
      headerMeta={headerMeta}
      onClose={onClose}
      footer={footer}
    >
      <section className="commercial-form-section">
        <div className="fulfillment-order-summary-card fulfillment-task-hero-card">
          <div className="fulfillment-task-summary-header fulfillment-task-hero-header">
            <div className="min-w-0">
              <div className="fulfillment-task-hero-kicker">Execution task</div>
              <h3>{task.title}</h3>
              <p>
                {order.orderNumber} · {order.serviceName}
                {milestone ? ` · ${milestone.name}` : ''}
              </p>
            </div>
            <div className="fulfillment-task-summary-badges">
              <span className={`fulfillment-pill ${statusClass(task.status)}`}>
                {label(task.status)}
              </span>
              <span className={`fulfillment-pill ${priorityClass(task.priority)}`}>
                {label(task.priority)}
              </span>
            </div>
          </div>
          <div className="fulfillment-task-hero-grid">
            <div className="fulfillment-task-meta-card">
              <span>Order</span>
              <b>{order.orderNumber}</b>
            </div>
            <div className="fulfillment-task-meta-card">
              <span>Milestone</span>
              <b>{milestone?.name ?? 'No milestone'}</b>
            </div>
            <div className="fulfillment-task-meta-card">
              <span>Owner</span>
              <b>{ownerName}</b>
            </div>
            <div className="fulfillment-task-meta-card">
              <span>Due</span>
              <b>{task.dueDate || 'Not set'}</b>
            </div>
            <div className="fulfillment-task-meta-card">
              <span>Priority</span>
              <b>{label(task.priority)}</b>
            </div>
          </div>
        </div>
      </section>

      {error ? <div className="commercial-notice commercial-notice-red">{error}</div> : null}

      {editing ? (
        <form
          onSubmit={(event) => {
            event.preventDefault()
            void form.handleSubmit()
          }}
        >
          <section className="commercial-form-section fulfillment-task-panel">
            <div className="commercial-form-section-heading">
              <div>
                <h3>Edit Task</h3>
                <p>Status is intentionally excluded. Use the lifecycle action to advance work.</p>
              </div>
            </div>

            <div className="commercial-form-grid">
              <form.Field name="title">
                {(field) => (
                  <label className="commercial-field commercial-field--full">
                    <span>Task title *</span>
                    <input
                      value={field.state.value}
                      onChange={(event) => field.handleChange(event.target.value)}
                    />
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
                    >
                      <option value={0}>No milestone</option>
                      {[...order.milestones]
                        .sort(
                          (left, right) => left.sortOrder - right.sortOrder || left.id - right.id,
                        )
                        .map((item) => (
                          <option key={item.id} value={item.id}>
                            {item.name} · {label(item.status)}
                          </option>
                        ))}
                    </select>
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

              <label className="commercial-field commercial-field--full">
                <span>Assignees</span>
                <div className="fulfillment-task-assignee-list">
                  {assigneeNames.length ? (
                    assigneeNames.map((name) => (
                      <span key={name} className="fulfillment-task-assignee-chip">
                        {name}
                      </span>
                    ))
                  ) : (
                    <b>No assignees</b>
                  )}
                </div>
              </label>

              <form.Field name="description">
                {(field) => (
                  <label className="commercial-field commercial-field--full">
                    <span>Description</span>
                    <textarea
                      value={field.state.value}
                      onChange={(event) => field.handleChange(event.target.value)}
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
                    />
                  </label>
                )}
              </form.Field>
            </div>
          </section>

          <div className="commercial-modal-footer">
            <button
              type="button"
              className="commercial-btn"
              disabled={saving}
              onClick={() => setEditing(false)}
            >
              Cancel Edit
            </button>
            <button
              type="submit"
              className="commercial-btn commercial-btn-primary"
              disabled={saving}
            >
              {saving ? 'Saving...' : 'Save Task'}
            </button>
          </div>
        </form>
      ) : (
        <div className="fulfillment-task-control-layout">
          <div className="fulfillment-task-detail-main">
            <section className="commercial-form-section fulfillment-task-panel">
              <div className="commercial-form-section-heading">
                <div>
                  <h3>Execution Scope</h3>
                  <p>Work definition, instructions and acceptance checks.</p>
                </div>
              </div>

              <div className="fulfillment-order-detail-stack fulfillment-order-detail-stack--compact">
                <div className="fulfillment-order-detail-row fulfillment-task-detail-row">
                  <span className="commercial-field-label">Description</span>
                  <p>{task.description || 'Not provided.'}</p>
                </div>
                <div className="fulfillment-order-detail-row fulfillment-task-detail-row">
                  <span className="commercial-field-label">Instructions</span>
                  <p>{task.instructions || 'Not provided.'}</p>
                </div>
                <div className="fulfillment-order-detail-row fulfillment-task-detail-row">
                  <span className="commercial-field-label">Acceptance criteria</span>
                  <p>{task.acceptanceCriteria || 'Not provided.'}</p>
                </div>
              </div>
            </section>

            <section className="commercial-form-section fulfillment-task-panel">
              <div className="commercial-form-section-heading">
                <div>
                  <h3>Assignment</h3>
                  <p>Owner and assigned execution team.</p>
                </div>
              </div>

              <div className="fulfillment-task-people-grid">
                <div className="fulfillment-task-meta-card">
                  <span>Owner</span>
                  <b>{ownerName}</b>
                </div>
                <div className="fulfillment-task-meta-card fulfillment-task-meta-card--wide">
                  <span>Assignees</span>
                  {assigneeNames.length ? (
                    <div className="fulfillment-task-assignee-list">
                      {assigneeNames.map((name) => (
                        <span key={name} className="fulfillment-task-assignee-chip">
                          {name}
                        </span>
                      ))}
                    </div>
                  ) : (
                    <b>No assignees</b>
                  )}
                </div>
              </div>
            </section>
          </div>

          <aside className="fulfillment-task-detail-aside">
            <section className="commercial-form-section fulfillment-task-panel">
              <div className="commercial-form-section-heading">
                <div>
                  <h3>Lifecycle</h3>
                  <p>Server-driven status transitions.</p>
                </div>
              </div>

              <div className="fulfillment-order-detail-stack fulfillment-order-detail-stack--compact">
                <div className="fulfillment-order-detail-row fulfillment-task-detail-row">
                  <span className="commercial-field-label">Current status</span>
                  <b>{label(task.status)}</b>
                </div>
                <div className="fulfillment-order-detail-row fulfillment-task-detail-row">
                  <span className="commercial-field-label">Milestone</span>
                  <b>{milestone?.name ?? 'Not linked'}</b>
                </div>
              </div>

              {canUpdate ? (
                <div className="fulfillment-task-detail-actions fulfillment-top-gap">
                  {lifecycleLabel(task.status) ? (
                    <CompactActionButton
                      type="button"
                      tone="primary"
                      disabled={saving}
                      onClick={onAdvance}
                    >
                      {saving ? 'Updating...' : lifecycleLabel(task.status)}
                    </CompactActionButton>
                  ) : null}
                  {!['done', 'cancelled'].includes(task.status) ? (
                    <CompactActionButton type="button" disabled={saving} onClick={onCancel}>
                      Cancel Task
                    </CompactActionButton>
                  ) : null}
                </div>
              ) : null}
            </section>

            <section className="commercial-form-section fulfillment-task-panel">
              <div className="commercial-form-section-heading">
                <div>
                  <h3>Task Controls</h3>
                  <p>Metadata changes stay separate from lifecycle transitions.</p>
                </div>
              </div>

              {canUpdate ? (
                <div className="fulfillment-task-detail-actions">
                  <CompactActionButton
                    type="button"
                    tone="secondary"
                    disabled={saving || !canEditTask}
                    onClick={() => setEditing(true)}
                  >
                    Edit Task
                  </CompactActionButton>
                  <CompactActionButton type="button" disabled={saving} onClick={onDelete}>
                    Delete Task
                  </CompactActionButton>
                </div>
              ) : (
                <div className="commercial-notice commercial-notice-blue">
                  You have read-only access to this Service Order.
                </div>
              )}
            </section>
          </aside>
        </div>
      )}
    </TaskModalShell>
  )
}
