import {
  IconAlertCircle,
  IconCalculator,
  IconChevronDown,
  IconLoader2,
  IconX,
} from '@tabler/icons-react'
import { useForm } from '@tanstack/react-form'
import { useQuery } from '@tanstack/react-query'
import { useRef, useState } from 'react'

import { presentError } from '@/shared/errors'
import { formatCurrency } from '@/shared/lib/formatters'
import { parseNumberFieldValue } from '@/shared/lib/number-input'
import { Button } from '@/shared/ui/button'
import { EmptyState } from '@/shared/ui/empty-state'
import { useToast } from '@/shared/ui/toast/useToast'

import { serviceRequestsApi } from '../api/service-requests.api'
import { serviceRequestQueries } from '../api/service-requests.queries'
import type {
  ClientOption,
  CreateServiceRequestAttachmentInput,
  CreateServiceRequestInput,
  IntakeField,
  ServiceOption,
  ServiceRequestChoices,
} from '../api/service-requests.types'

import { RequestIntakeFields } from '../request-intake/RequestIntakeFields'
import type { PendingUpload } from '../request-intake/request-intake.types'
import {
  calculateEstimateTotal,
  firstScopeValue,
  isBudgetField,
  isPreferredDateField,
  isPriorityValue,
  isScopeField,
  normalizeAnswers,
  nonNegativeNumber,
  resolveAutoAnswer,
  shouldHideAutoField,
  validateAnswerFields,
  validateAnswers,
} from '../request-intake/request-intake.utils'

