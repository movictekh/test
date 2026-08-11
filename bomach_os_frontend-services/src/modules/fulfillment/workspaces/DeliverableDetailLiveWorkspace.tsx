import { IconExternalLink, IconX } from '@tabler/icons-react'
import { useForm } from '@tanstack/react-form'
import { useState } from 'react'

import { CompactActionButton } from '@/shared/ui/module-controls'

import {
  canDeleteDeliverable,
  canEditDeliverable,
  canReviewDeliverable,
} from '../deliverables/deliverable-capabilities'
import {
  deliverableTypes,
  type Deliverable,
  type DeliverableType,
  type UpdateDeliverableInput,
} from '../deliverables/deliverable.types'
import { validateDeliverableUpdate } from '../deliverables/deliverable.validation'
import type { ExecutionTask } from '../execution-tasks/execution-task.types'
import type { EmployeeOption, ServiceOrder } from '../service-orders/service-order.types'

function label(value: string) {
  return value.replaceAll('_', ' ').replace(/\b\w/g, (letter) => letter.toUpperCase())
}

function statusClass(status: Deliverable['status']) {
  if (status === 'approved') return 'fulfillment-pill-green'
  if (status === 'under_review') return 'fulfillment-pill-blue'
  if (status === 'rejected') return 'fulfillment-pill-red'
  if (status === 'superseded') return 'fulfillment-pill-gray'
  return 'fulfillment-pill-yellow'
}

