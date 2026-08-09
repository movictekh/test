import {
  IconAlertCircle,
  IconCalculator,
  IconChevronDown,
  IconFile,
  IconFileDescription,
  IconFileTypeDoc,
  IconFileTypePdf,
  IconLoader2,
  IconPhoto,
  IconRefresh,
  IconTrash,
  IconUpload,
  IconX,
} from '@tabler/icons-react'
import { useForm } from '@tanstack/react-form'
import { useQuery } from '@tanstack/react-query'
import { useRef, useState } from 'react'

import { presentError } from '@/shared/errors'
import { formatCurrency } from '@/shared/lib/formatters'
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
  ServicePricingConfig,
  ServiceOption,
  ServiceRequestPriority,
  ServiceRequestChoices,
} from '../api/service-requests.types'

type UploadStatus = 'uploading' | 'uploaded' | 'error'

interface PendingUpload {
  id: string
  fieldKey: string
  label: string
  file: File
  fileName: string
  fileSizeBytes: number
  contentType: string
  fileUrl: string
  status: UploadStatus
  error: string
}

function missing(value: unknown) {
  return value == null || value === '' || (Array.isArray(value) && value.length === 0)
}

function normalizeToken(value: string) {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim()
}

function fieldToken(field: IntakeField) {
  return normalizeToken(`${field.key} ${field.label}`)
}

function isClientIdentityField(field: IntakeField) {
  const token = fieldToken(field)
  return token.includes('client identity') || token.includes('client name')
}

function isPhoneEmailField(field: IntakeField) {
  const token = fieldToken(field)
  return token.includes('phone') && token.includes('email')
}

function isPhoneField(field: IntakeField) {
  const token = fieldToken(field)
  return field.fieldType === 'phone' || (token.includes('phone') && !token.includes('email'))
}

function isEmailField(field: IntakeField) {
  const token = fieldToken(field)
  return field.fieldType === 'email' || token === 'email' || token.includes('contact email')
}

function isCustomerTypeField(field: IntakeField) {
  return fieldToken(field).includes('customer type')
}

function isBudgetField(field: IntakeField) {
  return fieldToken(field) === 'budget' || fieldToken(field).endsWith(' budget')
}

function isPreferredDateField(field: IntakeField) {
  return fieldToken(field).includes('preferred date')
}

function isScopeField(field: IntakeField) {
  const token = fieldToken(field)
  return (
    token.includes('scope message') ||
    token.includes('scope details') ||
    token.includes('scope summary') ||
    token.includes('scope') ||
    token.includes('request details') ||
    token.includes('message')
  )
}

function isAutoFilledField(field: IntakeField) {
  return (
    isClientIdentityField(field) ||
    isPhoneEmailField(field) ||
    isPhoneField(field) ||
    isEmailField(field) ||
    isCustomerTypeField(field) ||
    isBudgetField(field) ||
    isPreferredDateField(field)
  )
}

