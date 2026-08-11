import { IconX } from '@tabler/icons-react'
import { useForm } from '@tanstack/react-form'
import { useEffect, useRef, useState } from 'react'

import { formatCurrency } from '@/shared/lib/formatters'

import type {
  AddOrderActivityInput,
  AddOrderMilestoneInput,
  EmployeeOption,
  ServiceOrder,
  UpdateServiceOrderInput,
} from '../service-orders/service-order.types'
import {
  validateOrderActivity,
  validateOrderMilestone,
} from '../service-orders/service-order.validation'

function statusLabel(status: string) {
  return status.replaceAll('_', ' ').replace(/\b\w/g, (letter) => letter.toUpperCase())
}

function visibilityLabel(visibility: string) {
  if (visibility === 'internal_client') return 'Internal and client'
  if (visibility === 'management') return 'Management only'
  return 'Internal only'
}

function statusClass(status: ServiceOrder['orderStatus']) {
  if (status === 'completed') return 'commercial-pill-green'
  if (status === 'cancelled' || status === 'on_hold') return 'commercial-pill-gray'
  if (status === 'quality_review' || status === 'awaiting_client') return 'commercial-pill-yellow'
  return 'commercial-pill-blue'
}

const activityTypes = [
  ['progress_update', 'Progress Update'],
  ['client_communication', 'Client Communication'],
  ['delay_blocker', 'Delay / Blocker'],
  ['inspection', 'Inspection'],
  ['decision', 'Decision'],
] as const