function formatBytes(bytes: number) {
  if (!bytes) return 'Not recorded'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export function DeliverableDetailLiveWorkspace({
  deliverable,
  order,
  tasks,
  employees,
  saving,
  canUpdate,
  onClose,
  onUpdate,
  onApprove,
  onReject,
  onDelete,
}: {
  deliverable: Deliverable
  order: ServiceOrder
  tasks: ExecutionTask[]
  employees: EmployeeOption[]
  saving: boolean
  canUpdate: boolean
  onClose: () => void
  onUpdate: (input: UpdateDeliverableInput) => void
  onApprove: () => void
  onReject: (reason: string) => void
  onDelete: () => void
}) {
  const [editing, setEditing] = useState(false)
  const [rejecting, setRejecting] = useState(false)
  const [rejectionReason, setRejectionReason] = useState('')
  const [error, setError] = useState('')

  const milestone = order.milestones.find((item) => item.id === deliverable.milestoneId) ?? null
  const task = tasks.find((item) => item.id === deliverable.taskId) ?? null
  const employeeNames = new Map(employees.map((employee) => [employee.id, employee.name]))
  const ownerName = deliverable.ownerId
    ? (employeeNames.get(deliverable.ownerId) ?? `Employee #${deliverable.ownerId}`)
    : 'Unassigned'

  const form = useForm({
    defaultValues: {
      milestoneId: deliverable.milestoneId ?? 0,
      taskId: deliverable.taskId ?? 0,
      title: deliverable.title,
      deliverableType: deliverable.deliverableType,
      version: deliverable.version,
      fileUrl: deliverable.fileUrl,
      fileName: deliverable.fileName,
      contentType: deliverable.contentType,
      fileSizeBytes: deliverable.fileSizeBytes,
      description: deliverable.description,
      clientVisible: deliverable.clientVisible,
      ownerId: deliverable.ownerId ?? 0,
    },
    onSubmit: ({ value }) => {
      const input: UpdateDeliverableInput = {
        milestoneId: value.milestoneId || null,
        taskId: value.taskId || null,
        title: value.title.trim(),
        deliverableType: value.deliverableType,
        version: value.version.trim(),
        fileUrl: value.fileUrl.trim(),
        fileName: value.fileName.trim(),
        contentType: value.contentType.trim(),
        fileSizeBytes: Number(value.fileSizeBytes) || 0,
        description: value.description.trim(),
        clientVisible: deliverable.approvalMode === 'client' ? true : value.clientVisible,
        ownerId: value.ownerId || null,
      }

      const validationError = validateDeliverableUpdate(input)
      setError(validationError)
      if (validationError) return

      onUpdate(input)
      setEditing(false)
    },
  })

  const canEdit = canUpdate && canEditDeliverable(deliverable.status)
  const canReview = canUpdate && canReviewDeliverable(deliverable.status)
  const canDelete = canUpdate && canDeleteDeliverable(deliverable.status)

  return (
    <div className="commercial-modal-backdrop" role="presentation" onMouseDown={onClose}>
      <section
        className="commercial-modal commercial-modal--xl fulfillment-deliverable-modal"
        role="dialog"
        aria-modal="true"
        aria-label={`Deliverable ${deliverable.deliverableNumber}`}
        onMouseDown={(event) => event.stopPropagation()}
      >
        <header className="commercial-modal-header">
          <div className="min-w-0">
            <h2>Deliverable — {deliverable.deliverableNumber}</h2>
            <p>
              {order.orderNumber} · {order.serviceName}
            </p>
          </div>
          <div className="commercial-modal-header-meta">
            <span className={`fulfillment-pill ${statusClass(deliverable.status)}`}>{label(deliverable.status)}</span>
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
          <div className="fulfillment-order-room-layout">
            <div className="fulfillment-order-room-main">
              <section className="fulfillment-order-summary-card">
                <div className="fulfillment-order-summary-header">
                  <div>
                    <h3>{deliverable.title}</h3>
                    <p>
                      {label(deliverable.deliverableType)} · {deliverable.version}
                    </p>
                  </div>
                  {deliverable.fileUrl ? (
                    <a
                      className="commercial-btn commercial-btn-small"
                      href={deliverable.fileUrl}
                      target="_blank"
                      rel="noreferrer"
                    >
                      <IconExternalLink size={14} /> Open Document
                    </a>
                  ) : null}
                </div>
              </section>

              <section className="commercial-form-section fulfillment-task-panel">
                <div className="commercial-form-section-heading">
                  <div>
                    <h3>Deliverable Overview</h3>
                    <p>Formal output, links and visibility settings for this record.</p>
                  </div>
                </div>

                <div className="fulfillment-order-key-grid fulfillment-order-key-grid--compact">
                  <div className="fulfillment-order-key-card">
                    <span className="commercial-field-label">Milestone</span>
                    <b>{milestone?.name ?? 'Not linked'}</b>
                  </div>
                  <div className="fulfillment-order-key-card">
                    <span className="commercial-field-label">Execution Task</span>
                    <b>{task ? `${task.taskNumber} · ${task.title}` : 'Not linked'}</b>
                  </div>
                  <div className="fulfillment-order-key-card">
                    <span className="commercial-field-label">Owner</span>
                    <b>{ownerName}</b>
                  </div>
                  <div className="fulfillment-order-key-card">
                    <span className="commercial-field-label">Client visibility</span>
                    <b>{deliverable.clientVisible ? 'Visible to client' : 'Internal only'}</b>
                  </div>
                </div>
              </section>

              {error ? <div className="commercial-notice commercial-notice-red">{error}</div> : null}

              <section className="commercial-form-section fulfillment-task-panel">
                <div className="commercial-form-section-heading">
                  <div>
                    <h3>Document</h3>
                    <p>Stored file reference and metadata for this formal output.</p>
                  </div>
                </div>

                <div className="fulfillment-order-detail-stack fulfillment-order-detail-stack--compact">
                  <div className="fulfillment-order-detail-row fulfillment-task-detail-row">
                    <span className="commercial-field-label">File name</span>
                    <b>{deliverable.fileName || 'Not recorded'}</b>
                  </div>
                  <div className="fulfillment-order-detail-grid">
                    <div className="fulfillment-order-detail-row fulfillment-task-detail-row">
                      <span className="commercial-field-label">Content type</span>
                      <b>{deliverable.contentType || 'Not recorded'}</b>
                    </div>
                    <div className="fulfillment-order-detail-row fulfillment-task-detail-row">
                      <span className="commercial-field-label">File size</span>
                      <b>{formatBytes(deliverable.fileSizeBytes)}</b>
                    </div>
                  </div>
                </div>
              </section>

              <section className="commercial-form-section fulfillment-task-panel">
                <div className="commercial-form-section-heading">
                  <div>
                    <h3>Review Notes</h3>
                    <p>Document description and any review feedback for this deliverable.</p>
                  </div>
                </div>

                <div className="fulfillment-order-detail-stack fulfillment-order-detail-stack--compact">
                  <div className="fulfillment-order-detail-row fulfillment-task-detail-row">
                    <span className="commercial-field-label">Description</span>
                    <p>{deliverable.description || 'Not recorded'}</p>
                  </div>
                  {deliverable.status === 'rejected' ? (
                    <div className="fulfillment-order-detail-row fulfillment-task-detail-row">
                      <span className="commercial-field-label">Rejection reason</span>
                      <p>{deliverable.rejectionReason || 'Not recorded'}</p>
                    </div>
                  ) : null}
                </div>
              </section>
            </div>

            <aside className="fulfillment-order-room-aside">
              <section className="commercial-form-section fulfillment-task-panel">
                <div className="commercial-form-section-heading">
                  <div>
                    <h3>Approval</h3>
                  </div>
                </div>

                <div className="fulfillment-order-detail-stack fulfillment-order-detail-stack--compact">
                  <div className="fulfillment-order-detail-row fulfillment-task-detail-row">
                    <span className="commercial-field-label">Approval mode</span>
                    <b>{label(deliverable.approvalMode)}</b>
                  </div>
                  <div className="fulfillment-order-detail-row fulfillment-task-detail-row">
                    <span className="commercial-field-label">Status</span>
                    <b>{label(deliverable.status)}</b>
                  </div>
                  {deliverable.approvedAt ? (
                    <div className="fulfillment-order-detail-row fulfillment-task-detail-row">
                      <span className="commercial-field-label">Approved</span>
                      <b>{deliverable.approvedAt}</b>
                    </div>
                  ) : null}
                  {deliverable.rejectedAt ? (
                    <div className="fulfillment-order-detail-row fulfillment-task-detail-row">
                      <span className="commercial-field-label">Rejected</span>
                      <b>{deliverable.rejectedAt}</b>
                    </div>
                  ) : null}
                </div>

                {canReview ? (
                  <div className="fulfillment-task-detail-actions fulfillment-top-gap">
                    <CompactActionButton
                      type="button"
                      disabled={saving}
                      onClick={() => setRejecting((value) => !value)}
                    >
                      Reject
                    </CompactActionButton>
                    <CompactActionButton
                      type="button"
                      tone="primary"
                      disabled={saving}
                      onClick={onApprove}
                    >
                      {saving ? 'Updating...' : 'Approve'}
                    </CompactActionButton>
                  </div>
                ) : null}

                {rejecting ? (
                  <div className="fulfillment-order-detail-stack fulfillment-top-gap">
                    <label className="commercial-field">
                      <span>Rejection reason</span>
                      <textarea
                        rows={4}
                        value={rejectionReason}
                        onChange={(event) => setRejectionReason(event.target.value)}
                        placeholder="Explain what must be corrected."
                      />
                    </label>
                    <CompactActionButton
                      type="button"
                      tone="primary"
                      disabled={saving || !rejectionReason.trim()}
                      onClick={() => onReject(rejectionReason.trim())}
                    >
                      Confirm Rejection
                    </CompactActionButton>
                  </div>
                ) : null}
              </section>

              <section className="commercial-form-section fulfillment-task-panel">
                <div className="commercial-form-section-heading">
                  <div>
                    <h3>Controls</h3>
                    <p>Metadata edits stay separate from approval status.</p>
                  </div>
                </div>

                {canUpdate ? (
                  <div className="fulfillment-task-detail-actions">
                    <CompactActionButton
                      type="button"
                      tone="secondary"
                      disabled={saving || !canEdit}
                      onClick={() => setEditing(true)}
                    >
                      Edit Deliverable
                    </CompactActionButton>
                    <CompactActionButton
                      type="button"
                      disabled={saving || !canDelete}
                      onClick={onDelete}
                    >
                      Delete Deliverable
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
                    <h3>Edit Deliverable</h3>
                    <p>Status and approval mode are intentionally excluded from normal metadata editing.</p>
                  </div>
                </div>
                <div className="commercial-form-grid">
                  <form.Field name="title">
                    {(field) => (
                      <label className="commercial-field commercial-field--full">
                        <span>Title *</span>
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
                            .sort((a, b) => a.sortOrder - b.sortOrder || a.id - b.id)
                            .map((item) => (
                              <option key={item.id} value={item.id}>
                                {item.name} · {label(item.status)}
                              </option>
                            ))}
                        </select>
                      </label>
                    )}
                  </form.Field>
                  <form.Field name="taskId">
                    {(field) => (
                      <label className="commercial-field">
                        <span>Execution Task</span>
                        <select
                          value={field.state.value}
                          onChange={(event) => field.handleChange(Number(event.target.value))}
                        >
                          <option value={0}>No task link</option>
                          {tasks.map((item) => (
                            <option key={item.id} value={item.id}>
                              {item.taskNumber} · {item.title}
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
                  <form.Field name="deliverableType">
                    {(field) => (
                      <label className="commercial-field">
                        <span>Type</span>
                        <select
                          value={field.state.value}
                          onChange={(event) => field.handleChange(event.target.value as DeliverableType)}
                        >
                          {deliverableTypes.map((type) => (
                            <option key={type.value} value={type.value}>
                              {type.label}
                            </option>
                          ))}
                        </select>
                      </label>
                    )}
                  </form.Field>
                  <form.Field name="version">
                    {(field) => (
                      <label className="commercial-field">
                        <span>Version *</span>
                        <input
                          value={field.state.value}
                          onChange={(event) => field.handleChange(event.target.value)}
                        />
                      </label>
                    )}
                  </form.Field>
                  <form.Field name="fileUrl">
                    {(field) => (
                      <label className="commercial-field commercial-field--full">
                        <span>Document URL *</span>
                        <input
                          type="url"
                          value={field.state.value}
                          onChange={(event) => field.handleChange(event.target.value)}
                        />
                      </label>
                    )}
                  </form.Field>
                  <form.Field name="fileName">
                    {(field) => (
                      <label className="commercial-field">
                        <span>File name</span>
                        <input
                          value={field.state.value}
                          onChange={(event) => field.handleChange(event.target.value)}
                        />
                      </label>
                    )}
                  </form.Field>
                  <form.Field name="contentType">
                    {(field) => (
                      <label className="commercial-field">
                        <span>Content type</span>
                        <input
                          value={field.state.value}
                          onChange={(event) => field.handleChange(event.target.value)}
                        />
                      </label>
                    )}
                  </form.Field>
                  <form.Field name="fileSizeBytes">
                    {(field) => (
                      <label className="commercial-field">
                        <span>File size (bytes)</span>
                        <input
                          type="number"
                          min={0}
                          value={field.state.value}
                          onChange={(event) => field.handleChange(Number(event.target.value))}
                        />
                      </label>
                    )}
                  </form.Field>
                  <form.Field name="clientVisible">
                    {(field) => (
                      <label className="commercial-check">
                        <input
                          type="checkbox"
                          checked={deliverable.approvalMode === 'client' ? true : field.state.value}
                          disabled={deliverable.approvalMode === 'client'}
                          onChange={(event) => field.handleChange(event.target.checked)}
                        />
                        <span>
                          <b>Visible to client</b>
                          <small>Required when approval mode is set to client.</small>
                        </span>
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
                        />
                      </label>
                    )}
                  </form.Field>
                </div>
              </section>
              <div className="commercial-modal-footer">
                <button type="button" className="commercial-btn" disabled={saving} onClick={() => setEditing(false)}>
                  Cancel Edit
                </button>
                <button type="submit" className="commercial-btn commercial-btn-primary" disabled={saving}>
                  {saving ? 'Saving...' : 'Save Deliverable'}
                </button>
              </div>
            </form>
          ) : null}
        </div>

        {!editing ? (
          <footer className="commercial-modal-footer">
            <button type="button" className="commercial-btn" onClick={onClose}>
              Close
            </button>
          </footer>
        ) : null}
      </section>
    </div>
  )
}
