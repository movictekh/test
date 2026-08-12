import { IconRefresh, IconTrash, IconUpload, IconX } from '@tabler/icons-react'
import { useQuery } from '@tanstack/react-query'
import { useForm } from '@tanstack/react-form'
import { useEffect, useRef, useState } from 'react'

import { presentError } from '@/shared/errors'
import { serviceRequestsApi } from '@/modules/commercial/api/service-requests.api'
import { FileTypeIcon } from '@/modules/commercial/request-intake/file-presentation'
import { formatBytes } from '@/modules/commercial/request-intake/file-presentation.utils'

import type { EmployeeOption, ServiceOrder } from '../service-orders/service-order.types'
import { serviceOrderQueries } from '../service-orders/service-order.queries'
import { executionTaskQueries } from '../execution-tasks/execution-task.queries'
import {
  deliverableApprovalModes,
  deliverableTypes,
  type CreateDeliverableInput,
  type DeliverableApprovalMode,
  type DeliverableType,
} from '../deliverables/deliverable.types'
import { validateDeliverableCreate } from '../deliverables/deliverable.validation'

type FormValues = {
  milestoneId: number
  taskId: number
  title: string
  deliverableType: DeliverableType
  version: string
  fileUrl: string
  fileName: string
  contentType: string
  fileSizeBytes: number
  description: string
  clientVisible: boolean
  approvalMode: DeliverableApprovalMode
  ownerId: number
}

type PendingDocumentUpload = {
  file: File
  fileName: string
  fileSizeBytes: number
  contentType: string
  fileUrl: string
  status: 'uploading' | 'uploaded' | 'error'
  error: string
}

function label(value: string) {
  return value.replaceAll('_', ' ').replace(/\b\w/g, (letter) => letter.toUpperCase())
}