function formatBytes(size: number) {
  if (size < 1024) return `${size} B`
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`
  return `${(size / (1024 * 1024)).toFixed(1)} MB`
}

function fieldTextValue(value: unknown) {
  return typeof value === 'string' || typeof value === 'number' ? String(value) : ''
}

function isPriorityValue(value: string): value is ServiceRequestPriority {
  return value === 'normal' || value === 'high' || value === 'critical'
}

function fileIcon(upload: PendingUpload) {
  const name = upload.fileName.toLowerCase()
  const contentType = upload.contentType.toLowerCase()

  if (contentType.startsWith('image/') || /\.(png|jpg|jpeg|gif|webp|svg)$/.test(name)) {
    return <IconPhoto size={16} />
  }
  if (contentType.includes('pdf') || name.endsWith('.pdf')) {
    return <IconFileTypePdf size={16} />
  }
  if (contentType.includes('word') || /\.(doc|docx)$/.test(name)) {
    return <IconFileTypeDoc size={16} />
  }
  if (contentType.includes('text') || /\.(txt|csv|rtf)$/.test(name)) {
    return <IconFileDescription size={16} />
  }
  return <IconFile size={16} />
}

function resolveAutoAnswer(
  field: IntakeField,
  context: {
    contactName: string
    contactPhone: string
    contactEmail: string
    customerType: string
    budget: number
    preferredDate: string
    uploads: PendingUpload[]
  },
) {
  if (field.fieldType === 'file') {
    return context.uploads
      .filter((upload) => upload.fieldKey === field.key && upload.status === 'uploaded')
      .map((upload) => upload.fileUrl)
  }
  if (isClientIdentityField(field)) return context.contactName
  if (isPhoneEmailField(field)) {
    return [context.contactPhone, context.contactEmail].filter(Boolean).join(' · ')
  }
  if (isPhoneField(field)) return context.contactPhone
  if (isEmailField(field)) return context.contactEmail
  if (isCustomerTypeField(field)) return context.customerType
  if (isBudgetField(field)) return context.budget > 0 ? context.budget : ''
  if (isPreferredDateField(field)) return context.preferredDate
  return undefined
}

function shouldHideAutoField(
  field: IntakeField,
  context: Parameters<typeof resolveAutoAnswer>[1],
) {
  if (!isAutoFilledField(field)) return false
  const resolved = resolveAutoAnswer(field, context)
  if (field.required && missing(resolved)) return false
  return true
}

function nonNegativeNumber(value: string) {
  const parsed = Number(value)
  if (!Number.isFinite(parsed)) return 0
  return Math.max(0, parsed)
}

function toNumericValue(value: unknown) {
  if (typeof value === 'number' && Number.isFinite(value)) return value
  if (typeof value === 'string') {
    const cleaned = value.trim().replace(/,/g, '')
    if (cleaned === '') return null
    const parsed = Number(cleaned)
    return Number.isFinite(parsed) ? parsed : null
  }
  return null
}

function normalizeMatchToken(value: string) {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, '')
}

function resolvePricingValue(
  pricingField: ServicePricingConfig['fields'][number],
  intakeFields: IntakeField[],
  answers: Record<string, unknown>,
  topLevel: {
    budget: number
    preferredDate: string
    contactName: string
    contactPhone: string
    contactEmail: string
    customerType: string
    uploads: PendingUpload[]
  },
) {
  const direct = toNumericValue(answers[pricingField.key])
  if (direct != null) return direct

  const pricingTokens = new Set([
    normalizeMatchToken(pricingField.key),
    normalizeMatchToken(pricingField.label),
  ])

  for (const field of intakeFields) {
    const intakeTokens = [normalizeMatchToken(field.key), normalizeMatchToken(field.label)]
    if (!intakeTokens.some((token) => token && pricingTokens.has(token))) continue
    const resolved = shouldHideAutoField(field, topLevel)
      ? resolveAutoAnswer(field, topLevel)
      : answers[field.key]
    const numeric = toNumericValue(resolved)
    if (numeric != null) return numeric
  }

  return toNumericValue(pricingField.defaultValue)
}

function conventionalEstimate(
  pricingConfig: ServicePricingConfig,
  variables: Record<string, number>,
) {
  const findValue = (...keys: string[]) => {
    for (const key of keys) {
      const value = variables[key]
      if (Number.isFinite(value)) return value
    }
    return null
  }

  if (pricingConfig.pricingType === 'fixed') {
    const fixed =
      findValue('amount', 'fixed_price', 'fixedprice', 'price', 'rate') ??
      Object.values(variables)[0] ??
      null
    return fixed
  }

  if (pricingConfig.pricingType === 'percentage') {
    const baseAmount = findValue('base_amount', 'baseamount', 'amount', 'budget')
    const rate = findValue('rate', 'percentage', 'percent')
    return baseAmount != null && rate != null ? (baseAmount * rate) / 100 : null
  }

  if (pricingConfig.pricingType === 'unit_rate') {
    const quantity = findValue('quantity', 'units', 'count')
    const rate = findValue('rate', 'unit_rate', 'unitrate', 'price')
    return quantity != null && rate != null ? quantity * rate : null
  }

  if (pricingConfig.pricingType === 'area_rate') {
    const area = findValue('area', 'size', 'plot_size', 'plotsize', 'quantity')
    const rate = findValue('rate', 'area_rate', 'arearate', 'price')
    return area != null && rate != null ? area * rate : null
  }

  return null
}

function pricingNeedsFormula(pricingConfig: ServicePricingConfig) {
  return pricingConfig.pricingType === 'formula' || pricingConfig.formula.trim().length > 0
}

function calculateEstimateTotal(
  pricingConfig: ServicePricingConfig,
  intakeFields: IntakeField[],
  answers: Record<string, unknown>,
  topLevel: Parameters<typeof resolvePricingValue>[3],
) {
  const numericVariables: Record<string, number> = {}

  for (const field of pricingConfig.fields) {
    const value = resolvePricingValue(field, intakeFields, answers, topLevel)
    if (value == null) {
      if (field.required) {
        return { supported: false as const, reason: `Missing ${field.label.toLowerCase()}.` }
      }
      continue
    }
    numericVariables[field.key] = value
  }

  if (pricingNeedsFormula(pricingConfig)) {
    return {
      supported: false as const,
      reason: 'This service uses an advanced calculator formula that cannot be resolved safely here yet.',
    }
  }

  const subtotal = conventionalEstimate(pricingConfig, numericVariables)

  if (subtotal == null || !Number.isFinite(subtotal)) {
    return {
      supported: false as const,
      reason: 'This calculator needs pricing rules that are not available in this request form.',
    }
  }

  const total = subtotal + subtotal * (pricingConfig.taxRate / 100)
  return {
    supported: true as const,
    total: Math.max(0, Number(total.toFixed(2))),
    subtotal: Math.max(0, Number(subtotal.toFixed(2))),
  }
}

function validateAnswers(fields: IntakeField[], answers: Record<string, unknown>) {
  for (const field of fields) {
    const value = answers[field.key]
    if (field.required && missing(value)) return `${field.label} is required.`
    if (missing(value)) continue

    if (
      (field.fieldType === 'number' || field.fieldType === 'money') &&
      !Number.isFinite(Number(value))
    ) {
      return `${field.label} must be numeric.`
    }
  }
  return null
}

function validateAnswerFields(fields: IntakeField[], answers: Record<string, unknown>) {
  const errors: Record<string, string> = {}

  for (const field of fields) {
    const value = answers[field.key]
    if (field.required && missing(value)) {
      errors[field.key] = `${field.label} is required.`
      continue
    }
    if (missing(value)) continue

    if (
      (field.fieldType === 'number' || field.fieldType === 'money') &&
      !Number.isFinite(Number(value))
    ) {
      errors[field.key] = `${field.label} must be numeric.`
    }
  }

  return errors
}

function normalizeAnswers(fields: IntakeField[], answers: Record<string, unknown>) {
  return Object.fromEntries(
    fields.map((field) => {
      const value = answers[field.key]

      if (field.fieldType === 'number' || field.fieldType === 'money') {
        return [field.key, missing(value) ? null : Number(value)]
      }
      if (field.fieldType === 'checkbox') {
        return [field.key, Boolean(value)]
      }
      if (field.fieldType === 'multiselect') {
        return [field.key, Array.isArray(value) ? value : []]
      }
      if (field.fieldType === 'file') {
        return [field.key, Array.isArray(value) ? value : missing(value) ? [] : [value]]
      }

      return [field.key, value]
    }),
  )
}

function firstScopeValue(fields: IntakeField[], answers: Record<string, unknown>) {
  const match = fields.find(isScopeField)
  const value = match ? answers[match.key] : null
  return typeof value === 'string' ? value.trim() : ''
}

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
  const initialService = services[0] ?? null
  const initialClient = activeClients[0] ?? null
  const [serviceId, setServiceId] = useState(initialService?.id ?? 0)
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
      priority: (choices.priorities[0]?.value ?? 'normal') as ServiceRequestPriority,
      subserviceId: 0,
      branchId: initialService?.activeBranches[0]?.id ?? 0,
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
            ...(value.budget > 0 ? { budget: value.budget } : {}),
            estimatedValue: Number(value.estimatedValue || value.budget || 0),
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

  const ready = activeClients.length > 0 && services.length > 0
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

    const result = calculateEstimateTotal(activePricingConfig, fields, answerValues, autoAnswerContext)
    if (!result.supported) {
      toast.error('Estimate cannot be calculated yet.', {
        description: result.reason,
      })
      return
    }

    form.setFieldValue('estimatedValue', result.total)
    toast.success(`Estimate calculated: ${formatCurrency(result.total)}`)
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
                  : 'No active client-facing services are currently available for requests.'
              }
            />
          ) : intakeQuery.isPending ? (
            <div className="commercial-empty">Loading request form...</div>
          ) : intakeQuery.isError ? (
            <EmptyState
              title="Request form unavailable"
              description="The selected service is not ready for request intake yet. Publish its request form and try again."
              action={
                <Button variant="outline" size="sm" onClick={() => void intakeQuery.refetch()}>
                  Retry
                </Button>
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

              <section className="commercial-form-section">
                <div className="commercial-form-section-heading">
                  <div>
                    <h3>{intakeQuery.data?.form.name ?? 'Request details'}</h3>
                    <p>These questions are specific to this service and become part of the request record.</p>
                  </div>
                </div>
                <div className="commercial-form-grid">
                  <>
                    {visibleFields.map((field) => {
                      const value = answerValues[field.key]
                      const setValue = (next: unknown) => {
                        const nextAnswers = {
                          ...answerValues,
                          [field.key]: next,
                        }
                        setAnswerValues(nextAnswers)
                        form.setFieldValue('answers', {
                          ...nextAnswers,
                        })
                        setFieldErrors((current) => {
                          if (!current[field.key]) return current
                          const nextErrors = { ...current }
                          delete nextErrors[field.key]
                          return nextErrors
                        })
                      }

                      if (field.fieldType === 'textarea') {
                        return (
                          <label
                            key={field.id}
                            className="commercial-field commercial-field--full"
                          >
                            <span>
                              {field.label}
                              {field.required ? ' *' : ''}
                            </span>
                            <textarea
                              ref={(node) => {
                                fieldRefs.current[field.key] = node
                              }}
                              rows={4}
                              placeholder={field.placeholder}
                              value={fieldTextValue(value)}
                              onChange={(event) => setValue(event.target.value)}
                            />
                            {fieldErrors[field.key] ? (
                              <small className="commercial-field-error">{fieldErrors[field.key]}</small>
                            ) : null}
                          </label>
                        )
                      }

                      if (field.fieldType === 'select') {
                        return (
                          <label key={field.id} className="commercial-field">
                            <span>
                              {field.label}
                              {field.required ? ' *' : ''}
                            </span>
                            <select
                              ref={(node) => {
                                fieldRefs.current[field.key] = node
                              }}
                              value={fieldTextValue(value)}
                              onChange={(event) => setValue(event.target.value)}
                            >
                              <option value="">Select</option>
                              {field.options.map((option) => (
                                <option key={option.value} value={option.value}>
                                  {option.label}
                                </option>
                              ))}
                            </select>
                            {fieldErrors[field.key] ? (
                              <small className="commercial-field-error">{fieldErrors[field.key]}</small>
                            ) : null}
                          </label>
                        )
                      }

                      if (field.fieldType === 'multiselect') {
                        const selected = Array.isArray(value) ? value.map(String) : []
                        return (
                          <label key={field.id} className="commercial-field">
                            <span>
                              {field.label}
                              {field.required ? ' *' : ''}
                            </span>
                            <select
                              ref={(node) => {
                                fieldRefs.current[field.key] = node
                              }}
                              multiple
                              value={selected}
                              onChange={(event) =>
                                setValue(
                                  Array.from(event.target.selectedOptions).map(
                                    (option) => option.value,
                                  ),
                                )
                              }
                            >
                              {field.options.map((option) => (
                                <option key={option.value} value={option.value}>
                                  {option.label}
                                </option>
                              ))}
                            </select>
                            {fieldErrors[field.key] ? (
                              <small className="commercial-field-error">{fieldErrors[field.key]}</small>
                            ) : null}
                          </label>
                        )
                      }

                      if (field.fieldType === 'checkbox') {
                        return (
                          <label
                            key={field.id}
                            className="commercial-check commercial-field--full"
                            ref={(node) => {
                              fieldRefs.current[field.key] = node
                            }}
                          >
                            <input
                              type="checkbox"
                              checked={Boolean(value)}
                              onChange={(event) => setValue(event.target.checked)}
                            />
                            <span>
                              {field.label}
                              {field.required ? ' *' : ''}
                            </span>
                            {fieldErrors[field.key] ? (
                              <small className="commercial-field-error">{fieldErrors[field.key]}</small>
                            ) : null}
                          </label>
                        )
                      }

                      if (field.fieldType === 'file') {
                        const uploads = uploadsByField[field.key] ?? []
                        return (
                          <div
                            key={field.id}
                            className="commercial-field commercial-field--full commercial-upload-field"
                            ref={(node) => {
                              fieldRefs.current[field.key] = node
                            }}
                          >
                            <span>
                              {field.label}
                              {field.required ? ' *' : ''}
                            </span>
                            <label className="commercial-upload-dropzone">
                              <div className="commercial-upload-dropzone-icon">
                                <IconUpload size={18} />
                              </div>
                              <div>
                                <strong>Add documents</strong>
                                <small>
                                  Upload one or more files now. They will be attached when the request is created.
                                </small>
                              </div>
                              <input
                                type="file"
                                multiple
                                onChange={(event) => {
                                  void handleFileSelection(field, event.target.files)
                                  event.target.value = ''
                                }}
                              />
                            </label>
                            {uploads.length > 0 ? (
                              <div className="commercial-upload-list">
                                {uploads.map((upload) => (
                                  <article
                                    key={upload.id}
                                    className={`commercial-upload-item commercial-upload-item--${upload.status}`}
                                  >
                                    <div className="commercial-upload-item-icon">
                                      {fileIcon(upload)}
                                    </div>
                                    <div className="commercial-upload-item-body">
                                      <div className="commercial-upload-item-top">
                                        <strong>{upload.fileName}</strong>
                                        <span>{formatBytes(upload.fileSizeBytes)}</span>
                                      </div>
                                      {upload.status === 'uploading' ? (
                                        <div className="commercial-upload-progress">
                                          <div className="commercial-upload-progress-bar" />
                                        </div>
                                      ) : null}
                                      {upload.status === 'uploaded' ? (
                                        <small>Ready to attach to this request</small>
                                      ) : null}
                                      {upload.status === 'error' ? <small>{upload.error}</small> : null}
                                    </div>
                                    <div className="commercial-upload-actions">
                                      {upload.status === 'error' ? (
                                        <button
                                          type="button"
                                          className="commercial-upload-remove"
                                          onClick={() => retryUpload(upload)}
                                          aria-label={`Retry ${upload.fileName}`}
                                        >
                                          <IconRefresh size={14} />
                                        </button>
                                      ) : null}
                                      <button
                                        type="button"
                                        className="commercial-upload-remove"
                                        onClick={() => removeUpload(field.key, upload.id)}
                                        aria-label={`Remove ${upload.fileName}`}
                                      >
                                        {upload.status === 'uploading' ? (
                                          <IconX size={14} />
                                        ) : (
                                          <IconTrash size={14} />
                                        )}
                                      </button>
                                    </div>
                                  </article>
                                ))}
                              </div>
                            ) : null}
                            {fieldErrors[field.key] ? (
                              <small className="commercial-field-error">{fieldErrors[field.key]}</small>
                            ) : null}
                          </div>
                        )
                      }

                      return (
                        <label key={field.id} className="commercial-field">
                          <span>
                            {field.label}
                            {field.required ? ' *' : ''}
                          </span>
                          <input
                            ref={(node) => {
                              fieldRefs.current[field.key] = node
                            }}
                            type={
                              field.fieldType === 'date'
                                ? 'date'
                                : field.fieldType === 'number' || field.fieldType === 'money'
                                  ? 'number'
                                  : field.fieldType === 'email'
                                    ? 'email'
                                    : 'text'
                            }
                            placeholder={field.placeholder}
                            value={fieldTextValue(value)}
                            onChange={(event) =>
                              setValue(
                                field.fieldType === 'number' || field.fieldType === 'money'
                                  ? nonNegativeNumber(event.target.value)
                                  : event.target.value,
                              )
                            }
                          />
                          {fieldErrors[field.key] ? (
                            <small className="commercial-field-error">{fieldErrors[field.key]}</small>
                          ) : null}
                          {field.helpText ? <small>{field.helpText}</small> : null}
                        </label>
                      )
                    })}
                  </>
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
                              {pricingConfigQuery.isPending ? 'Loading pricing...' : 'Calculate estimate'}
                            </Button>
                          </div>
                          {estimatePreview?.supported ? (
                            <small>
                              Current calculator result: {formatCurrency(estimatePreview.total)}
                            </small>
                          ) : activePricingConfig ? (
                            <small>
                              Use the button when the pricing inputs for this service are filled.
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
                  <span>Document uploads are still in progress. Submit will unlock when they finish.</span>
                </div>
              ) : null}

              {hasUploadErrors ? (
                <div className="commercial-form-alert commercial-form-alert-danger">
                  <IconAlertCircle size={16} />
                  <span>One or more documents failed to upload. Remove or upload them again before submitting.</span>
                </div>
              ) : null}
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