export function CreateServiceRequestLiveWorkspace({
  clients,
  services,
  choices,
  saving,
  onClose,
  onSubmit,
}: {
  clients: ClientOption[]
  services: ServiceOption[]
  choices: ServiceRequestChoices
  saving: boolean
  onClose: () => void
  onSubmit: (
    input: CreateServiceRequestInput,
    attachments: CreateServiceRequestAttachmentInput[],
  ) => Promise<unknown> | void
}) {
  const toast = useToast()
  const activeClients = clients.filter((item) => item.active)
  const initialClient = activeClients[0] ?? null
  const [serviceId, setServiceId] = useState(0)
  const [error, setError] = useState('')
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})
  const [showInternalDetails, setShowInternalDetails] = useState(false)
  const [uploadsByField, setUploadsByField] = useState<Record<string, PendingUpload[]>>({})
  const [answerValues, setAnswerValues] = useState<Record<string, unknown>>({})
  const controllersRef = useRef<Record<string, AbortController>>({})
  const uploadIdRef = useRef(0)
  const fieldRefs = useRef<Record<string, HTMLElement | null>>({})

  const intakeQuery = useQuery({
    ...serviceRequestQueries.intake(serviceId),
    enabled: serviceId > 0,
  })
  const pricingConfigQuery = useQuery({
    ...serviceRequestQueries.pricingConfig(serviceId),
    enabled: serviceId > 0,
  })

  const selectedService = services.find((item) => item.id === serviceId) ?? null
  const branches = selectedService?.activeBranches ?? []
  const fields = intakeQuery.data?.form.fields ?? []
  const subservices = intakeQuery.data?.subservices ?? []
  const hasBudgetField = fields.some(isBudgetField)
  const hasPreferredDateField = fields.some(isPreferredDateField)
  const hasScopeSummaryField = fields.some(isScopeField)
  const flattenedUploads = Object.values(uploadsByField).flat()
  const hasUploadingFiles = flattenedUploads.some((upload) => upload.status === 'uploading')
  const hasUploadErrors = flattenedUploads.some((upload) => upload.status === 'error')
  const initialAnswers: Record<string, unknown> = {}
  const activePricingConfig = pricingConfigQuery.data

  const form = useForm({
    defaultValues: {
      clientId: initialClient?.id ?? 0,
      contactName: initialClient?.name ?? '',
      contactPhone: initialClient?.phone ?? '',
      contactEmail: initialClient?.email ?? '',
      customerType: choices.customerTypes[0]?.value ?? 'individual',
      source:
        choices.sources.find((item) => item.value === 'sales_crm')?.value ??
        choices.sources[0]?.value ??
        'sales_crm',
      sourceReference: '',
      priority: (choices.priorities[0]?.value ?? 'normal') as 'normal' | 'high' | 'critical',
      subserviceId: 0,
      branchId: 0,
      budget: 0,
      estimatedValue: 0,
      preferredDate: '',
      dueDate: '',
      nextAction: '',
      scopeSummary: '',
      answers: initialAnswers,
    },
    onSubmit: async ({ value }) => {
      if (!value.clientId) {
        setError('Select a client.')
        return
      }

      if (!serviceId) {
        setError('Select a service.')
        return
      }

      if (branches.length > 0 && !value.branchId) {
        setError('Select an active branch.')
        return
      }

      if (hasUploadingFiles) {
        setError('Wait for document uploads to finish before submitting.')
        return
      }

      if (hasUploadErrors) {
        setError('Remove failed document uploads or upload them again before submitting.')
        return
      }

      const resolvedAnswers = Object.fromEntries(
        fields.map((field) => [
          field.key,
          field.fieldType === 'file'
            ? resolveAutoAnswer(field, {
                contactName: value.contactName.trim(),
                contactPhone: value.contactPhone.trim(),
                contactEmail: value.contactEmail.trim(),
                customerType: value.customerType,
                budget: value.budget,
                preferredDate: value.preferredDate,
                uploads: flattenedUploads,
              })
            : shouldHideAutoField(field, {
                  contactName: value.contactName.trim(),
                  contactPhone: value.contactPhone.trim(),
                  contactEmail: value.contactEmail.trim(),
                  customerType: value.customerType,
                  budget: value.budget,
                  preferredDate: value.preferredDate,
                  uploads: flattenedUploads,
                })
              ? resolveAutoAnswer(field, {
                  contactName: value.contactName.trim(),
                  contactPhone: value.contactPhone.trim(),
                  contactEmail: value.contactEmail.trim(),
                  customerType: value.customerType,
                  budget: value.budget,
                  preferredDate: value.preferredDate,
                  uploads: flattenedUploads,
                })
              : value.answers[field.key],
        ]),
      )

      const answerErrors = validateAnswerFields(fields, resolvedAnswers)
      if (Object.keys(answerErrors).length > 0) {
        setFieldErrors(answerErrors)
        setError('')
        const firstErrorKey = visibleFields.find((field) => answerErrors[field.key])?.key
        if (firstErrorKey) {
          window.requestAnimationFrame(() => {
            const node = fieldRefs.current[firstErrorKey]
            node?.scrollIntoView({ behavior: 'smooth', block: 'center' })
            if (
              node instanceof HTMLInputElement ||
              node instanceof HTMLTextAreaElement ||
              node instanceof HTMLSelectElement
            ) {
              node.focus()
            }
          })
        }
        return
      }

      const validationError = validateAnswers(fields, resolvedAnswers)
      if (validationError) {
        setError(validationError)
        return
      }

      const normalizedAnswers = normalizeAnswers(fields, resolvedAnswers)
      const derivedBudget =
        value.budget > 0
          ? value.budget
          : (() => {
              const budgetField = fields.find(isBudgetField)
              if (!budgetField) return 0
              const rawBudget = normalizedAnswers[budgetField.key]
              return parseNumberFieldValue(
                typeof rawBudget === 'string' || typeof rawBudget === 'number'
                  ? String(rawBudget)
                  : '',
              )
            })()
      const derivedScopeSummary =
        value.scopeSummary.trim() || firstScopeValue(fields, normalizedAnswers) || ''
      const attachments = flattenedUploads
        .filter((upload) => upload.status === 'uploaded')
        .map((upload) => ({
          fieldKey: upload.fieldKey,
          label: upload.label,
          fileName: upload.fileName,
          fileUrl: upload.fileUrl,
          contentType: upload.contentType,
          fileSizeBytes: upload.fileSizeBytes,
        }))

      setError('')
      setFieldErrors({})

      try {
        await onSubmit(
          {
            clientId: value.clientId,
            serviceId,
            ...(value.subserviceId ? { subserviceId: value.subserviceId } : {}),
            ...(value.branchId ? { branchId: value.branchId } : {}),
            contactName: value.contactName.trim(),
            contactPhone: value.contactPhone.trim(),
            contactEmail: value.contactEmail.trim(),
            customerType: value.customerType,
            source: value.source,
            sourceReference: value.sourceReference.trim(),
            priority: value.priority,
            ...(derivedBudget > 0 ? { budget: derivedBudget } : {}),
            estimatedValue: Number(value.estimatedValue || derivedBudget || 0),
            ...(value.preferredDate ? { preferredDate: value.preferredDate } : {}),
            ...(value.dueDate ? { dueDate: value.dueDate } : {}),
            nextAction: value.nextAction.trim(),
            scopeSummary: derivedScopeSummary,
            answers: normalizedAnswers,
          },
          attachments,
        )
      } catch (submitError) {
        setError(presentError(submitError, 'form-submit').message)
      }
    },
  })

  const updateUploadsForField = (
    fieldKey: string,
    updater: (current: PendingUpload[]) => PendingUpload[],
  ) => {
    setUploadsByField((current) => ({
      ...current,
      [fieldKey]: updater(current[fieldKey] ?? []),
    }))
  }

  const clearUploads = () => {
    Object.values(controllersRef.current).forEach((controller) => controller.abort())
    controllersRef.current = {}
    setUploadsByField({})
  }

  const chooseClient = (clientId: number) => {
    const client = clients.find((item) => item.id === clientId)
    form.setFieldValue('clientId', clientId)
    form.setFieldValue('contactName', client?.name ?? '')
    form.setFieldValue('contactPhone', client?.phone ?? '')
    form.setFieldValue('contactEmail', client?.email ?? '')
  }

  const chooseService = (nextServiceId: number) => {
    const service = services.find((item) => item.id === nextServiceId)
    clearUploads()
    setServiceId(nextServiceId)
    form.setFieldValue('branchId', service?.activeBranches[0]?.id ?? 0)
    form.setFieldValue('subserviceId', 0)
    form.setFieldValue('estimatedValue', 0)
    form.setFieldValue('answers', {})
    setAnswerValues({})
    setFieldErrors({})
    setError('')
  }

  const removeUpload = (fieldKey: string, uploadId: string) => {
    const controller = controllersRef.current[uploadId]
    if (controller) {
      controller.abort()
      delete controllersRef.current[uploadId]
    }
    updateUploadsForField(fieldKey, (current) => current.filter((upload) => upload.id !== uploadId))
  }

  const uploadFile = async (field: IntakeField, file: File, uploadId?: string) => {
    const nextUploadId = uploadId ?? `${field.key}-${++uploadIdRef.current}`
    const controller = new AbortController()
    controllersRef.current[nextUploadId] = controller

    updateUploadsForField(field.key, (current) => {
      const nextItem: PendingUpload = {
        id: nextUploadId,
        fieldKey: field.key,
        label: field.label,
        file,
        fileName: file.name,
        fileSizeBytes: file.size,
        contentType: file.type,
        fileUrl: '',
        status: 'uploading',
        error: '',
      }

      if (uploadId) {
        return current.map((upload) => (upload.id === nextUploadId ? nextItem : upload))
      }

      return [...current, nextItem]
    })

    try {
      const fileUrl = await serviceRequestsApi.uploadFile(file, controller.signal)
      updateUploadsForField(field.key, (current) =>
        current.map((upload) =>
          upload.id === nextUploadId
            ? {
                ...upload,
                fileUrl,
                status: 'uploaded',
              }
            : upload,
        ),
      )
    } catch (uploadError) {
      if (!controller.signal.aborted) {
        const message = presentError(uploadError, 'background-action').message
        updateUploadsForField(field.key, (current) =>
          current.map((upload) =>
            upload.id === nextUploadId
              ? {
                  ...upload,
                  status: 'error',
                  error: message,
                }
              : upload,
          ),
        )
        toast.error('Document upload failed', { description: message })
      }
    } finally {
      delete controllersRef.current[nextUploadId]
    }
  }

  const retryUpload = (upload: PendingUpload) => {
    void uploadFile(
      {
        id: 0,
        key: upload.fieldKey,
        label: upload.label,
        fieldType: 'file',
        required: false,
        options: [],
        validation: {},
        helpText: '',
        placeholder: '',
        sortOrder: 0,
      },
      upload.file,
      upload.id,
    )
  }

  const handleFileSelection = async (field: IntakeField, files: FileList | null) => {
    if (!files || files.length === 0) return

    for (const file of Array.from(files)) {
      await uploadFile(field, file)
    }
  }

  const setAnswerValue = (fieldKey: string, next: unknown) => {
    const nextAnswers = {
      ...answerValues,
      [fieldKey]: next,
    }
    setAnswerValues(nextAnswers)
    form.setFieldValue('answers', {
      ...nextAnswers,
    })
    setFieldErrors((current) => {
      if (!current[fieldKey]) return current
      const nextErrors = { ...current }
      delete nextErrors[fieldKey]
      return nextErrors
    })
  }

  const ready = activeClients.length > 0 && services.length > 0
  const intakeErrorMessage = intakeQuery.isError
    ? presentError(intakeQuery.error, 'section-load').message
    : ''
  const autoAnswerContext = {
    contactName: form.state.values.contactName.trim(),
    contactPhone: form.state.values.contactPhone.trim(),
    contactEmail: form.state.values.contactEmail.trim(),
    customerType: form.state.values.customerType,
    budget: form.state.values.budget,
    preferredDate: form.state.values.preferredDate,
    uploads: flattenedUploads,
  }
  const visibleFields = fields.filter((field) => !shouldHideAutoField(field, autoAnswerContext))
  const estimatePreview =
    activePricingConfig && !pricingConfigQuery.isError
      ? calculateEstimateTotal(activePricingConfig, fields, answerValues, autoAnswerContext)
      : null

  const calculateEstimate = () => {
    if (pricingConfigQuery.isPending) {
      toast.error('Pricing is still loading.')
      return
    }

    if (!activePricingConfig || pricingConfigQuery.isError) {
      toast.error('No active pricing setup is available for this service.')
      return
    }

    const result = calculateEstimateTotal(
      activePricingConfig,
      fields,
      answerValues,
      autoAnswerContext,
    )
    if (!result.supported) {
      toast.error('Estimate cannot be calculated yet.', {
        description: result.reason,
      })
      return
    }

    form.setFieldValue('estimatedValue', result.total)
    toast.success(`Estimate calculated: ${formatCurrency(result.total)}`)
  }

  const retryIntakeForm = () => {
    void intakeQuery.refetch()
  }

  return (
    <div className="commercial-modal-backdrop" role="presentation" onMouseDown={onClose}>
      <form
        className="commercial-modal commercial-modal--xl"
        aria-label="Create Service Request"
        onMouseDown={(event) => event.stopPropagation()}
        onSubmit={(event) => {
          event.preventDefault()
          event.stopPropagation()
          void form.handleSubmit()
        }}
      >
        <header className="commercial-modal-header">
          <div>
            <h2>Create Service Request</h2>
            <p>Create a commercial request using the selected service intake form.</p>
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
          {!ready ? (
            <EmptyState
              title="Request cannot be created yet"
              description={
                activeClients.length === 0
                  ? 'Add at least one active client before creating a service request.'
                  : 'There are no active services available for request intake right now.'
              }
            />
          ) : (
            <>
              {error ? (
                <div className="service-admin-notice service-admin-notice-red">{error}</div>
              ) : null}

              <section className="commercial-form-section">
                <div className="commercial-form-section-heading">
                  <div>
                    <h3>Client</h3>
                    <p>Select the existing client record for this request.</p>
                  </div>
                </div>
                <div className="commercial-form-grid">
                  <form.Field name="clientId">
                    {(field) => (
                      <label className="commercial-field commercial-field--full">
                        <span>Client / organization *</span>
                        <select
                          value={field.state.value}
                          onChange={(event) => chooseClient(Number(event.target.value))}
                        >
                          {activeClients.map((client) => (
                            <option key={client.id} value={client.id}>
                              {client.name} — {client.email}
                            </option>
                          ))}
                        </select>
                      </label>
                    )}
                  </form.Field>
                </div>
              </section>

              <section className="commercial-form-section">
                <div className="commercial-form-section-heading">
                  <div>
                    <h3>Service</h3>
                    <p>Only routing choices that matter for this request stay editable.</p>
                  </div>
                </div>
                <div className="commercial-form-grid">
                  <label className="commercial-field">
                    <span>Service *</span>
                    <select
                      value={serviceId}
                      onChange={(event) => chooseService(Number(event.target.value))}
                    >
                      <option value={0}>Select a service</option>
                      {services.map((service) => (
                        <option key={service.id} value={service.id}>
                          {service.name}
                        </option>
                      ))}
                    </select>
                  </label>

                  <label className="commercial-field">
                    <span>Division</span>
                    <input value={selectedService?.division ?? ''} readOnly />
                  </label>

                  {branches.length > 1 ? (
                    <form.Field name="branchId">
                      {(field) => (
                        <label className="commercial-field">
                          <span>Active branch *</span>
                          <select
                            value={field.state.value}
                            onChange={(event) => field.handleChange(Number(event.target.value))}
                          >
                            {branches.map((branch) => (
                              <option key={branch.id} value={branch.id}>
                                {branch.name}
                              </option>
                            ))}
                          </select>
                        </label>
                      )}
                    </form.Field>
                  ) : (
                    <label className="commercial-field">
                      <span>Active branch</span>
                      <input value={branches[0]?.name ?? 'No active branch'} readOnly />
                    </label>
                  )}

                  {subservices.length > 0 ? (
                    <form.Field name="subserviceId">
                      {(field) => (
                        <label className="commercial-field">
                          <span>Sub-service</span>
                          <select
                            value={field.state.value}
                            onChange={(event) => field.handleChange(Number(event.target.value))}
                          >
                            <option value={0}>None</option>
                            {subservices.map((item) => (
                              <option key={item.id} value={item.id}>
                                {item.name}
                              </option>
                            ))}
                          </select>
                        </label>
                      )}
                    </form.Field>
                  ) : null}
                </div>
              </section>

              {!selectedService ? (
                <EmptyState
                  title="Select a service"
                  description="Choose the service you want to request before the intake form can be loaded."
                />
              ) : intakeQuery.isPending ? (
                <div className="commercial-empty">Loading request form...</div>
              ) : intakeQuery.isError ? (
                <EmptyState
                  title="Request form unavailable"
                  description={
                    intakeErrorMessage ||
                    'This service is not ready for request intake yet. Publish its request form and try again.'
                  }
                  action={
                    <Button variant="outline" size="sm" onClick={retryIntakeForm}>
                      Retry
                    </Button>
                  }
                />
              ) : (
                <>
                  <section className="commercial-form-section">
                    <div className="commercial-form-section-heading">
                      <div>
                        <h3>{intakeQuery.data?.form.name ?? 'Request details'}</h3>
                        <p>
                          These questions are specific to this service and become part of the
                          request record.
                        </p>
                      </div>
                    </div>
                    <div className="commercial-form-grid">
                      <RequestIntakeFields
                        fields={visibleFields}
                        answerValues={answerValues}
                        fieldErrors={fieldErrors}
                        uploadsByField={uploadsByField}
                        fieldRefs={fieldRefs}
                        onValueChange={setAnswerValue}
                        onFileSelection={handleFileSelection}
                        onRetryUpload={retryUpload}
                        onRemoveUpload={removeUpload}
                      />
                    </div>
                  </section>

                  <section className="commercial-form-section">
                    <button
                      type="button"
                      className="commercial-inline-toggle"
                      onClick={() => setShowInternalDetails((current) => !current)}
                    >
                      <span>Optional internal details</span>
                      <IconChevronDown
                        size={16}
                        className={showInternalDetails ? 'commercial-inline-toggle-icon-open' : ''}
                      />
                    </button>
                    {showInternalDetails ? (
                      <div className="commercial-form-grid commercial-form-grid-top">
                        <form.Field name="priority">
                          {(field) => (
                            <label className="commercial-field">
                              <span>Priority</span>
                              <select
                                value={field.state.value}
                                onChange={(event) => {
                                  const nextValue = event.target.value
                                  if (isPriorityValue(nextValue)) field.handleChange(nextValue)
                                }}
                              >
                                {choices.priorities.map((item) => (
                                  <option key={item.value} value={item.value}>
                                    {item.label}
                                  </option>
                                ))}
                              </select>
                            </label>
                          )}
                        </form.Field>

                        <form.Field name="sourceReference">
                          {(field) => (
                            <label className="commercial-field">
                              <span>Lead / campaign reference</span>
                              <input
                                value={field.state.value}
                                onChange={(event) => field.handleChange(event.target.value)}
                              />
                            </label>
                          )}
                        </form.Field>

                        {!hasBudgetField ? (
                          <form.Field name="budget">
                            {(field) => (
                              <label className="commercial-field">
                                <span>Budget</span>
                                <input
                                  type="number"
                                  min="0"
                                  value={field.state.value}
                                  onChange={(event) =>
                                    field.handleChange(nonNegativeNumber(event.target.value))
                                  }
                                />
                              </label>
                            )}
                          </form.Field>
                        ) : null}

                        <form.Field name="estimatedValue">
                          {(field) => (
                            <label className="commercial-field commercial-field--full">
                              <span>Estimated value</span>
                              <div className="commercial-estimate-row">
                                <input
                                  type="number"
                                  min="0"
                                  value={field.state.value}
                                  onChange={(event) =>
                                    field.handleChange(nonNegativeNumber(event.target.value))
                                  }
                                />
                                <Button
                                  type="button"
                                  size="sm"
                                  variant="outline"
                                  className="commercial-estimate-button"
                                  onClick={calculateEstimate}
                                  disabled={pricingConfigQuery.isPending}
                                >
                                  <IconCalculator size={14} />
                                  {pricingConfigQuery.isPending
                                    ? 'Loading pricing...'
                                    : 'Calculate estimate'}
                                </Button>
                              </div>
                              {estimatePreview?.supported ? (
                                <small>
                                  Current calculator result: {formatCurrency(estimatePreview.total)}
                                </small>
                              ) : activePricingConfig ? (
                                <small>
                                  Use the button when the pricing inputs for this service are
                                  filled.
                                </small>
                              ) : null}
                            </label>
                          )}
                        </form.Field>

                        {!hasPreferredDateField ? (
                          <form.Field name="preferredDate">
                            {(field) => (
                              <label className="commercial-field">
                                <span>Preferred date</span>
                                <input
                                  type="date"
                                  value={field.state.value}
                                  onChange={(event) => field.handleChange(event.target.value)}
                                />
                              </label>
                            )}
                          </form.Field>
                        ) : null}

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

                        {!hasScopeSummaryField ? (
                          <form.Field name="scopeSummary">
                            {(field) => (
                              <label className="commercial-field commercial-field--full">
                                <span>Scope summary</span>
                                <textarea
                                  rows={4}
                                  value={field.state.value}
                                  onChange={(event) => field.handleChange(event.target.value)}
                                />
                              </label>
                            )}
                          </form.Field>
                        ) : null}

                        <form.Field name="nextAction">
                          {(field) => (
                            <label className="commercial-field commercial-field--full">
                              <span>Next action</span>
                              <input
                                value={field.state.value}
                                onChange={(event) => field.handleChange(event.target.value)}
                              />
                            </label>
                          )}
                        </form.Field>
                      </div>
                    ) : null}
                  </section>

                  {hasUploadingFiles ? (
                    <div className="commercial-form-alert">
                      <IconLoader2 size={16} className="commercial-spin" />
                      <span>
                        Document uploads are still in progress. Submit will unlock when they finish.
                      </span>
                    </div>
                  ) : null}

                  {hasUploadErrors ? (
                    <div className="commercial-form-alert commercial-form-alert-danger">
                      <IconAlertCircle size={16} />
                      <span>
                        One or more documents failed to upload. Remove or upload them again before
                        submitting.
                      </span>
                    </div>
                  ) : null}
                </>
              )}
            </>
          )}
        </div>

        <footer className="commercial-modal-footer">
          <button type="button" className="commercial-btn" onClick={onClose} disabled={saving}>
            Cancel
          </button>
          <button
            type="submit"
            className="commercial-btn commercial-btn-primary"
            disabled={
              saving ||
              !ready ||
              !selectedService ||
              intakeQuery.isPending ||
              intakeQuery.isError ||
              hasUploadingFiles
            }
          >
            {saving ? 'Creating...' : 'Create Request'}
          </button>
        </footer>
      </form>
    </div>
  )
}