export function CreateDeliverableLiveWorkspace({
  initialOrder,
  orders,
  employees,
  saving,
  onClose,
  onSubmit,
}: {
  initialOrder: ServiceOrder | null
  orders: ServiceOrder[]
  employees: EmployeeOption[]
  saving: boolean
  onClose: () => void
  onSubmit: (orderId: number, input: CreateDeliverableInput) => void
}) {
  const [selectedOrderId, setSelectedOrderId] = useState(initialOrder?.id ?? 0)
  const [error, setError] = useState('')
  const [documentUpload, setDocumentUpload] = useState<PendingDocumentUpload | null>(null)
  const uploadControllerRef = useRef<AbortController | null>(null)

  const selectedOrderQuery = useQuery({
    ...serviceOrderQueries.detail(selectedOrderId || 0),
    enabled: Boolean(selectedOrderId) && initialOrder?.id !== selectedOrderId,
  })

  const activeOrder =
    initialOrder?.id === selectedOrderId ? initialOrder : (selectedOrderQuery.data ?? null)

  const tasksQuery = useQuery({
    ...executionTaskQueries.list(activeOrder?.id ?? 0, { page: 1, limit: 100 }),
    enabled: Boolean(activeOrder),
  })

  const defaultValues: FormValues = {
    milestoneId: 0,
    taskId: 0,
    title: '',
    deliverableType: 'report',
    version: 'v1',
    fileUrl: '',
    fileName: '',
    contentType: '',
    fileSizeBytes: 0,
    description: '',
    clientVisible: true,
    approvalMode: 'supervisor',
    ownerId: 0,
  }

  const form = useForm({
    defaultValues,
    onSubmit: ({ value }) => {
      if (!activeOrder) {
        setError('Select a Service Order before adding a Deliverable.')
        return
      }

      const input: CreateDeliverableInput = {
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
        clientVisible: value.clientVisible,
        approvalMode: value.approvalMode,
        ownerId: value.ownerId || null,
      }

      const validationError = validateDeliverableCreate(input)
      setError(validationError)
      if (validationError) return

      onSubmit(activeOrder.id, input)
    },
  })

  useEffect(() => {
    form.setFieldValue('milestoneId', 0)
    form.setFieldValue('taskId', 0)
  }, [selectedOrderId, form])

  const resetDocumentUpload = () => {
    uploadControllerRef.current?.abort()
    uploadControllerRef.current = null
    setDocumentUpload(null)
    form.setFieldValue('fileUrl', '')
    form.setFieldValue('fileName', '')
    form.setFieldValue('contentType', '')
    form.setFieldValue('fileSizeBytes', 0)
  }

  const uploadDocumentFile = async (file: File) => {
    uploadControllerRef.current?.abort()
    const controller = new AbortController()
    uploadControllerRef.current = controller

    setDocumentUpload({
      file,
      fileName: file.name,
      fileSizeBytes: file.size,
      contentType: file.type,
      fileUrl: '',
      status: 'uploading',
      error: '',
    })

    form.setFieldValue('fileName', file.name)
    form.setFieldValue('contentType', file.type)
    form.setFieldValue('fileSizeBytes', file.size)

    try {
      const fileUrl = await serviceRequestsApi.uploadFile(file, controller.signal)
      setDocumentUpload({
        file,
        fileName: file.name,
        fileSizeBytes: file.size,
        contentType: file.type,
        fileUrl,
        status: 'uploaded',
        error: '',
      })
      form.setFieldValue('fileUrl', fileUrl)
    } catch (uploadError) {
      if (controller.signal.aborted) return
      const message = presentError(uploadError, 'background-action').message
      setDocumentUpload({
        file,
        fileName: file.name,
        fileSizeBytes: file.size,
        contentType: file.type,
        fileUrl: '',
        status: 'error',
        error: message,
      })
      form.setFieldValue('fileUrl', '')
      setError(message)
    } finally {
      if (uploadControllerRef.current === controller) {
        uploadControllerRef.current = null
      }
    }
  }

  const retryDocumentUpload = () => {
    if (!documentUpload) return
    void uploadDocumentFile(documentUpload.file)
  }

  const tasks = tasksQuery.data?.items ?? []

  return (
    <div className="commercial-modal-backdrop" role="presentation" onMouseDown={onClose}>
      <form
        className="commercial-modal commercial-modal--xl"
        role="dialog"
        aria-modal="true"
        aria-label="Add Deliverable"
        onMouseDown={(event) => event.stopPropagation()}
        onSubmit={(event) => {
          event.preventDefault()
          void form.handleSubmit()
        }}
      >
        <header className="commercial-modal-header">
          <div>
            <h2>Add Deliverable / Document</h2>
            <p>
              {activeOrder
                ? `${activeOrder.orderNumber} · ${activeOrder.serviceName}`
                : 'Select a Service Order to continue'}
            </p>
          </div>
          <button
            type="button"
            className="commercial-modal-close"
            onClick={onClose}
            aria-label="Close"
          >
            ×
          </button>
        </header>

        <div className="commercial-modal-body">
          <section className="commercial-form-section">
            <div className="commercial-form-section-heading">
              <div>
                <h3>Deliverable Context</h3>
                <p>Link the output to its Service Order, Milestone and Execution Task.</p>
              </div>
            </div>

            <div className="commercial-form-grid">
              <label className="commercial-field commercial-field--full">
                <span>Service Order *</span>
                <select
                  autoFocus={!initialOrder}
                  value={selectedOrderId}
                  disabled={Boolean(initialOrder)}
                  onChange={(event) => setSelectedOrderId(Number(event.target.value))}
                >
                  <option value={0}>Select a Service Order</option>
                  {[...orders]
                    .sort((left, right) => left.orderNumber.localeCompare(right.orderNumber))
                    .map((order) => (
                      <option key={order.id} value={order.id}>
                        {order.orderNumber} · {order.serviceName}
                      </option>
                    ))}
                </select>
              </label>

              <form.Field name="milestoneId">
                {(field) => (
                  <label className="commercial-field">
                    <span>Milestone</span>
                    <select
                      value={field.state.value}
                      disabled={!activeOrder}
                      onChange={(event) => field.handleChange(Number(event.target.value))}
                    >
                      <option value={0}>No milestone</option>
                      {[...(activeOrder?.milestones ?? [])]
                        .sort(
                          (left, right) => left.sortOrder - right.sortOrder || left.id - right.id,
                        )
                        .map((milestone) => (
                          <option key={milestone.id} value={milestone.id}>
                            {milestone.name} · {label(milestone.status)}
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
                      disabled={!activeOrder || tasksQuery.isPending}
                      onChange={(event) => field.handleChange(Number(event.target.value))}
                    >
                      <option value={0}>
                        {tasksQuery.isPending ? 'Loading tasks…' : 'No task link'}
                      </option>
                      {tasks.map((task) => (
                        <option key={task.id} value={task.id}>
                          {task.taskNumber} · {task.title} · {label(task.status)}
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
                          {employee.designation ? ` · ${employee.designation}` : ''}
                        </option>
                      ))}
                    </select>
                  </label>
                )}
              </form.Field>
            </div>
          </section>

          {error ? <div className="commercial-notice commercial-notice-red">{error}</div> : null}

          <section className="commercial-form-section">
            <div className="commercial-form-section-heading">
              <div>
                <h3>Deliverable Information</h3>
                <p>Describe the formal output being handed into the fulfillment record.</p>
              </div>
            </div>

            <div className="commercial-form-grid">
              <form.Field name="title">
                {(field) => (
                  <label className="commercial-field commercial-field--full">
                    <span>Title *</span>
                    <input
                      autoFocus={Boolean(initialOrder)}
                      required
                      value={field.state.value}
                      onChange={(event) => field.handleChange(event.target.value)}
                      placeholder="e.g. Final Boundary Survey Report"
                    />
                  </label>
                )}
              </form.Field>

              <form.Field name="deliverableType">
                {(field) => (
                  <label className="commercial-field">
                    <span>Type</span>
                    <select
                      value={field.state.value}
                      onChange={(event) =>
                        field.handleChange(event.target.value as DeliverableType)
                      }
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
                      required
                      value={field.state.value}
                      onChange={(event) => field.handleChange(event.target.value)}
                      placeholder="v1"
                    />
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
                      placeholder="Describe the document, output or evidence."
                    />
                  </label>
                )}
              </form.Field>
            </div>
          </section>

          <section className="commercial-form-section">
            <div className="commercial-form-section-heading">
              <div>
                <h3>Document Reference</h3>
                <p>Upload the document and the form will store its reference automatically.</p>
              </div>
            </div>

            <div className="commercial-form-grid">
              <div className="commercial-field commercial-field--full commercial-upload-field">
                <span>Document *</span>
                <label className="commercial-upload-dropzone">
                  <div className="commercial-upload-dropzone-icon">
                    <IconUpload size={18} />
                  </div>
                  <div>
                    <strong>Select document</strong>
                    <small>
                      Upload the file now and the deliverable will store the reference
                      automatically.
                    </small>
                  </div>
                  <input
                    type="file"
                    onChange={(event) => {
                      const file = event.target.files?.[0]
                      if (file) void uploadDocumentFile(file)
                      event.target.value = ''
                    }}
                  />
                </label>

                {documentUpload ? (
                  <div className="commercial-upload-list">
                    <article
                      className={`commercial-upload-item commercial-upload-item--${documentUpload.status}`}
                    >
                      <div className="commercial-upload-item-icon">
                        <FileTypeIcon
                          fileName={documentUpload.fileName}
                          contentType={documentUpload.contentType}
                        />
                      </div>
                      <div className="commercial-upload-item-body">
                        <div className="commercial-upload-item-top">
                          <strong>{documentUpload.fileName}</strong>
                          <span>{formatBytes(documentUpload.fileSizeBytes)}</span>
                        </div>
                        {documentUpload.status === 'uploading' ? (
                          <div className="commercial-upload-progress">
                            <div className="commercial-upload-progress-bar" />
                          </div>
                        ) : null}
                        {documentUpload.status === 'uploaded' ? (
                          <small>Ready to save this deliverable</small>
                        ) : null}
                        {documentUpload.status === 'error' ? (
                          <small>{documentUpload.error}</small>
                        ) : null}
                      </div>
                      <div className="commercial-upload-actions">
                        {documentUpload.status === 'error' ? (
                          <button
                            type="button"
                            className="commercial-upload-remove"
                            onClick={retryDocumentUpload}
                            aria-label={`Retry ${documentUpload.fileName}`}
                          >
                            <IconRefresh size={14} />
                          </button>
                        ) : null}
                        <button
                          type="button"
                          className="commercial-upload-remove"
                          onClick={resetDocumentUpload}
                          aria-label={`Remove ${documentUpload.fileName}`}
                        >
                          {documentUpload.status === 'uploading' ? (
                            <IconX size={14} />
                          ) : (
                            <IconTrash size={14} />
                          )}
                        </button>
                      </div>
                    </article>
                  </div>
                ) : (
                  <small>
                    Choose a file so the system can upload it and store the reference automatically.
                  </small>
                )}
              </div>
            </div>
          </section>

          <section className="commercial-form-section">
            <div className="commercial-form-section-heading">
              <div>
                <h3>Visibility & Approval</h3>
                <p>Status is derived by the backend from the selected approval mode.</p>
              </div>
            </div>

            <div className="commercial-form-grid">
              <form.Field name="approvalMode">
                {(field) => (
                  <label className="commercial-field">
                    <span>Approval mode</span>
                    <select
                      value={field.state.value}
                      onChange={(event) => {
                        const next = event.target.value as DeliverableApprovalMode
                        field.handleChange(next)
                        if (next === 'client') form.setFieldValue('clientVisible', true)
                      }}
                    >
                      {deliverableApprovalModes.map((mode) => (
                        <option key={mode.value} value={mode.value}>
                          {mode.label}
                        </option>
                      ))}
                    </select>
                  </label>
                )}
              </form.Field>

              <form.Field name="clientVisible">
                {(field) => (
                  <label className="commercial-check">
                    <input
                      type="checkbox"
                      checked={field.state.value}
                      disabled={form.state.values.approvalMode === 'client'}
                      onChange={(event) => field.handleChange(event.target.checked)}
                    />
                    <span>
                      <b>Visible to client</b>
                      <small>Required when approval mode is set to client.</small>
                    </span>
                  </label>
                )}
              </form.Field>
            </div>
          </section>
        </div>

        <footer className="commercial-modal-footer">
          <button type="button" className="commercial-btn" disabled={saving} onClick={onClose}>
            Cancel
          </button>
          <button
            type="submit"
            className="commercial-btn commercial-btn-primary"
            disabled={saving || !activeOrder}
          >
            {saving ? 'Adding...' : 'Add Deliverable'}
          </button>
        </footer>
      </form>
    </div>
  )
}
