import { IconX } from '@tabler/icons-react'
import { useForm } from '@tanstack/react-form'
import { useState } from 'react'

import { formatCurrency } from '@/shared/lib/formatters'
import { formatNumberFieldValue, parseNumberFieldValue } from '@/shared/lib/number-input'

import type {
  AddMilestoneInput,
  AddOrderUpdateInput,
  CreateExecutionTaskInput,
  ExecutionTask,
  ServiceOrder,
  UpdateServiceOrderInput,
} from '../types/fulfillment.types'
import { CreateTaskWorkspace } from './CreateTaskWorkspace'
import { OrderUpdateWorkspace } from './OrderUpdateWorkspace'

function statusClass(status: ServiceOrder['status']) {
  if (status === 'Completed') return 'fulfillment-pill-green'
  if (status === 'Quality Review') return 'fulfillment-pill-purple'
  if (status === 'Awaiting Client') return 'fulfillment-pill-yellow'
  if (status === 'On Hold' || status === 'Cancelled') return 'fulfillment-pill-red'
  return 'fulfillment-pill-blue'
}

export function OrderControlRoomWorkspace({
  order,
  relatedTasks,
  saving,
  canEditOrder,
  canCreateTask,
  canCreateDeliverable,
  onClose,
  onSave,
  onAdvance,
  onAddUpdate,
  onAddMilestone,
  onCreateTask,
  onAddDeliverable,
  onRequestClientApproval,
  onRecordFeedback,
}: {
  order: ServiceOrder
  relatedTasks: ExecutionTask[]
  saving: boolean
  canEditOrder: boolean
  canCreateTask: boolean
  canCreateDeliverable: boolean
  onClose: () => void
  onSave: (input: UpdateServiceOrderInput) => void
  onAdvance: () => void
  onAddUpdate: (input: AddOrderUpdateInput) => void
  onAddMilestone: (input: AddMilestoneInput) => void
  onCreateTask: (input: CreateExecutionTaskInput) => void
  onAddDeliverable: () => void
  onRequestClientApproval: () => void
  onRecordFeedback: () => void
}) {
  const [showUpdate, setShowUpdate] = useState(false)
  const [showTask, setShowTask] = useState(false)
  const [milestoneName, setMilestoneName] = useState('')
  const [showMilestone, setShowMilestone] = useState(false)

  const form = useForm({
    defaultValues: {
      status: order.status,
      progress: order.progress,
      stage: order.stage,
      nextAction: order.nextAction,
    } satisfies UpdateServiceOrderInput,
  })

  return (
    <>
      <div className="fulfillment-modal-backdrop" onMouseDown={onClose}>
        <section
          className="fulfillment-modal fulfillment-modal-xl"
          role="dialog"
          aria-modal="true"
          aria-label={`Order Control Room ${order.id}`}
          onMouseDown={(event) => event.stopPropagation()}
        >
          <header className="fulfillment-modal-header">
            <h2>Order Control Room — {order.id}</h2>
            <button
              type="button"
              className="fulfillment-modal-close"
              onClick={onClose}
              aria-label="Close"
            >
              <IconX size={16} />
            </button>
          </header>

          <div className="fulfillment-modal-body">
            <section className="fulfillment-card">
              <header className="fulfillment-card-header">
                <div>
                  <div className="fulfillment-card-title">{order.client}</div>
                  <div className="fulfillment-card-subtitle">
                    {order.service} · {order.mode} · {order.owner}
                  </div>
                </div>
                <span className={`fulfillment-pill ${statusClass(order.status)}`}>
                  {order.status}
                </span>
              </header>
              <div className="fulfillment-progress">
                <i style={{ width: `${order.progress}%` }} />
              </div>
              <div className="fulfillment-kpi-note">
                {order.progress}% complete · {order.stage} · Due {order.dueAt}
              </div>
            </section>

            <div className="fulfillment-grid-2-1">
              <div>
                <section className="fulfillment-card">
                  <header className="fulfillment-card-header">
                    <div>
                      <div className="fulfillment-card-title">Milestones & Client Checkpoints</div>
                      <div className="fulfillment-card-subtitle">
                        Evidence, review and acceptance are retained
                      </div>
                    </div>
                    {canEditOrder ? (
                      <button
                        type="button"
                        className="fulfillment-btn fulfillment-btn-primary"
                        onClick={() => setShowMilestone((value) => !value)}
                      >
                        Add Milestone
                      </button>
                    ) : null}
                  </header>

                  {showMilestone && canEditOrder ? (
                    <div className="fulfillment-inline-create">
                      <input
                        value={milestoneName}
                        placeholder="Milestone name"
                        onChange={(event) => setMilestoneName(event.target.value)}
                      />
                      <button
                        type="button"
                        className="fulfillment-btn"
                        disabled={!milestoneName.trim() || saving}
                        onClick={() => {
                          onAddMilestone({
                            orderId: order.id,
                            name: milestoneName.trim(),
                          })
                          setMilestoneName('')
                          setShowMilestone(false)
                        }}
                      >
                        Add
                      </button>
                    </div>
                  ) : null}

                  <div className="fulfillment-lifecycle">
                    {order.milestones.map((milestone, index) => (
                      <article
                        key={milestone.id}
                        className={[
                          'fulfillment-step',
                          milestone.status === 'Done'
                            ? 'fulfillment-step-done'
                            : milestone.status === 'Active'
                              ? 'fulfillment-step-active'
                              : '',
                        ]
                          .filter(Boolean)
                          .join(' ')}
                      >
                        <small>{String(index + 1).padStart(2, '0')}</small>
                        <b>{milestone.name}</b>
                        <span>{milestone.status}</span>
                      </article>
                    ))}
                  </div>
                </section>

                <section className="fulfillment-card">
                  <header className="fulfillment-card-header">
                    <div className="fulfillment-card-title">Execution Tasks</div>
                    {canCreateTask ? (
                      <button
                        type="button"
                        className="fulfillment-btn fulfillment-btn-small"
                        onClick={() => setShowTask(true)}
                      >
                        New Task
                      </button>
                    ) : null}
                  </header>
                  <div className="fulfillment-table-wrap">
                    <table className="fulfillment-table">
                      <thead>
                        <tr>
                          <th>Task</th>
                          <th>Owner</th>
                          <th>Due</th>
                          <th>Status</th>
                        </tr>
                      </thead>
                      <tbody>
                        {relatedTasks.length > 0 ? (
                          relatedTasks.map((task) => (
                            <tr key={task.id}>
                              <td>
                                <b>{task.title}</b>
                              </td>
                              <td>{task.owner}</td>
                              <td>{task.dueAt}</td>
                              <td>
                                <span className="fulfillment-pill fulfillment-pill-blue">
                                  {task.status}
                                </span>
                              </td>
                            </tr>
                          ))
                        ) : (
                          <tr>
                            <td colSpan={4}>No tasks yet</td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                </section>

                <section className="fulfillment-card">
                  <header className="fulfillment-card-header">
                    <div>
                      <div className="fulfillment-card-title">Order Activity Log</div>
                      <div className="fulfillment-card-subtitle">
                        Internal and client-facing history
                      </div>
                    </div>
                    {canEditOrder ? (
                      <button
                        type="button"
                        className="fulfillment-btn"
                        onClick={() => setShowUpdate(true)}
                      >
                        Add Update
                      </button>
                    ) : null}
                  </header>

                  <div className="fulfillment-timeline">
                    {[...order.activities].reverse().map((item) => (
                      <article className="fulfillment-timeline-item" key={item.id}>
                        <b>{item.title}</b>
                        <p>
                          {item.description}
                          <br />
                          <strong>{item.actor}</strong>
                        </p>
                        <time>{new Date(item.at).toLocaleString('en-GB')}</time>
                      </article>
                    ))}
                  </div>
                </section>
              </div>

              <aside>
                {canEditOrder ? (
                  <section className="fulfillment-card">
                    <header className="fulfillment-card-header">
                      <div className="fulfillment-card-title">Order Controls</div>
                    </header>

                    <form.Field name="status">
                      {(field) => (
                        <label className="fulfillment-field">
                          <span>Status</span>
                          <select
                            value={field.state.value}
                            onChange={(event) =>
                              field.handleChange(event.target.value as typeof field.state.value)
                            }
                          >
                            {[
                              'Pending Mobilisation',
                              'Active',
                              'Quality Review',
                              'Awaiting Client',
                              'Completed',
                              'On Hold',
                              'Cancelled',
                            ].map((status) => (
                              <option key={status}>{status}</option>
                            ))}
                          </select>
                        </label>
                      )}
                    </form.Field>

                    <form.Field name="progress">
                      {(field) => (
                        <label className="fulfillment-field">
                          <span>Progress (%)</span>
                          <input
                            type="number"
                            min="0"
                            max="100"
                            value={formatNumberFieldValue(field.state.value)}
                            onChange={(event) =>
                              field.handleChange(parseNumberFieldValue(event.target.value))
                            }
                          />
                        </label>
                      )}
                    </form.Field>

                    <form.Field name="stage">
                      {(field) => (
                        <label className="fulfillment-field">
                          <span>Current stage</span>
                          <input
                            value={field.state.value}
                            onChange={(event) => field.handleChange(event.target.value)}
                          />
                        </label>
                      )}
                    </form.Field>

                    <form.Field name="nextAction">
                      {(field) => (
                        <label className="fulfillment-field">
                          <span>Next action</span>
                          <input
                            value={field.state.value}
                            onChange={(event) => field.handleChange(event.target.value)}
                          />
                        </label>
                      )}
                    </form.Field>

                    <button
                      type="button"
                      className="fulfillment-btn fulfillment-btn-primary fulfillment-btn-block"
                      disabled={saving}
                      onClick={() => onSave(form.state.values)}
                    >
                      {saving ? 'Saving...' : 'Save Update'}
                    </button>
                    <button
                      type="button"
                      className="fulfillment-btn fulfillment-btn-green fulfillment-btn-block fulfillment-top-gap"
                      disabled={saving || order.status === 'Completed'}
                      onClick={onAdvance}
                    >
                      Advance Stage
                    </button>
                  </section>
                ) : null}

                <section className="fulfillment-card">
                  <header className="fulfillment-card-header">
                    <div className="fulfillment-card-title">Financial Summary</div>
                  </header>
                  <div className="fulfillment-metric">
                    <label>Order value</label>
                    <strong>{formatCurrency(order.value)}</strong>
                  </div>
                  <div className="fulfillment-metric">
                    <label>Budget used</label>
                    <strong>{Math.round(order.progress * 0.82)}%</strong>
                  </div>
                  <div className="fulfillment-metric">
                    <label>Projected margin</label>
                    <strong>27%</strong>
                  </div>
                </section>

                <section className="fulfillment-card">
                  <header className="fulfillment-card-header">
                    <div className="fulfillment-card-title">Quick Actions</div>
                  </header>
                  {canCreateDeliverable ? (
                    <button
                      type="button"
                      className="fulfillment-btn fulfillment-btn-block"
                      onClick={onAddDeliverable}
                    >
                      Add Deliverable
                    </button>
                  ) : null}
                  {canEditOrder ? (
                    <>
                      <button
                        type="button"
                        className="fulfillment-btn fulfillment-btn-block fulfillment-top-gap"
                        onClick={onRequestClientApproval}
                      >
                        Request Client Approval
                      </button>
                      <button
                        type="button"
                        className="fulfillment-btn fulfillment-btn-block fulfillment-top-gap"
                        onClick={onRecordFeedback}
                      >
                        Record Feedback
                      </button>
                    </>
                  ) : null}
                </section>
              </aside>
            </div>
          </div>

          <footer className="fulfillment-modal-footer">
            <button type="button" className="fulfillment-btn" onClick={onClose}>
              Close
            </button>
          </footer>
        </section>
      </div>

      {showUpdate && canEditOrder ? (
        <OrderUpdateWorkspace
          order={order}
          saving={saving}
          onClose={() => setShowUpdate(false)}
          onSubmit={(input) => {
            onAddUpdate(input)
            setShowUpdate(false)
          }}
        />
      ) : null}

      {showTask && canCreateTask ? (
        <CreateTaskWorkspace
          initialOrderId={order.id}
          saving={saving}
          onClose={() => setShowTask(false)}
          onSubmit={(input) => {
            onCreateTask(input)
            setShowTask(false)
          }}
        />
      ) : null}
    </>
  )
}
