import { IconFileUpload, IconX } from '@tabler/icons-react'
import { useForm } from '@tanstack/react-form'
import { useState } from 'react'

import { formatNumberFieldValue, parseNumberFieldValue } from '@/shared/lib/number-input'

import type {
  ExecutionTask,
  ServiceOrder,
  UpdateExecutionTaskInput,
} from '../types/fulfillment.types'
import { canCompleteTask } from './fulfillment-workflow.rules'

function taskStatusClass(status: ExecutionTask['status']) {
  if (status === 'Done') return 'fulfillment-pill-green'
  if (status === 'Review') return 'fulfillment-pill-purple'
  if (status === 'Blocked') return 'fulfillment-pill-red'
  if (status === 'In Progress') return 'fulfillment-pill-blue'
  return 'fulfillment-pill-gray'
}

export function TaskDetailWorkspace({
  task,
  order,
  saving,
  canEdit,
  onClose,
  onUpdate,
}: {
  task: ExecutionTask
  order?: ServiceOrder
  saving: boolean
  canEdit: boolean
  onClose: () => void
  onUpdate: (input: UpdateExecutionTaskInput) => void
}) {
  const [blockReason, setBlockReason] = useState(task.blockedReason ?? '')
  const [activityNote, setActivityNote] = useState('')
  const [evidenceLabel, setEvidenceLabel] = useState('')
  const [evidenceFileName, setEvidenceFileName] = useState('')

  const form = useForm({
    defaultValues: {
      progress: task.progress,
      owner: task.owner,
      dueAt: task.dueAt,
      priority: task.priority,
    },
  })

  const canComplete = canCompleteTask({
    evidenceRequired: task.evidenceRequired,
    evidenceCount: task.evidence.length,
  })

  return (
    <div className="fulfillment-modal-backdrop" onMouseDown={onClose}>
      <section
        className="fulfillment-modal fulfillment-modal-xl"
        role="dialog"
        aria-modal="true"
        aria-label={`Execution Task ${task.id}`}
        onMouseDown={(event) => event.stopPropagation()}
      >
        <header className="fulfillment-modal-header">
          <div>
            <h2>{task.title}</h2>
            <div className="fulfillment-card-subtitle">
              {task.id} · {task.orderId} · {task.stageName}
            </div>
          </div>
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
                <div className="fulfillment-card-title">{task.title}</div>
                <div className="fulfillment-card-subtitle">
                  {order
                    ? `${order.client} · ${order.service} · ${task.stageName}`
                    : `${task.orderId} · ${task.stageName}`}
                </div>
              </div>
              <span className={`fulfillment-pill ${taskStatusClass(task.status)}`}>
                {task.status}
              </span>
            </header>
            <div className="fulfillment-progress">
              <i style={{ width: `${task.progress}%` }} />
            </div>
            <div className="fulfillment-kpi-note">
              {task.progress}% complete · Due {task.dueAt} · {task.priority} priority
            </div>
          </section>

          {task.status === 'Blocked' ? (
            <div className="fulfillment-notice fulfillment-notice-red">
              <b>Blocked</b>
              <br />
              {task.blockedReason}
            </div>
          ) : null}

          <div className="fulfillment-grid-2-1">
            <div>
              <section className="fulfillment-card">
                <header className="fulfillment-card-header">
                  <div>
                    <div className="fulfillment-card-title">Task Instructions</div>
                    <div className="fulfillment-card-subtitle">
                      Execution scope and acceptance criteria
                    </div>
                  </div>
                </header>
                <p className="fulfillment-detail-copy">
                  {task.instructions || 'No instructions recorded.'}
                </p>
              </section>

              <section className="fulfillment-card">
                <header className="fulfillment-card-header">
                  <div>
                    <div className="fulfillment-card-title">Evidence</div>
                    <div className="fulfillment-card-subtitle">
                      {task.evidenceRequired
                        ? 'Evidence is required before completion'
                        : 'Evidence is optional for this task'}
                    </div>
                  </div>
                </header>
                {task.evidence.length ? (
                  task.evidence.map((evidence) => (
                    <div className="fulfillment-row" key={evidence.id}>
                      <div className="fulfillment-row-icon">
                        <IconFileUpload size={15} />
                      </div>
                      <div className="fulfillment-row-main">
                        <div className="fulfillment-row-name">{evidence.label}</div>
                        <div className="fulfillment-row-sub">
                          {evidence.fileName} · {evidence.addedBy}
                        </div>
                      </div>
                      <span className="fulfillment-row-sub">
                        {new Date(evidence.addedAt).toLocaleDateString('en-GB')}
                      </span>
                    </div>
                  ))
                ) : (
                  <div className="fulfillment-empty">No evidence added yet.</div>
                )}
                {canEdit ? (
                  <div className="fulfillment-inline-evidence">
                    <input
                      placeholder="Evidence label"
                      value={evidenceLabel}
                      onChange={(event) => setEvidenceLabel(event.target.value)}
                    />
                    <input
                      placeholder="File name / upload reference"
                      value={evidenceFileName}
                      onChange={(event) => setEvidenceFileName(event.target.value)}
                    />
                    <button
                      type="button"
                      className="fulfillment-btn"
                      disabled={saving || !evidenceLabel.trim() || !evidenceFileName.trim()}
                      onClick={() => {
                        onUpdate({
                          action: 'add-evidence',
                          evidence: {
                            label: evidenceLabel.trim(),
                            fileName: evidenceFileName.trim(),
                          },
                        })
                        setEvidenceLabel('')
                        setEvidenceFileName('')
                      }}
                    >
                      Add Evidence
                    </button>
                  </div>
                ) : null}
              </section>

              <section className="fulfillment-card">
                <header className="fulfillment-card-header">
                  <div>
                    <div className="fulfillment-card-title">Task Activity</div>
                    <div className="fulfillment-card-subtitle">
                      Assignment, progress, blockers and completion history
                    </div>
                  </div>
                </header>
                <div className="fulfillment-timeline">
                  {[...task.activities].reverse().map((item) => (
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
                {canEdit ? (
                  <div className="fulfillment-inline-create">
                    <input
                      placeholder="Add task activity..."
                      value={activityNote}
                      onChange={(event) => setActivityNote(event.target.value)}
                    />
                    <button
                      type="button"
                      className="fulfillment-btn"
                      disabled={saving || !activityNote.trim()}
                      onClick={() => {
                        onUpdate({ action: 'add-activity', note: activityNote.trim() })
                        setActivityNote('')
                      }}
                    >
                      Add
                    </button>
                  </div>
                ) : null}
              </section>
            </div>

            {canEdit ? (
              <aside>
                <section className="fulfillment-card">
                  <header className="fulfillment-card-header">
                    <div className="fulfillment-card-title">Task Controls</div>
                  </header>
                  <form.Field name="owner">
                    {(field) => (
                      <label className="fulfillment-field">
                        <span>Owner</span>
                        <input
                          value={field.state.value}
                          onChange={(event) => field.handleChange(event.target.value)}
                        />
                      </label>
                    )}
                  </form.Field>
                  <form.Field name="dueAt">
                    {(field) => (
                      <label className="fulfillment-field">
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
                      <label className="fulfillment-field">
                        <span>Priority</span>
                        <select
                          value={field.state.value}
                          onChange={(event) =>
                            field.handleChange(event.target.value as typeof field.state.value)
                          }
                        >
                          <option>Normal</option>
                          <option>High</option>
                          <option>Critical</option>
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
                  <button
                    type="button"
                    className="fulfillment-btn fulfillment-btn-primary fulfillment-btn-block"
                    disabled={saving}
                    onClick={() =>
                      onUpdate({
                        action: 'save',
                        progress: form.state.values.progress,
                        owner: form.state.values.owner,
                        dueAt: form.state.values.dueAt,
                        priority: form.state.values.priority,
                        note: 'Task controls saved.',
                      })
                    }
                  >
                    Save Task
                  </button>
                  {task.status !== 'Done' && task.status !== 'Blocked' ? (
                    <button
                      type="button"
                      className="fulfillment-btn fulfillment-btn-green fulfillment-btn-block fulfillment-top-gap"
                      disabled={saving}
                      onClick={() => onUpdate({ action: 'advance' })}
                    >
                      Advance Task
                    </button>
                  ) : null}
                </section>

                <section className="fulfillment-card">
                  <header className="fulfillment-card-header">
                    <div className="fulfillment-card-title">Blocker Control</div>
                  </header>
                  {task.status === 'Blocked' ? (
                    <>
                      <div className="fulfillment-notice fulfillment-notice-red">
                        {task.blockedReason}
                      </div>
                      <button
                        type="button"
                        className="fulfillment-btn fulfillment-btn-block"
                        disabled={saving}
                        onClick={() =>
                          onUpdate({
                            action: 'unblock',
                            note: 'Blocker resolved and task returned to execution.',
                          })
                        }
                      >
                        Resolve Blocker
                      </button>
                    </>
                  ) : task.status !== 'Done' ? (
                    <>
                      <label className="fulfillment-field">
                        <span>Blocked reason</span>
                        <textarea
                          value={blockReason}
                          onChange={(event) => setBlockReason(event.target.value)}
                        />
                      </label>
                      <button
                        type="button"
                        className="fulfillment-btn fulfillment-btn-block"
                        disabled={saving || !blockReason.trim()}
                        onClick={() =>
                          onUpdate({ action: 'block', blockedReason: blockReason.trim() })
                        }
                      >
                        Mark Blocked
                      </button>
                    </>
                  ) : (
                    <div className="fulfillment-notice fulfillment-notice-green">
                      Task is completed.
                    </div>
                  )}
                </section>

                <section className="fulfillment-card">
                  <header className="fulfillment-card-header">
                    <div className="fulfillment-card-title">Completion</div>
                  </header>
                  {!canComplete ? (
                    <div className="fulfillment-notice fulfillment-notice-yellow">
                      Add the required evidence before completing this task.
                    </div>
                  ) : null}
                  <button
                    type="button"
                    className="fulfillment-btn fulfillment-btn-green fulfillment-btn-block"
                    disabled={saving || task.status === 'Done' || !canComplete}
                    onClick={() =>
                      onUpdate({
                        action: 'complete',
                        note: 'Execution task completed and accepted.',
                      })
                    }
                  >
                    {task.status === 'Done' ? 'Task Completed' : 'Complete Task'}
                  </button>
                </section>
              </aside>
            ) : null}
          </div>
        </div>

        <footer className="fulfillment-modal-footer">
          <button type="button" className="fulfillment-btn" onClick={onClose}>
            Close
          </button>
        </footer>
      </section>
    </div>
  )
}
