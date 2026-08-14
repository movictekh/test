import { IconExternalLink, IconRefresh, IconTrash, IconUpload, IconX } from '@tabler/icons-react'
import { useForm } from '@tanstack/react-form'
import { useRef, useState } from 'react'

import { presentError } from '@/shared/errors'
import { formatCurrency } from '@/shared/lib/formatters'
import { formatNumberFieldValue, parseNumberFieldValue } from '@/shared/lib/number-input'
import { useToast } from '@/shared/ui/toast/useToast'

import { serviceRequestsApi } from '../api/service-requests.api'
import type {
  CreateServiceRequestActivityInput,
  CreateServiceRequestAttachmentInput,
  EmployeeOption,
  ServiceRequestChoices,
  ServiceRequestDetail,
  UpdateServiceRequestInput,
} from '../api/service-requests.types'

import { FileTypeIcon } from '../request-intake/file-presentation'
import { formatBytes } from '../request-intake/file-presentation.utils'

function statusClass(status: string) {
  if (status === 'rejected') return 'commercial-pill-gray'
  if (status === 'quoted' || status === 'converted') return 'commercial-pill-green'
  if (status === 'awaiting_client' || status === 'site_assessment') {
    return 'commercial-pill-yellow'
  }
  return 'commercial-pill-blue'
}

type AttachmentUploadStatus = 'uploading' | 'uploaded' | 'error'

interface PendingAttachmentUpload {
  file: File
  fileName: string
  fileSizeBytes: number
  contentType: string
  fileUrl: string
  status: AttachmentUploadStatus
  error: string
}

function renderAnswerValue(value: unknown) {
  if (Array.isArray(value)) return value.map((item) => String(item)).join(', ')
  if (typeof value === 'boolean') return value ? 'Yes' : 'No'
  if (typeof value === 'string') return value || '—'
  if (typeof value === 'number') return String(value)
  return '—'
}

function normalizeAttachmentText(value: string | null | undefined) {
  return value?.trim().toLowerCase() ?? ''
}