export function OrderControlRoomLiveWorkspace({
  order,
  clientName,
  assignedEmployeeName,
  invoiceNumber,
  employees,
  saving,
  canUpdate,
  onClose,
  onUpdate,
  onCompleteMilestone,
  onAddActivity,
  onAddMilestone,
  onOpenTasks,
  onOpenDeliverables,
}: {
  order: ServiceOrder
  clientName: string
  assignedEmployeeName: string
  invoiceNumber: string
  employees: EmployeeOption[]
  saving: boolean
  canUpdate: boolean
  onClose: () => void
  onUpdate: (input: UpdateServiceOrderInput) => void
  onCompleteMilestone: (milestoneId: number) => void
  onAddActivity: (input: AddOrderActivityInput) => void
  onAddMilestone: (input: AddOrderMilestoneInput) => void
  onOpenTasks: () => void
  onOpenDeliverables: () => void
}) {
  const [editing, setEditing] = useState(false)
  const [addingUpdate, setAddingUpdate] = useState(false)
  const [addingMilestone, setAddingMilestone] = useState(false)
  const [activityError, setActivityError] = useState('')
  const [milestoneError, setMilestoneError] = useState('')
  const activeMilestoneRef = useRef<HTMLElement | null>(null)

  const editForm = useForm({
    defaultValues: {
      assignedToId: order.assignedToId ?? 0,
      dueDate: order.dueDate ?? '',
      description: order.description,
      nextAction: order.nextAction,
    },
    onSubmit: ({ value }) => {
      onUpdate({
        assignedToId: value.assignedToId || null,
        dueDate: value.dueDate || null,
        description: value.description.trim(),
        nextAction: value.nextAction.trim(),
      })
      setEditing(false)
    },
  })

  const activityForm = useForm({
    defaultValues: {
      activityType: 'progress_update',
      visibility: 'internal_client' as const,
      note: '',
      nextAction: '',
    },
    onSubmit: ({ value }) => {
      const input: AddOrderActivityInput = {
        activityType: value.activityType,
        visibility: value.visibility,
        note: value.note.trim(),
        nextAction: value.nextAction.trim(),
      }
      const error = validateOrderActivity(input)
      setActivityError(error)
      if (error) return
      onAddActivity(input)
      setAddingUpdate(false)
    },
  })

  const milestoneForm = useForm({
    defaultValues: {
      name: '',
      dueDate: '',
      clientVisible: true,
    },
    onSubmit: ({ value }) => {
      const nextSortOrder =
        Math.max(0, ...order.milestones.map((milestone) => milestone.sortOrder)) + 1
      const input: AddOrderMilestoneInput = {
        name: value.name.trim(),
        sortOrder: nextSortOrder,
        dueDate: value.dueDate || null,
        clientVisible: value.clientVisible,
      }
      const error = validateOrderMilestone(input)
      setMilestoneError(error)
      if (error) return
      onAddMilestone(input)
      setAddingMilestone(false)
    },
  })

  const orderedMilestones = [...order.milestones].sort(
    (left, right) => left.sortOrder - right.sortOrder || left.id - right.id,
  )
  const activeMilestones = orderedMilestones.filter((milestone) => milestone.status === 'active')
  const activeMilestone = activeMilestones.length === 1 ? activeMilestones[0] : null
  const canAddMilestone = canUpdate && !['completed', 'cancelled'].includes(order.orderStatus)
  const canShowAdvanceStage = canUpdate && !['completed', 'cancelled'].includes(order.orderStatus)
  const canAdvanceStage =
    canShowAdvanceStage && activeMilestones.length === 1 && order.orderStatus !== 'on_hold'
  const taskTotal = Object.values(order.taskCounts).reduce((sum, count) => sum + count, 0)
  const deliverableTotal = Object.values(order.deliverableCounts).reduce(
    (sum, count) => sum + count,
    0,
  )
  const dueSummary = order.dueDate ?? order.validUntil ?? '—'
  const subtitle = [clientName, order.serviceName, assignedEmployeeName]
    .filter((value) => value && value !== 'Unassigned')
    .join(' · ')

  useEffect(() => {
    if (!activeMilestoneRef.current) return

    activeMilestoneRef.current.scrollIntoView({
      block: 'center',
      inline: 'nearest',
    })
    activeMilestoneRef.current.focus({ preventScroll: true })
  }, [activeMilestone?.id, order.id, order.updatedAt])

  return (
    <div className="commercial-modal-backdrop" role="presentation" onMouseDown={onClose}>
      <section
        className="commercial-modal commercial-modal--xl"
        role="dialog"
        aria-modal="true"
        aria-label={`Order ${order.orderNumber}`}
        onMouseDown={(event) => event.stopPropagation()}
      >
        <header className="commercial-modal-header">
          <div>
            <h2>Order Control Room — {order.orderNumber}</h2>
            <p>{subtitle || `${clientName} · ${order.serviceName}`}</p>
          </div>
          <div className="commercial-modal-header-meta">
            <span className={`commercial-pill ${statusClass(order.orderStatus)}`}>
              {statusLabel(order.orderStatus)}
            </span>
            <button
              type="button"
              className="commercial-modal-close"
              onClick={onClose}
              aria-label="Close"
            >
              <IconX size={16} />
            </button>
          </div>
        </header>

        <div className="commercial-modal-body">
          <section className="commercial-form-section">
            <div className="fulfillment-order-summary-card">
              <div className="fulfillment-order-summary-header">
                <div>
                  <h3>{clientName}</h3>
                  <p>
                    {order.serviceName} · Service order · {assignedEmployeeName}
                  </p>
                </div>
                <span className={`commercial-pill ${statusClass(order.orderStatus)}`}>
                  {statusLabel(order.orderStatus)}
                </span>
              </div>
              <div className="fulfillment-progress">
                <i style={{ width: `${order.progress}%` }} />
              </div>
              <div className="fulfillment-order-summary-note">
                {order.progress}% complete · {order.stage || 'Order Setup'} · Due {dueSummary}
              </div>
            </div>
          </section>

          <div className="fulfillment-order-room-layout">
            <div className="fulfillment-order-room-main">
              <section className="commercial-form-section">
                <div className="commercial-form-section-heading">
                  <div>
                    <h3>Milestones & Client Checkpoints</h3>
                    <p>Evidence, review and acceptance are retained across the order lifecycle.</p>
                  </div>
                  {canAddMilestone ? (
                    <button
                      type="button"
                      className="commercial-btn commercial-btn-small"
                      onClick={() => setAddingMilestone(true)}
                    >
                      Add Milestone
                    </button>
                  ) : null}
                </div>

                <div className="fulfillment-lifecycle">
                  {orderedMilestones.map((milestone, index) => (
                    <article
                      key={milestone.id}
                      ref={milestone.status === 'active' ? activeMilestoneRef : null}
                      tabIndex={milestone.status === 'active' ? -1 : undefined}
                      aria-current={milestone.status === 'active' ? 'step' : undefined}
                      className={`fulfillment-step ${
                        milestone.status === 'done'
                          ? 'fulfillment-step-done'
                          : milestone.status === 'active'
                            ? 'fulfillment-step-active'
                            : ''
                      }`}
                    >
                      <div className="fulfillment-step-head" aria-hidden="true">
                        <span className="fulfillment-step-badge">
                          {String(index + 1).padStart(2, '0')}
                        </span>
                      </div>
                      <div className="fulfillment-step-content">
                        <b>{milestone.name}</b>
                        <div className="fulfillment-step-meta">
                          <span>{statusLabel(milestone.status)}</span>
                          {milestone.dueDate ? <span>Due {milestone.dueDate}</span> : null}
                        </div>
                      </div>
                    </article>
                  ))}
                </div>
                <div className="fulfillment-stage-controls">
                  {activeMilestones.length > 1 ? (
                    <div className="commercial-notice commercial-notice-blue">
                      Multiple milestones are currently active. Review the workflow before
                      continuing.
                    </div>
                  ) : activeMilestones.length === 0 &&
                    !['completed', 'cancelled'].includes(order.orderStatus) ? (
                    <div className="commercial-notice commercial-notice-blue">
                      No active milestone is available for this order.
                    </div>
                  ) : activeMilestone ? (
                    <div>
                      <p className="commercial-form-note">
                        Current milestone: <b>{activeMilestone.name}</b>
                      </p>
                      {order.orderStatus === 'on_hold' ? (
                        <p className="commercial-form-note">
                          Stage advancement is unavailable while this order is on hold.
                        </p>
                      ) : null}
                    </div>
                  ) : null}
                </div>
                <div className="fulfillment-stage-advance">
                  {canShowAdvanceStage ? (
                    <button
                      type="button"
                      className="commercial-btn commercial-btn-primary"
                      disabled={saving || !canAdvanceStage || !activeMilestone}
                      onClick={() => {
                        if (!activeMilestone || !canAdvanceStage) return
                        onCompleteMilestone(activeMilestone.id)
                      }}
                      title={
                        !activeMilestone
                          ? 'No active milestone is available for this order.'
                          : order.orderStatus === 'on_hold'
                            ? 'Stage advancement is unavailable while this order is on hold.'
                            : activeMilestones.length > 1
                              ? 'Multiple milestones are currently active.'
                              : undefined
                      }
                    >
                      {saving ? 'Advancing...' : 'Advance Stage'}
                    </button>
                  ) : null}
                </div>
              </section>

              <section className="commercial-form-section">
                <div className="commercial-form-section-heading">
                  <div>
                    <h3>Execution Tasks</h3>
                    <p>Tasks linked to this order's delivery workflow.</p>
                  </div>
                  <button
                    type="button"
                    className="commercial-btn commercial-btn-small"
                    onClick={onOpenTasks}
                  >
                    New Task
                  </button>
                </div>
                <div className="fulfillment-table-wrap">
                  <table className="fulfillment-table fulfillment-order-room-table">
                    <thead>
                      <tr>
                        <th>Task</th>
                        <th>Status</th>
                        <th>Total</th>
                      </tr>
                    </thead>
                    <tbody>
                      {taskTotal > 0 ? (
                        <>
                          <tr>
                            <td>
                              <b>All execution tasks</b>
                            </td>
                            <td>All statuses</td>
                            <td>{taskTotal}</td>
                          </tr>
                          <tr>
                            <td>
                              <b>Tasks in progress</b>
                            </td>
                            <td>In Progress</td>
                            <td>{order.taskCounts.in_progress ?? 0}</td>
                          </tr>
                          <tr>
                            <td>
                              <b>Tasks in review</b>
                            </td>
                            <td>Review</td>
                            <td>{order.taskCounts.review ?? 0}</td>
                          </tr>
                        </>
                      ) : (
                        <tr>
                          <td colSpan={3}>No tasks yet</td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </section>

              <section className="commercial-form-section">
                <div className="commercial-form-section-heading">
                  <div>
                    <h3>Deliverables</h3>
                    <p>Documents, reports and outputs attached to this order.</p>
                  </div>
                  <button
                    type="button"
                    className="commercial-btn commercial-btn-small"
                    onClick={onOpenDeliverables}
                  >
                    Add Deliverable
                  </button>
                </div>
                <div className="fulfillment-table-wrap">
                  <table className="fulfillment-table fulfillment-order-room-table">
                    <thead>
                      <tr>
                        <th>Deliverable</th>
                        <th>Status</th>
                        <th>Total</th>
                      </tr>
                    </thead>
                    <tbody>
                      {deliverableTotal > 0 ? (
                        <>
                          <tr>
                            <td>
                              <b>All deliverables</b>
                            </td>
                            <td>All statuses</td>
                            <td>{deliverableTotal}</td>
                          </tr>
                          <tr>
                            <td>
                              <b>Deliverables under review</b>
                            </td>
                            <td>Under Review</td>
                            <td>{order.deliverableCounts.under_review ?? 0}</td>
                          </tr>
                          <tr>
                            <td>
                              <b>Approved deliverables</b>
                            </td>
                            <td>Approved</td>
                            <td>{order.deliverableCounts.approved ?? 0}</td>
                          </tr>
                        </>
                      ) : (
                        <tr>
                          <td colSpan={3}>No deliverables yet</td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </section>

              <section className="commercial-form-section">
                <div className="commercial-form-section-heading">
                  <div>
                    <h3>Order Activity Log</h3>
                    <p>Operational and client-facing history retained against this order.</p>
                  </div>
                  {canUpdate ? (
                    <button
                      type="button"
                      className="commercial-btn commercial-btn-small"
                      onClick={() => setAddingUpdate((value) => !value)}
                    >
                      Add Update
                    </button>
                  ) : null}
                </div>

                {addingUpdate ? (
                  <form
                    className="commercial-form-grid"
                    onSubmit={(event) => {
                      event.preventDefault()
                      void activityForm.handleSubmit()
                    }}
                  >
                    <activityForm.Field name="activityType">
                      {(field) => (
                        <label className="commercial-field">
                          <span>Update type</span>
                          <select
                            value={field.state.value}
                            onChange={(event) => field.handleChange(event.target.value)}
                          >
                            {activityTypes.map(([value, label]) => (
                              <option key={value} value={value}>
                                {label}
                              </option>
                            ))}
                          </select>
                        </label>
                      )}
                    </activityForm.Field>
                    <activityForm.Field name="visibility">
                      {(field) => (
                        <label className="commercial-field">
                          <span>Visibility</span>
                          <select
                            value={field.state.value}
                            onChange={(event) =>
                              field.handleChange(event.target.value as typeof field.state.value)
                            }
                          >
                            <option value="internal_client">Internal and client</option>
                            <option value="internal">Internal only</option>
                            <option value="management">Management only</option>
                          </select>
                        </label>
                      )}
                    </activityForm.Field>
                    <activityForm.Field name="note">
                      {(field) => (
                        <label className="commercial-field commercial-field--full">
                          <span>Detailed update *</span>
                          <textarea
                            rows={4}
                            value={field.state.value}
                            onChange={(event) => {
                              setActivityError('')
                              field.handleChange(event.target.value)
                            }}
                          />
                          {activityError ? (
                            <small className="commercial-field-error">{activityError}</small>
                          ) : null}
                        </label>
                      )}
                    </activityForm.Field>
                    <activityForm.Field name="nextAction">
                      {(field) => (
                        <label className="commercial-field commercial-field--full">
                          <span>Next action</span>
                          <input
                            value={field.state.value}
                            onChange={(event) => field.handleChange(event.target.value)}
                          />
                        </label>
                      )}
                    </activityForm.Field>
                    <div className="commercial-modal-footer-actions">
                      <button
                        type="button"
                        className="commercial-btn"
                        onClick={() => setAddingUpdate(false)}
                      >
                        Cancel
                      </button>
                      <button
                        type="submit"
                        className="commercial-btn commercial-btn-primary"
                        disabled={saving}
                      >
                        Save Update
                      </button>
                    </div>
                  </form>
                ) : null}

                {order.activities.length === 0 ? (
                  <div className="commercial-empty">No order activity has been recorded yet.</div>
                ) : (
                  <div className="commercial-timeline-list fulfillment-order-activity-list">
                    {[...order.activities].reverse().map((activity) => (
                      <article className="commercial-tl" key={activity.id}>
                        <b>{statusLabel(activity.activityType)}</b>
                        <p>{activity.note}</p>
                        {activity.nextAction ? (
                          <p>
                            <strong>Next:</strong> {activity.nextAction}
                          </p>
                        ) : null}
                        <time>
                          {new Date(activity.createdAt).toLocaleString('en-GB')} ·{' '}
                          {visibilityLabel(activity.visibility)}
                        </time>
                      </article>
                    ))}
                  </div>
                )}
              </section>
            </div>

            <aside className="fulfillment-order-room-aside">
              <section className="commercial-form-section">
                <div className="commercial-form-section-heading">
                  <div>
                    <h3>Order Controls</h3>
                    <p>Assignment, delivery notes and next-step ownership for this order.</p>
                  </div>
                </div>
                <div className="fulfillment-order-key-grid fulfillment-order-key-grid--compact">
                  <div className="fulfillment-order-key-card">
                    <div className="commercial-kl">Status</div>
                    <b>{statusLabel(order.orderStatus)}</b>
                  </div>
                  <div className="fulfillment-order-key-card">
                    <div className="commercial-kl">Progress</div>
                    <b>{order.progress}%</b>
                  </div>
                  <div className="fulfillment-order-key-card">
                    <div className="commercial-kl">Current stage</div>
                    <b>{order.stage || '—'}</b>
                  </div>
                  <div className="fulfillment-order-key-card">
                    <div className="commercial-kl">Due date</div>
                    <b>{dueSummary}</b>
                  </div>
                </div>
                <div className="fulfillment-order-detail-stack fulfillment-order-detail-stack--compact">
                  <div className="fulfillment-order-detail-row">
                    <span className="commercial-kl">Assigned to</span>
                    <b>{assignedEmployeeName}</b>
                  </div>
                  <div className="fulfillment-order-detail-row">
                    <span className="commercial-kl">Next action</span>
                    <b>{order.nextAction || '—'}</b>
                  </div>
                  {order.description ? (
                    <div className="fulfillment-order-detail-row">
                      <span className="commercial-kl">Description</span>
                      <p>{order.description}</p>
                    </div>
                  ) : null}
                </div>
                {canUpdate ? (
                  <div className="fulfillment-order-controls-actions">
                    <button
                      type="button"
                      className="commercial-btn commercial-btn-primary fulfillment-order-primary-action"
                      disabled={saving}
                      onClick={() => setEditing(true)}
                    >
                      Edit Order Controls
                    </button>
                  </div>
                ) : null}
              </section>

              <section className="commercial-form-section">
                <div className="commercial-form-section-heading">
                  <div>
                    <h3>Financial & Source Record</h3>
                    <p>Linked commercial references and delivery ownership.</p>
                  </div>
                </div>
                <div className="fulfillment-order-financial-grid">
                  <div className="fulfillment-order-key-card">
                    <span className="commercial-kl">Order value</span>
                    <b>{formatCurrency(order.amount)}</b>
                  </div>
                  <div className="fulfillment-order-key-card">
                    <span className="commercial-kl">Payment status</span>
                    <b>{statusLabel(order.paymentStatus)}</b>
                  </div>
                  <div className="fulfillment-order-key-card">
                    <span className="commercial-kl">Invoice</span>
                    <b>{invoiceNumber || (order.invoiceId ? `#${order.invoiceId}` : '—')}</b>
                  </div>
                  <div className="fulfillment-order-key-card">
                    <span className="commercial-kl">Quote</span>
                    <b>{order.quoteNumber || (order.quoteId ? `#${order.quoteId}` : '—')}</b>
                  </div>
                  <div className="fulfillment-order-key-card">
                    <span className="commercial-kl">Service request</span>
                    <b>{order.serviceRequestId ? `#${order.serviceRequestId}` : '—'}</b>
                  </div>
                </div>
              </section>
            </aside>
          </div>
        </div>

        {editing ? (
          <div
            className="commercial-modal-backdrop commercial-modal-backdrop--nested"
            role="presentation"
            onMouseDown={() => setEditing(false)}
          >
            <section
              className="commercial-modal commercial-order-controls-modal"
              role="dialog"
              aria-modal="true"
              aria-label="Edit Order Controls"
              onMouseDown={(event) => event.stopPropagation()}
            >
              <header className="commercial-modal-header">
                <div>
                  <h2>Edit Order Controls</h2>
                  <p>Assignment, delivery notes and next-step ownership for this order.</p>
                </div>
                <button
                  type="button"
                  className="commercial-modal-close"
                  onClick={() => setEditing(false)}
                  aria-label="Close"
                >
                  <IconX size={16} />
                </button>
              </header>

              <form
                onSubmit={(event) => {
                  event.preventDefault()
                  void editForm.handleSubmit()
                }}
              >
                <div className="commercial-modal-body">
                  <div className="commercial-form-grid commercial-form-grid--compact">
                    <editForm.Field name="assignedToId">
                      {(field) => (
                        <label className="commercial-field">
                          <span>Assigned employee</span>
                          <select
                            value={field.state.value}
                            onChange={(event) => field.handleChange(Number(event.target.value))}
                          >
                            <option value={0}>Unassigned</option>
                            {employees.map((employee) => (
                              <option key={employee.id} value={employee.id}>
                                {employee.name}
                                {employee.designation ? ` — ${employee.designation}` : ''}
                              </option>
                            ))}
                          </select>
                        </label>
                      )}
                    </editForm.Field>
                    <editForm.Field name="dueDate">
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
                    </editForm.Field>
                    <editForm.Field name="description">
                      {(field) => (
                        <label className="commercial-field commercial-field--full">
                          <span>Description</span>
                          <textarea
                            rows={3}
                            value={field.state.value}
                            onChange={(event) => field.handleChange(event.target.value)}
                          />
                        </label>
                      )}
                    </editForm.Field>
                    <editForm.Field name="nextAction">
                      {(field) => (
                        <label className="commercial-field commercial-field--full">
                          <span>Next action</span>
                          <input
                            value={field.state.value}
                            onChange={(event) => field.handleChange(event.target.value)}
                          />
                        </label>
                      )}
                    </editForm.Field>
                  </div>
                </div>
                <footer className="commercial-modal-footer">
                  <div className="commercial-modal-footer-start">
                    <span className="commercial-kl">Order controls update</span>
                  </div>
                  <div className="commercial-modal-footer-actions">
                    <button
                      type="button"
                      className="commercial-btn"
                      onClick={() => setEditing(false)}
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      className="commercial-btn commercial-btn-primary"
                      disabled={saving}
                    >
                      Save Update
                    </button>
                  </div>
                </footer>
              </form>
            </section>
          </div>
        ) : null}

        {addingMilestone ? (
          <div
            className="commercial-modal-backdrop commercial-modal-backdrop--nested"
            role="presentation"
            onMouseDown={() => setAddingMilestone(false)}
          >
            <section
              className="commercial-modal commercial-order-controls-modal"
              role="dialog"
              aria-modal="true"
              aria-label="Add Milestone"
              onMouseDown={(event) => event.stopPropagation()}
            >
              <header className="commercial-modal-header">
                <div>
                  <h2>Add Milestone</h2>
                  <p>Keep the workflow clean by adding one checkpoint at a time.</p>
                </div>
                <button
                  type="button"
                  className="commercial-modal-close"
                  onClick={() => setAddingMilestone(false)}
                  aria-label="Close"
                >
                  <IconX size={16} />
                </button>
              </header>

              <form
                onSubmit={(event) => {
                  event.preventDefault()
                  void milestoneForm.handleSubmit()
                }}
              >
                <div className="commercial-modal-body">
                  <div className="commercial-form-grid commercial-form-grid--compact">
                    <milestoneForm.Field name="name">
                      {(field) => (
                        <label className="commercial-field commercial-field--full">
                          <span>Milestone name *</span>
                          <input
                            value={field.state.value}
                            onChange={(event) => {
                              setMilestoneError('')
                              field.handleChange(event.target.value)
                            }}
                          />
                          {milestoneError ? (
                            <small className="commercial-field-error">{milestoneError}</small>
                          ) : null}
                        </label>
                      )}
                    </milestoneForm.Field>
                    <milestoneForm.Field name="dueDate">
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
                    </milestoneForm.Field>
                    <milestoneForm.Field name="clientVisible">
                      {(field) => (
                        <label className="commercial-field">
                          <span>Visibility</span>
                          <select
                            value={field.state.value ? 'client' : 'internal'}
                            onChange={(event) =>
                              field.handleChange(event.target.value === 'client')
                            }
                          >
                            <option value="client">Internal and client</option>
                            <option value="internal">Internal only</option>
                          </select>
                        </label>
                      )}
                    </milestoneForm.Field>
                  </div>
                </div>
                <footer className="commercial-modal-footer">
                  <div className="commercial-modal-footer-start">
                    <span className="commercial-kl">Milestone checkpoint</span>
                  </div>
                  <div className="commercial-modal-footer-actions">
                    <button
                      type="button"
                      className="commercial-btn"
                      onClick={() => setAddingMilestone(false)}
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      className="commercial-btn commercial-btn-primary"
                      disabled={saving}
                    >
                      Add Milestone
                    </button>
                  </div>
                </footer>
              </form>
            </section>
          </div>
        ) : null}

        <footer className="commercial-modal-footer">
          <button type="button" className="commercial-btn" onClick={onClose}>
            Close
          </button>
        </footer>
      </section>
    </div>
  )
}