export function ServiceRequestDetailWorkspace({
  request,
  choices,
  employees,
  saving,
  activitySaving,
  attachmentSaving,
  onClose,
  onUpdate,
  onActivity,
  onAttachment,
  onPrepareQuotation,
}: {
  request: ServiceRequestDetail
  choices: ServiceRequestChoices
  employees: EmployeeOption[]
  saving: boolean
  activitySaving: boolean
  attachmentSaving: boolean
  onClose: () => void
  onUpdate: (input: UpdateServiceRequestInput) => void
  onActivity: (input: CreateServiceRequestActivityInput) => void
  onAttachment: (input: CreateServiceRequestAttachmentInput) => void
  onPrepareQuotation: () => void
}) {
  const toast = useToast()
  const [activityOpen, setActivityOpen] = useState(false)
  const [attachmentOpen, setAttachmentOpen] = useState(false)
  const [attachmentError, setAttachmentError] = useState('')
  const [pendingAttachment, setPendingAttachment] = useState<PendingAttachmentUpload | null>(null)
  const uploadControllerRef = useRef<AbortController | null>(null)

  const controlForm = useForm({
    defaultValues: {
      status: request.status,
      priority: request.priority,
      ownerId: request.ownerId ?? 0,
      budget: request.budget ?? 0,
      dueDate: request.dueDate ?? '',
      nextAction: request.nextAction,
      estimatedValue: request.estimatedValue,
      scopeSummary: request.scopeSummary,
    },
    onSubmit: ({ value }) =>
      onUpdate({
        status: value.status,
        priority: value.priority,
        ownerId: value.ownerId || null,
        budget: Number(value.budget || 0),
        dueDate: value.dueDate || null,
        nextAction: value.nextAction.trim(),
        estimatedValue: Number(value.estimatedValue || 0),
        scopeSummary: value.scopeSummary.trim(),
      }),
  })

  const activityForm = useForm({
    defaultValues: {
      activityType: choices.activityTypes[0]?.value ?? 'internal_note',
      outcome: choices.activityOutcomes[0]?.value ?? 'not_applicable',
      note: '',
      nextAction: '',
      nextFollowUpAt: '',
    },
    onSubmit: ({ value }) => {
      if (!value.note.trim()) return
      onActivity({
        activityType: value.activityType,
        outcome: value.outcome,
        note: value.note.trim(),
        nextAction: value.nextAction.trim(),
        nextFollowUpAt: value.nextFollowUpAt || null,
      })
      setActivityOpen(false)
    },
  })

  const attachmentForm = useForm({
    defaultValues: {
      label: '',
      fileName: '',
      fileUrl: '',
      contentType: '',
    },
    onSubmit: ({ value }) => {
      if (!value.fileUrl.trim()) {
        setAttachmentError('Upload a file before adding this attachment.')
        return
      }
      onAttachment({
        label: value.label.trim(),
        fileName: value.fileName.trim(),
        fileUrl: value.fileUrl.trim(),
        contentType: value.contentType.trim(),
      })
      setAttachmentError('')
      setPendingAttachment(null)
      setAttachmentOpen(false)
    },
  })

  const resetAttachmentUpload = () => {
    uploadControllerRef.current?.abort()
    uploadControllerRef.current = null
    setPendingAttachment(null)
    setAttachmentError('')
    attachmentForm.setFieldValue('fileName', '')
    attachmentForm.setFieldValue('fileUrl', '')
    attachmentForm.setFieldValue('contentType', '')
  }

  const uploadAttachmentFile = async (file: File) => {
    uploadControllerRef.current?.abort()
    const controller = new AbortController()
    uploadControllerRef.current = controller
    setAttachmentError('')

    setPendingAttachment({
      file,
      fileName: file.name,
      fileSizeBytes: file.size,
      contentType: file.type,
      fileUrl: '',
      status: 'uploading',
      error: '',
    })

    attachmentForm.setFieldValue('fileName', file.name)
    attachmentForm.setFieldValue('contentType', file.type)

    if (!attachmentForm.state.values.label.trim()) {
      const baseName = file.name.replace(/\.[^.]+$/, '')
      attachmentForm.setFieldValue('label', baseName)
    }

    try {
      const fileUrl = await serviceRequestsApi.uploadFile(file, controller.signal)
      setPendingAttachment({
        file,
        fileName: file.name,
        fileSizeBytes: file.size,
        contentType: file.type,
        fileUrl,
        status: 'uploaded',
        error: '',
      })
      attachmentForm.setFieldValue('fileUrl', fileUrl)
    } catch (uploadError) {
      if (controller.signal.aborted) return
      const message = presentError(uploadError, 'background-action').message
      setPendingAttachment({
        file,
        fileName: file.name,
        fileSizeBytes: file.size,
        contentType: file.type,
        fileUrl: '',
        status: 'error',
        error: message,
      })
      attachmentForm.setFieldValue('fileUrl', '')
      setAttachmentError(message)
      toast.error('Document upload failed', { description: message })
    } finally {
      if (uploadControllerRef.current === controller) {
        uploadControllerRef.current = null
      }
    }
  }

  const retryAttachmentUpload = () => {
    if (!pendingAttachment) return
    void uploadAttachmentFile(pendingAttachment.file)
  }

  const canPrepareQuotation =
    !request.quoteId && request.status !== 'converted' && request.status !== 'rejected'

  return (
    <>
      <div className="commercial-modal-backdrop" role="presentation" onMouseDown={onClose}>
        <section
          className="commercial-modal commercial-modal--xl commercial-request360"
          role="dialog"
          aria-modal="true"
          onMouseDown={(event) => event.stopPropagation()}
        >
          <header className="commercial-modal-header">
            <div>
              <h2>Request 360 File — {request.requestNumber}</h2>
              <p>Backend record #{request.id}</p>
            </div>
            <button
              type="button"
              className="commercial-modal-close"
              onClick={onClose}
              aria-label="Close"
            >
              <IconX size={16} />
            </button>
          </header>

          <div className="commercial-modal-body">
            <div className="commercial-g21">
              <div className="commercial-g21-main">
                <section className="commercial-card commercial-request360-card commercial-request360-journal">
                  <div className="commercial-card-header">
                    <div>
                      <h2>{request.clientName}</h2>
                      <p>
                        {request.serviceName} · {request.branchName || 'No branch'} ·{' '}
                        {new Date(request.createdAt).toLocaleString('en-GB')}
                      </p>
                    </div>
                    <span className={`commercial-pill ${statusClass(request.status)}`}>
                      {request.statusDisplay}
                    </span>
                  </div>
                </section>

                <section className="commercial-card commercial-request360-card">
                  <div className="commercial-card-header">
                    <div>
                      <h2>Request Information</h2>
                      <p>Request-form snapshot v{request.requestFormVersion}</p>
                    </div>
                  </div>
                  <div className="commercial-info-grid">
                    <div>
                      <div className="commercial-kl">Contact</div>
                      <b>{request.contactName}</b>
                    </div>
                    <div>
                      <div className="commercial-kl">Phone</div>
                      <b>{request.contactPhone || '—'}</b>
                    </div>
                    <div>
                      <div className="commercial-kl">Email</div>
                      <b>{request.contactEmail || '—'}</b>
                    </div>
                    <div>
                      <div className="commercial-kl">Customer type</div>
                      <b>{request.customerType}</b>
                    </div>
                    <div>
                      <div className="commercial-kl">Source</div>
                      <b>
                        {request.source}
                        {request.sourceReference ? ` · ${request.sourceReference}` : ''}
                      </b>
                    </div>
                    <div>
                      <div className="commercial-kl">Owner</div>
                      <b>{request.ownerName || 'Unassigned'}</b>
                    </div>
                    <div>
                      <div className="commercial-kl">Budget</div>
                      <b>{request.budget == null ? '—' : formatCurrency(request.budget)}</b>
                    </div>
                    <div>
                      <div className="commercial-kl">Estimate</div>
                      <b>{formatCurrency(request.estimatedValue)}</b>
                    </div>
                    <div className="commercial-info-full">
                      <div className="commercial-kl">Scope</div>
                      <p>{request.scopeSummary || '—'}</p>
                    </div>
                  </div>
                </section>

                <section className="commercial-card commercial-request360-card">
                  <div className="commercial-card-header">
                    <div>
                      <h2>Intake Responses</h2>
                      <p>Stored against the request snapshot</p>
                    </div>
                  </div>
                  <div className="commercial-info-grid">
                    {request.answers.length === 0 ? (
                      <div className="commercial-empty">No intake answers recorded.</div>
                    ) : (
                      [...request.answers]
                        .sort((a, b) => a.sortOrder - b.sortOrder)
                        .map((answer) => (
                          <div key={answer.id}>
                            <div className="commercial-kl">{answer.label}</div>
                            <b>{renderAnswerValue(answer.value)}</b>
                          </div>
                        ))
                    )}
                  </div>
                </section>

                <section className="commercial-card commercial-request360-card">
                  <div className="commercial-card-header">
                    <div>
                      <h2>Activity & Communication Journal</h2>
                      <p>Backend activity history</p>
                    </div>
                    <button
                      type="button"
                      className="commercial-btn commercial-btn-primary"
                      onClick={() => setActivityOpen(true)}
                    >
                      Add Activity
                    </button>
                  </div>
                  <div className="commercial-timeline-list">
                    {request.activities.length === 0 ? (
                      <div className="commercial-empty">No activity recorded.</div>
                    ) : (
                      [...request.activities]
                        .sort(
                          (left, right) =>
                            new Date(right.createdAt).getTime() -
                            new Date(left.createdAt).getTime(),
                        )
                        .map((activity) => (
                          <article key={activity.id} className="commercial-tl">
                            <b>{activity.activityTypeDisplay}</b>
                            <p>
                              {activity.outcomeDisplay}: {activity.note}
                              <br />
                              <strong>{activity.createdByName || 'System'}</strong>
                            </p>
                            <time>{new Date(activity.createdAt).toLocaleString('en-GB')}</time>
                          </article>
                        ))
                    )}
                  </div>
                </section>

                <section className="commercial-card commercial-request360-card">
                  <div className="commercial-card-header">
                    <div>
                      <h2>Attachments</h2>
                      <p>Request documents and references</p>
                    </div>
                    <button
                      type="button"
                      className="commercial-btn"
                      onClick={() => setAttachmentOpen(true)}
                    >
                      Add Attachment
                    </button>
                  </div>
                  {request.attachments.length === 0 ? (
                    <div className="commercial-empty">No attachments recorded.</div>
                  ) : (
                    <div className="commercial-attachment-list">
                      {request.attachments.map((attachment) => {
                        const title =
                          attachment.label?.trim() || attachment.fileName?.trim() || 'Attachment'
                        const subtitle =
                          normalizeAttachmentText(attachment.fileName) ===
                          normalizeAttachmentText(attachment.label)
                            ? attachment.contentType || 'Open attachment'
                            : attachment.fileName || attachment.contentType || 'Open attachment'

                        return (
                          <a
                            key={attachment.id}
                            href={attachment.fileUrl}
                            target="_blank"
                            rel="noreferrer"
                            className="commercial-attachment-row"
                          >
                            <div className="commercial-upload-item-icon">
                              <FileTypeIcon
                                fileName={
                                  attachment.fileName || attachment.label || attachment.fileUrl
                                }
                                contentType={attachment.contentType}
                              />
                            </div>
                            <div className="commercial-attachment-meta">
                              <div className="commercial-attachment-name">{title}</div>
                              <div className="commercial-attachment-sub">{subtitle}</div>
                            </div>
                            <span className="commercial-attachment-action">
                              <IconExternalLink size={16} />
                            </span>
                          </a>
                        )
                      })}
                    </div>
                  )}
                </section>
              </div>

              <aside className="commercial-g21-side">
                <form
                  className="commercial-card commercial-request360-card"
                  onSubmit={(event) => {
                    event.preventDefault()
                    void controlForm.handleSubmit()
                  }}
                >
                  <div className="commercial-card-header">
                    <div className="commercial-card-title-only">Control Panel</div>
                  </div>

                  <controlForm.Field name="status">
                    {(field) => (
                      <label className="commercial-field">
                        <span>Status</span>
                        <select
                          value={field.state.value}
                          onChange={(event) =>
                            field.handleChange(event.target.value as typeof field.state.value)
                          }
                        >
                          {choices.statuses.map((item) => (
                            <option key={item.value} value={item.value}>
                              {item.label}
                            </option>
                          ))}
                        </select>
                      </label>
                    )}
                  </controlForm.Field>

                  <controlForm.Field name="priority">
                    {(field) => (
                      <label className="commercial-field">
                        <span>Priority</span>
                        <select
                          value={field.state.value}
                          onChange={(event) =>
                            field.handleChange(event.target.value as typeof field.state.value)
                          }
                        >
                          {choices.priorities.map((item) => (
                            <option key={item.value} value={item.value}>
                              {item.label}
                            </option>
                          ))}
                        </select>
                      </label>
                    )}
                  </controlForm.Field>

                  <controlForm.Field name="ownerId">
                    {(field) => (
                      <label className="commercial-field">
                        <span>Owner</span>
                        {employees.length === 0 ? (
                          <input value={request.ownerName || 'Unassigned'} readOnly />
                        ) : (
                          <select
                            value={field.state.value}
                            onChange={(event) => field.handleChange(Number(event.target.value))}
                          >
                            <option value={0}>Unassigned</option>
                            {employees.map((employee) => (
                              <option key={employee.id} value={employee.id}>
                                {employee.name}
                                {employee.roleName ? ` — ${employee.roleName}` : ''}
                              </option>
                            ))}
                          </select>
                        )}
                      </label>
                    )}
                  </controlForm.Field>

                  <controlForm.Field name="dueDate">
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
                  </controlForm.Field>

                  <controlForm.Field name="budget">
                    {(field) => (
                      <label className="commercial-field">
                        <span>Budget</span>
                        <input
                          type="number"
                          min="0"
                          value={formatNumberFieldValue(field.state.value)}
                          onChange={(event) =>
                            field.handleChange(parseNumberFieldValue(event.target.value))
                          }
                        />
                      </label>
                    )}
                  </controlForm.Field>

                  <controlForm.Field name="estimatedValue">
                    {(field) => (
                      <label className="commercial-field">
                        <span>Estimated value</span>
                        <input
                          type="number"
                          min="0"
                          value={formatNumberFieldValue(field.state.value)}
                          onChange={(event) =>
                            field.handleChange(parseNumberFieldValue(event.target.value))
                          }
                        />
                      </label>
                    )}
                  </controlForm.Field>

                  <controlForm.Field name="nextAction">
                    {(field) => (
                      <label className="commercial-field">
                        <span>Next action</span>
                        <input
                          value={field.state.value}
                          onChange={(event) => field.handleChange(event.target.value)}
                        />
                      </label>
                    )}
                  </controlForm.Field>

                  <controlForm.Field name="scopeSummary">
                    {(field) => (
                      <label className="commercial-field">
                        <span>Scope summary</span>
                        <textarea
                          rows={4}
                          value={field.state.value}
                          onChange={(event) => field.handleChange(event.target.value)}
                        />
                      </label>
                    )}
                  </controlForm.Field>

                  <button
                    type="submit"
                    className="commercial-btn commercial-btn-primary commercial-btn-block"
                    disabled={saving}
                  >
                    {saving ? 'Saving...' : 'Save Update'}
                  </button>
                </form>

                <section className="commercial-card commercial-request360-card">
                  <div className="commercial-card-header">
                    <div className="commercial-card-title-only">Commercial Actions</div>
                  </div>
                  <button
                    type="button"
                    className="commercial-btn commercial-btn-block"
                    disabled={!canPrepareQuotation}
                    onClick={onPrepareQuotation}
                  >
                    Prepare Quotation
                  </button>
                  <button
                    type="button"
                    className="commercial-btn commercial-btn-block"
                    disabled={
                      saving || request.status === 'converted' || request.status === 'rejected'
                    }
                    onClick={() =>
                      onUpdate({
                        status: 'site_assessment',
                        nextAction: 'Attend assessment and record findings',
                      })
                    }
                  >
                    Schedule Assessment
                  </button>
                </section>
              </aside>
            </div>
          </div>

          <footer className="commercial-modal-footer">
            <button type="button" className="commercial-btn" onClick={onClose}>
              Close
            </button>
          </footer>
        </section>
      </div>

      {activityOpen ? (
        <div
          className="commercial-modal-backdrop commercial-modal-backdrop--nested"
          role="presentation"
          onMouseDown={() => setActivityOpen(false)}
        >
          <form
            className="commercial-modal"
            onMouseDown={(event) => event.stopPropagation()}
            onSubmit={(event) => {
              event.preventDefault()
              void activityForm.handleSubmit()
            }}
          >
            <header className="commercial-modal-header">
              <h2>Add Request Activity</h2>
              <button
                type="button"
                className="commercial-modal-close"
                onClick={() => setActivityOpen(false)}
              >
                <IconX size={16} />
              </button>
            </header>
            <div className="commercial-modal-body">
              <div className="commercial-form-grid">
                <activityForm.Field name="activityType">
                  {(field) => (
                    <label className="commercial-field">
                      <span>Type</span>
                      <select
                        value={field.state.value}
                        onChange={(event) => field.handleChange(event.target.value)}
                      >
                        {choices.activityTypes.map((item) => (
                          <option key={item.value} value={item.value}>
                            {item.label}
                          </option>
                        ))}
                      </select>
                    </label>
                  )}
                </activityForm.Field>

                <activityForm.Field name="outcome">
                  {(field) => (
                    <label className="commercial-field">
                      <span>Outcome</span>
                      <select
                        value={field.state.value}
                        onChange={(event) => field.handleChange(event.target.value)}
                      >
                        {choices.activityOutcomes.map((item) => (
                          <option key={item.value} value={item.value}>
                            {item.label}
                          </option>
                        ))}
                      </select>
                    </label>
                  )}
                </activityForm.Field>

                <activityForm.Field name="note">
                  {(field) => (
                    <label className="commercial-field commercial-field--full">
                      <span>Detailed note *</span>
                      <textarea
                        rows={4}
                        value={field.state.value}
                        onChange={(event) => field.handleChange(event.target.value)}
                      />
                    </label>
                  )}
                </activityForm.Field>

                <activityForm.Field name="nextAction">
                  {(field) => (
                    <label className="commercial-field">
                      <span>Next action</span>
                      <input
                        value={field.state.value}
                        onChange={(event) => field.handleChange(event.target.value)}
                      />
                    </label>
                  )}
                </activityForm.Field>

                <activityForm.Field name="nextFollowUpAt">
                  {(field) => (
                    <label className="commercial-field">
                      <span>Next follow-up</span>
                      <input
                        type="datetime-local"
                        value={field.state.value}
                        onChange={(event) => field.handleChange(event.target.value)}
                      />
                    </label>
                  )}
                </activityForm.Field>
              </div>
            </div>
            <footer className="commercial-modal-footer">
              <button
                type="button"
                className="commercial-btn"
                onClick={() => setActivityOpen(false)}
              >
                Cancel
              </button>
              <button
                type="submit"
                className="commercial-btn commercial-btn-primary"
                disabled={activitySaving}
              >
                {activitySaving ? 'Saving...' : 'Save Activity'}
              </button>
            </footer>
          </form>
        </div>
      ) : null}

      {attachmentOpen ? (
        <div
          className="commercial-modal-backdrop commercial-modal-backdrop--nested"
          role="presentation"
          onMouseDown={() => {
            resetAttachmentUpload()
            setAttachmentOpen(false)
          }}
        >
          <form
            className="commercial-modal"
            onMouseDown={(event) => event.stopPropagation()}
            onSubmit={(event) => {
              event.preventDefault()
              void attachmentForm.handleSubmit()
            }}
          >
            <header className="commercial-modal-header">
              <h2>Add Request Attachment</h2>
              <button
                type="button"
                className="commercial-modal-close"
                onClick={() => {
                  resetAttachmentUpload()
                  setAttachmentOpen(false)
                }}
              >
                <IconX size={16} />
              </button>
            </header>
            <div className="commercial-modal-body">
              <div className="commercial-form-grid">
                <attachmentForm.Field name="label">
                  {(field) => (
                    <label className="commercial-field">
                      <span>Label</span>
                      <input
                        value={field.state.value}
                        onChange={(event) => field.handleChange(event.target.value)}
                      />
                    </label>
                  )}
                </attachmentForm.Field>
                <div className="commercial-field commercial-field--full commercial-upload-field">
                  <span>File *</span>
                  <label className="commercial-upload-dropzone">
                    <div className="commercial-upload-dropzone-icon">
                      <IconUpload size={18} />
                    </div>
                    <div>
                      <strong>Add document</strong>
                      <small>Upload the file now and attach it to this request when ready.</small>
                    </div>
                    <input
                      type="file"
                      onChange={(event) => {
                        const file = event.target.files?.[0]
                        if (file) void uploadAttachmentFile(file)
                        event.target.value = ''
                      }}
                    />
                  </label>

                  {pendingAttachment ? (
                    <div className="commercial-upload-list">
                      <article
                        className={`commercial-upload-item commercial-upload-item--${pendingAttachment.status}`}
                      >
                        <div className="commercial-upload-item-icon">
                          <FileTypeIcon
                            fileName={pendingAttachment.fileName}
                            contentType={pendingAttachment.contentType}
                          />
                        </div>
                        <div className="commercial-upload-item-body">
                          <div className="commercial-upload-item-top">
                            <strong>{pendingAttachment.fileName}</strong>
                            <span>{formatBytes(pendingAttachment.fileSizeBytes)}</span>
                          </div>
                          {pendingAttachment.status === 'uploading' ? (
                            <div className="commercial-upload-progress">
                              <div className="commercial-upload-progress-bar" />
                            </div>
                          ) : null}
                          {pendingAttachment.status === 'uploaded' ? (
                            <small>Ready to attach to this request</small>
                          ) : null}
                          {pendingAttachment.status === 'error' ? (
                            <small>{pendingAttachment.error}</small>
                          ) : null}
                        </div>
                        <div className="commercial-upload-actions">
                          {pendingAttachment.status === 'error' ? (
                            <button
                              type="button"
                              className="commercial-upload-remove"
                              onClick={retryAttachmentUpload}
                              aria-label={`Retry ${pendingAttachment.fileName}`}
                            >
                              <IconRefresh size={14} />
                            </button>
                          ) : null}
                          <button
                            type="button"
                            className="commercial-upload-remove"
                            onClick={resetAttachmentUpload}
                            aria-label={`Remove ${pendingAttachment.fileName}`}
                          >
                            {pendingAttachment.status === 'uploading' ? (
                              <IconX size={14} />
                            ) : (
                              <IconTrash size={14} />
                            )}
                          </button>
                        </div>
                      </article>
                    </div>
                  ) : null}

                  {attachmentError ? (
                    <small className="commercial-field-error">{attachmentError}</small>
                  ) : null}
                </div>
              </div>
            </div>
            <footer className="commercial-modal-footer">
              <button
                type="button"
                className="commercial-btn"
                onClick={() => {
                  resetAttachmentUpload()
                  setAttachmentOpen(false)
                }}
              >
                Cancel
              </button>
              <button
                type="submit"
                className="commercial-btn commercial-btn-primary"
                disabled={attachmentSaving || pendingAttachment?.status === 'uploading'}
              >
                {attachmentSaving ? 'Saving...' : 'Add Attachment'}
              </button>
            </footer>
          </form>
        </div>
      ) : null}
    </>
  )
}
