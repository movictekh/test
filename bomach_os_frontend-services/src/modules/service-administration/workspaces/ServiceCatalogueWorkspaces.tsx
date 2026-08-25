import { IconPlus, IconTrash, IconX } from '@tabler/icons-react'
import { useRef, useState } from 'react'

import { formatNumberFieldValue, parseNumberFieldValue } from '@/shared/lib/number-input'

import type {
  ConfigureServiceInput,
  WorkflowOwnerRoleOption,
  ServiceSetupStageProgress,
  ServiceSetupStageId,
  CreateServiceStageAccess,
  CreateServiceWizardInput,
  PricingCalculator,
  ServiceCategoryOption,
  ServiceCatalogueItem,
  ServiceRequestForm,
  ServiceStatus,
  ServiceSubserviceSetup,
  ServiceWorkflow,
} from '../types/service-administration.types'

const divisions = [
  'Real Estate',
  'Land Surveying & Geospatial',
  'Engineering & Construction',
  'Courier & Logistics',
  'Information Technology',
  'Food & Farms',
  'Hospitality Services',
]

const requestFieldOptions = [
  'Client identity',
  'Phone & email',
  'Customer type',
  'Location / site',
  'Budget',
  'Preferred date',
  'Scope / message',
  'Document uploads',
  'Images / videos',
  'Title documents',
  'Consent',
  'Lead / campaign source',
]

const wizardSteps = ['Basic', 'Sub-services', 'Pricing', 'Request Form', 'Workflow', 'Publish']

function splitLines(value: string) {
  return value
    .split('\n')
    .map((item) => item.trim())
    .filter(Boolean)
}

type CreateSubserviceDraft = ServiceSubserviceSetup & {
  localId: string
}

type ServiceWizardFieldName =
  | 'name'
  | 'code'
  | 'categoryId'
  | 'division'
  | 'ownerRoleId'
  | 'description'
  | 'slaDays'
  | 'fulfilmentMode'
  | 'subservices'
  | 'pricingMethod'
  | 'rate'
  | 'depositPercent'
  | 'taxPercent'
  | 'discountApprovalPercent'
  | 'requestFields'
  | 'workflow'
  | 'branches'
  | 'status'
  | 'clientVisibility'

type ServiceWizardFieldErrors = Partial<Record<ServiceWizardFieldName, string>>

type SubserviceEditorFieldName = 'name' | 'code' | 'status' | 'defaultSlaDays' | 'description'

type SubserviceEditorFieldErrors = Partial<Record<SubserviceEditorFieldName, string>>

let subserviceDraftSequence = 0

function nextSubserviceDraftId() {
  subserviceDraftSequence += 1
  return `subservice-draft-${subserviceDraftSequence}`
}

function slugifySubservice(value: string) {
  return value
    .trim()
    .toLowerCase()
    .replace(/&/g, ' and ')
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
}

function createSubserviceDraft(
  defaultSlaDays: number,
  overrides: Partial<ServiceSubserviceSetup> = {},
): CreateSubserviceDraft {
  return {
    localId: nextSubserviceDraftId(),
    code: overrides.code ?? '',
    name: overrides.name ?? '',
    description: overrides.description ?? '',
    status: overrides.status ?? 'draft',
    defaultSlaDays: overrides.defaultSlaDays ?? defaultSlaDays,
  }
}

function buildInitialSubserviceDrafts(defaultSlaDays: number) {
  void defaultSlaDays
  return [] as CreateSubserviceDraft[]
}

function subserviceStatusForServiceStatus(status: ServiceStatus): CreateSubserviceDraft['status'] {
  if (status === 'active') return 'active'
  if (status === 'inactive') return 'inactive'
  return 'draft'
}

function buildSubserviceDraftsFromNames(
  names: string[],
  defaultSlaDays: number,
  status: ServiceStatus,
) {
  return names.map((name) =>
    createSubserviceDraft(defaultSlaDays, {
      name,
      status: subserviceStatusForServiceStatus(status),
    }),
  )
}

function validateSubserviceDrafts(subserviceDrafts: CreateSubserviceDraft[]): string | null {
  if (subserviceDrafts.length === 0) return 'Add at least one sub-service.'

  const effectiveCodes = new Set<string>()

  for (const [index, item] of subserviceDrafts.entries()) {
    if (!item.name.trim()) return `Sub-service ${index + 1} needs a name.`
    if (!Number.isFinite(item.defaultSlaDays) || item.defaultSlaDays < 1) {
      return `Sub-service ${index + 1} must have an SLA of at least 1 day.`
    }

    const effectiveCode = slugifySubservice(item.code?.trim() || item.name)
    if (!effectiveCode) return `Sub-service ${index + 1} needs a valid name or code.`
    if (effectiveCodes.has(effectiveCode)) {
      return 'Each sub-service must have a unique code or generated slug.'
    }

    effectiveCodes.add(effectiveCode)
  }

  return null
}

function serializeSubserviceDrafts(
  subserviceDrafts: CreateSubserviceDraft[],
): ServiceSubserviceSetup[] {
  return subserviceDrafts.map(({ code: draftCode, description: draftDescription, ...item }) => ({
    code: draftCode?.trim() ? draftCode.trim() : null,
    name: item.name.trim(),
    description: draftDescription.trim(),
    status: item.status,
    defaultSlaDays: item.defaultSlaDays,
  }))
}

function focusField(
  fieldRefs: React.MutableRefObject<Record<string, HTMLElement | null>>,
  fieldName: string,
) {
  window.requestAnimationFrame(() => {
    const node = fieldRefs.current[fieldName]
    node?.scrollIntoView({ behavior: 'smooth', block: 'center' })
    if (
      node instanceof HTMLInputElement ||
      node instanceof HTMLTextAreaElement ||
      node instanceof HTMLSelectElement ||
      node instanceof HTMLButtonElement
    ) {
      node.focus()
    }
  })
}

function focusNotice(ref: React.RefObject<HTMLElement | null>) {
  window.requestAnimationFrame(() => {
    ref.current?.scrollIntoView({ behavior: 'smooth', block: 'center' })
    ref.current?.focus()
  })
}

function validateSubserviceEditorDraft(draft: CreateSubserviceDraft): SubserviceEditorFieldErrors {
  const errors: SubserviceEditorFieldErrors = {}

  if (!draft.name.trim()) {
    errors.name = 'Sub-service name is required.'
  }
  if (!Number.isFinite(draft.defaultSlaDays) || draft.defaultSlaDays < 1) {
    errors.defaultSlaDays = 'Default SLA must be at least 1 day.'
  }
  if (!slugifySubservice(draft.code?.trim() || draft.name)) {
    errors.code = 'Enter a valid code or a name that can generate one.'
  }

  return errors
}

function ModalShell({
  title,
  wide = false,
  variant = 'default',
  children,
  footer,
  onClose,
}: {
  title: string
  wide?: boolean
  variant?: 'default' | 'wizard'
  children: React.ReactNode
  footer: React.ReactNode
  onClose: () => void
}) {
  return (
    <div className="service-admin-modal-backdrop" role="presentation" onMouseDown={onClose}>
      <section
        role="dialog"
        aria-modal="true"
        aria-label={title}
        className={[
          'service-admin-modal',
          wide ? 'service-admin-modal--wide' : '',
          variant === 'wizard' ? 'service-admin-modal--wizard' : '',
        ]
          .filter(Boolean)
          .join(' ')}
        onMouseDown={(event) => event.stopPropagation()}
      >
        <header className="service-admin-modal-header">
          <h2 className="service-admin-modal-title">{title}</h2>
          <button
            type="button"
            className="service-admin-modal-close"
            aria-label="Close"
            onClick={onClose}
          >
            <IconX size={16} />
          </button>
        </header>
        <div className="service-admin-modal-body">{children}</div>
        <footer className="service-admin-modal-footer">{footer}</footer>
      </section>
    </div>
  )
}

function Field({
  label,
  children,
  full = false,
  required = false,
  error,
}: {
  label: string
  children: React.ReactNode
  full?: boolean
  required?: boolean
  error?: string | undefined
}) {
  return (
    <label
      className={`service-admin-config-field${full ? 'service-admin-config-field--full' : ''}`}
    >
      <span>
        {label}
        {required ? <em className="service-admin-required">*</em> : null}
      </span>
      {children}
      {error ? <small className="service-admin-field-error">{error}</small> : null}
    </label>
  )
}

function SubserviceEditorModal({
  draft,
  pending,
  title,
  onClose,
  onSave,
}: {
  draft: CreateSubserviceDraft
  pending: boolean
  title: string
  onClose: () => void
  onSave: (draft: CreateSubserviceDraft) => void
}) {
  const [localDraft, setLocalDraft] = useState<CreateSubserviceDraft>(draft)
  const [error, setError] = useState('')
  const [fieldErrors, setFieldErrors] = useState<SubserviceEditorFieldErrors>({})
  const fieldRefs = useRef<Record<string, HTMLElement | null>>({})
  const errorNoticeRef = useRef<HTMLDivElement | null>(null)

  const save = () => {
    const nextErrors = validateSubserviceEditorDraft(localDraft)
    setFieldErrors(nextErrors)

    const firstField = (
      ['name', 'code', 'status', 'defaultSlaDays', 'description'] as SubserviceEditorFieldName[]
    ).find((field) => nextErrors[field])

    if (firstField) {
      setError(nextErrors[firstField] ?? '')
      focusField(fieldRefs, firstField)
      return
    }

    setError('')
    setFieldErrors({})
    onSave({
      ...localDraft,
      name: localDraft.name.trim(),
      code: localDraft.code?.trim() ?? '',
      description: localDraft.description.trim(),
    })
  }

  return (
    <div
      className="service-admin-modal-backdrop service-admin-modal-backdrop--nested"
      role="presentation"
      onMouseDown={onClose}
    >
      <section
        role="dialog"
        aria-modal="true"
        aria-label={title}
        className="service-admin-modal service-admin-modal--nested"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <header className="service-admin-modal-header">
          <h2 className="service-admin-modal-title">{title}</h2>
          <button
            type="button"
            className="service-admin-modal-close"
            aria-label="Close"
            onClick={onClose}
          >
            <IconX size={16} />
          </button>
        </header>
        <div className="service-admin-modal-body">
          {error ? (
            <div
              ref={errorNoticeRef}
              tabIndex={-1}
              className="service-admin-notice service-admin-notice-red"
            >
              {error}
            </div>
          ) : null}
          <div className="service-admin-form-grid">
            <Field label="Sub-service name" required error={fieldErrors.name}>
              <input
                ref={(node) => {
                  fieldRefs.current.name = node
                }}
                aria-invalid={fieldErrors.name ? true : undefined}
                value={localDraft.name}
                placeholder="e.g. Priority Site Assessment"
                onChange={(event) =>
                  setLocalDraft((current) => ({
                    ...current,
                    name: event.target.value,
                  }))
                }
              />
            </Field>
            <Field label="Code" error={fieldErrors.code}>
              <input
                ref={(node) => {
                  fieldRefs.current.code = node
                }}
                aria-invalid={fieldErrors.code ? true : undefined}
                value={localDraft.code ?? ''}
                placeholder="Optional custom code"
                onChange={(event) =>
                  setLocalDraft((current) => ({
                    ...current,
                    code: event.target.value,
                  }))
                }
              />
            </Field>
            <Field label="Status" required error={fieldErrors.status}>
              <select
                ref={(node) => {
                  fieldRefs.current.status = node
                }}
                aria-invalid={fieldErrors.status ? true : undefined}
                value={localDraft.status}
                onChange={(event) =>
                  setLocalDraft((current) => ({
                    ...current,
                    status: event.target.value as CreateSubserviceDraft['status'],
                  }))
                }
              >
                <option value="draft">Draft</option>
                <option value="active">Active</option>
                <option value="inactive">Inactive</option>
              </select>
            </Field>
            <Field label="Default SLA (days)" required error={fieldErrors.defaultSlaDays}>
              <input
                ref={(node) => {
                  fieldRefs.current.defaultSlaDays = node
                }}
                aria-invalid={fieldErrors.defaultSlaDays ? true : undefined}
                type="number"
                min={1}
                value={formatNumberFieldValue(localDraft.defaultSlaDays)}
                onChange={(event) =>
                  setLocalDraft((current) => ({
                    ...current,
                    defaultSlaDays: parseNumberFieldValue(event.target.value),
                  }))
                }
              />
            </Field>
          </div>
          <Field label="Description" full error={fieldErrors.description}>
            <textarea
              ref={(node) => {
                fieldRefs.current.description = node
              }}
              aria-invalid={fieldErrors.description ? true : undefined}
              className="service-admin-wizard-textarea"
              rows={4}
              value={localDraft.description}
              placeholder="Optional scope, packaging notes, or client-facing explanation."
              onChange={(event) =>
                setLocalDraft((current) => ({
                  ...current,
                  description: event.target.value,
                }))
              }
            />
          </Field>
        </div>
        <footer className="service-admin-modal-footer">
          <button
            type="button"
            className="service-admin-button"
            disabled={pending}
            onClick={onClose}
          >
            Cancel
          </button>
          <button
            type="button"
            className="service-admin-button service-admin-button-primary"
            disabled={pending}
            onClick={save}
          >
            Save Sub-service
          </button>
        </footer>
      </section>
    </div>
  )
}

function SubserviceStagePanel({
  drafts,
  pending,
  error,
  addButtonRef,
  onAdd,
  onEdit,
  onRemove,
}: {
  drafts: CreateSubserviceDraft[]
  pending: boolean
  error?: string | undefined
  addButtonRef?: React.Ref<HTMLButtonElement>
  onAdd: () => void
  onEdit: (localId: string) => void
  onRemove: (localId: string) => void
}) {
  return (
    <div className="service-admin-subservice-stack">
      <div className="service-admin-card">
        <div className="service-admin-card-header">
          <div>
            <div className="service-admin-card-title">Sub-services</div>
            <div className="service-admin-card-subtitle">
              Define the service variants that should be available for setup, pricing, and request
              intake.
            </div>
          </div>
          <button
            type="button"
            ref={addButtonRef}
            className="service-admin-button service-admin-button-primary"
            disabled={pending}
            onClick={onAdd}
          >
            <IconPlus size={14} />
            Add Sub-service
          </button>
        </div>

        {drafts.length === 0 ? (
          <div className="service-admin-notice service-admin-notice-blue">
            No sub-services added yet.
          </div>
        ) : (
          <div className="service-admin-subservice-list">
            {drafts.map((item, index) => {
              const effectiveCode = item.code?.trim() || slugifySubservice(item.name)

              return (
                <article key={item.localId} className="service-admin-subservice-card">
                  <div className="service-admin-subservice-card-meta">
                    <div className="service-admin-subservice-card-name">
                      {item.name.trim() || `Sub-service ${index + 1}`}
                    </div>
                    <div className="service-admin-subservice-card-subtitle">
                      {effectiveCode || 'Code will be generated from the name'} ·{' '}
                      {item.defaultSlaDays} day SLA · {item.status}
                    </div>
                    {item.description.trim() ? (
                      <div className="service-admin-subservice-card-description">
                        {item.description.trim()}
                      </div>
                    ) : null}
                  </div>
                  <div className="service-admin-subservice-card-actions">
                    <button
                      type="button"
                      className="service-admin-button"
                      disabled={pending}
                      onClick={() => onEdit(item.localId)}
                    >
                      Edit
                    </button>
                    <button
                      type="button"
                      className="service-admin-button"
                      disabled={pending}
                      onClick={() => onRemove(item.localId)}
                    >
                      <IconTrash size={14} />
                      Remove
                    </button>
                  </div>
                </article>
              )
            })}
          </div>
        )}
        {error ? <small className="service-admin-field-error">{error}</small> : null}
      </div>
    </div>
  )
}

/** Backend stores category slugs; show human labels in the wizard. */
const SERVICE_CATEGORY_LABELS: Record<string, string> = {
  surveying: 'Surveying',
  construction: 'Construction',
  it: 'Information Technology (IT)',
  civil_engineering: 'Civil Engineering',
  mechanical_engineering: 'Mechanical Engineering',
  electrical_engineering: 'Electrical Engineering',
  environmental_engineering: 'Environmental Engineering',
  project_management: 'Project Management',
  property_sale_rent: 'Property Sale/Rent',
  maintenance: 'Maintenance & Technical Support',
  others: 'Others',
}

function categoryLabel(name: string) {
  return SERVICE_CATEGORY_LABELS[name] ?? name
}

export function CreateServiceWizard({
  open,
  pending,
  categories,
  branches: branchOptions = [],
  ownerRoles = [],
  stageAccess,
  progress = [],
  setupServiceId = null,
  onClose,
  onSubmit,
  onRetryFailed,
}: {
  open: boolean
  pending: boolean
  categories: ServiceCategoryOption[]
  branches?: Array<{ id: number; name: string; code: string }>
  ownerRoles?: WorkflowOwnerRoleOption[]
  stageAccess?: CreateServiceStageAccess
  progress?: ServiceSetupStageProgress[]
  setupServiceId?: number | null
  onClose: () => void
  onSubmit: (input: CreateServiceWizardInput) => void
  onRetryFailed?: () => void
}) {
  const access: CreateServiceStageAccess = stageAccess ?? {
    subservices: true,
    pricing: true,
    requestForm: true,
    workflow: true,
    branches: true,
    publish: true,
    ownerRoles: true,
  }

  const [step, setStep] = useState(0)
  const [maxReachedStep, setMaxReachedStep] = useState(0)
  const [name, setName] = useState('')
  const [code, setCode] = useState('')
  const [categoryId, setCategoryId] = useState<number>(0)
  const [division, setDivision] = useState(divisions[0] ?? '')
  const [ownerRoleId, setOwnerRoleId] = useState<number | null>(null)
  const [description, setDescription] = useState('')
  const [slaDays, setSlaDays] = useState(5)
  const [fulfilmentMode, setFulfilmentMode] = useState('Quick service order')
  const [subserviceDrafts, setSubserviceDrafts] = useState<CreateSubserviceDraft[]>(() =>
    buildInitialSubserviceDrafts(5),
  )
  const [subserviceEditorDraft, setSubserviceEditorDraft] = useState<CreateSubserviceDraft | null>(
    null,
  )
  const [editingSubserviceId, setEditingSubserviceId] = useState<string | null>(null)
  const [pricingMethod, setPricingMethod] = useState('Fixed')
  const [rate, setRate] = useState(100000)
  const [depositPercent, setDepositPercent] = useState(70)
  const [taxPercent, setTaxPercent] = useState(0)
  const [discountApprovalPercent, setDiscountApprovalPercent] = useState(5)
  const [requestFields, setRequestFields] = useState<string[]>([
    'Client identity',
    'Phone & email',
    'Customer type',
    'Location / site',
    'Budget',
    'Preferred date',
    'Scope / message',
    'Document uploads',
  ])
  const [workflow, setWorkflow] = useState(
    'Request Review\nTechnical Assessment\nQuotation\nApproval\nInvoice & Payment\nService Order\nExecution\nQuality Review\nClient Acceptance\nCompletion & Feedback',
  )
  const [selectedBranchIds, setSelectedBranchIds] = useState<number[] | null>(null)
  const [status, setStatus] = useState<'active' | 'draft' | 'inactive'>('draft')
  const [clientVisibility, setClientVisibility] = useState<'visible' | 'internal' | 'hidden'>(
    'visible',
  )
  const [error, setError] = useState('')
  const [fieldErrors, setFieldErrors] = useState<ServiceWizardFieldErrors>({})
  const fieldRefs = useRef<Record<string, HTMLElement | null>>({})
  const errorNoticeRef = useRef<HTMLDivElement | null>(null)

  if (!open) return null

  type WizardStage =
    'basic' | 'subservices' | 'pricing' | 'request-form' | 'workflow' | 'branches' | 'review'
  const steps: Array<{ id: WizardStage; label: string }> = [
    { id: 'basic', label: 'Basic' },
    ...(access.subservices ? [{ id: 'subservices' as const, label: 'Sub-services' }] : []),
    ...(access.pricing ? [{ id: 'pricing' as const, label: 'Pricing' }] : []),
    ...(access.requestForm ? [{ id: 'request-form' as const, label: 'Request Form' }] : []),
    ...(access.workflow ? [{ id: 'workflow' as const, label: 'Workflow' }] : []),
    ...(access.branches ? [{ id: 'branches' as const, label: 'Branches' }] : []),
    { id: 'review', label: access.publish ? 'Review & Publish' : 'Review' },
  ]
  const currentStage = steps[Math.min(step, steps.length - 1)]?.id ?? 'basic'
  const effectiveSelectedBranchIds = selectedBranchIds ?? branchOptions.map((branch) => branch.id)
  const canPublishActive =
    access.publish &&
    access.pricing &&
    access.requestForm &&
    access.branches &&
    effectiveSelectedBranchIds.length > 0

  const clearFieldError = (field: ServiceWizardFieldName) => {
    setFieldErrors((current) => {
      if (!current[field]) return current
      const next = { ...current }
      delete next[field]
      return next
    })
  }

  const failValidation = (message: string, field?: ServiceWizardFieldName) => {
    setError(message)
    setFieldErrors(field ? { [field]: message } : {})
    if (field) {
      focusField(fieldRefs, field)
      return
    }
    focusNotice(errorNoticeRef)
  }

  const validateStage = (
    stage: WizardStage,
  ): { message: string; field?: ServiceWizardFieldName } | null => {
    if (stage === 'basic') {
      if (!name.trim()) return { message: 'Service name is required.', field: 'name' }
      if (!code.trim()) return { message: 'Service code is required.', field: 'code' }
      if (!categoryId) return { message: 'Service category is required.', field: 'categoryId' }
      if (!division.trim()) return { message: 'Division is required.', field: 'division' }
      if (!description.trim()) return { message: 'Description is required.', field: 'description' }
      if (!Number.isFinite(slaDays) || slaDays < 1) {
        return { message: 'SLA must be at least 1 day.', field: 'slaDays' }
      }
      if (!fulfilmentMode.trim()) {
        return { message: 'Fulfillment mode is required.', field: 'fulfilmentMode' }
      }
    }
    if (stage === 'subservices') {
      const subserviceError = validateSubserviceDrafts(subserviceDrafts)
      return subserviceError ? { message: subserviceError, field: 'subservices' } : null
    }
    if (stage === 'pricing') {
      if (!pricingMethod.trim()) {
        return { message: 'Pricing method is required.', field: 'pricingMethod' }
      }
      if (!Number.isFinite(rate) || rate < 0) {
        return { message: 'Base / unit price is required.', field: 'rate' }
      }
      if (!Number.isFinite(depositPercent) || depositPercent < 0 || depositPercent > 100) {
        return { message: 'Deposit (%) must be between 0 and 100.', field: 'depositPercent' }
      }
      if (!Number.isFinite(taxPercent) || taxPercent < 0 || taxPercent > 100) {
        return { message: 'Tax (%) must be between 0 and 100.', field: 'taxPercent' }
      }
      if (
        !Number.isFinite(discountApprovalPercent) ||
        discountApprovalPercent < 0 ||
        discountApprovalPercent > 100
      )
        return {
          message: 'Discount approval (%) must be between 0 and 100.',
          field: 'discountApprovalPercent',
        }
    }
    if (stage === 'request-form' && requestFields.length === 0) {
      return {
        message: 'Select at least one request form field.',
        field: 'requestFields',
      }
    }
    if (stage === 'workflow' && splitLines(workflow).length === 0) {
      return { message: 'Add at least one workflow stage.', field: 'workflow' }
    }
    if (stage === 'branches' && status === 'active' && effectiveSelectedBranchIds.length === 0) {
      return {
        message: 'Select at least one active branch before publishing.',
        field: 'branches',
      }
    }
    return null
  }

  const submit = () => {
    for (const stage of steps) {
      if (stage.id === 'review') continue
      const problem = validateStage(stage.id)
      if (problem) {
        setStep(steps.findIndex((item) => item.id === stage.id))
        failValidation(problem.message, problem.field)
        return
      }
    }

    const enabledStages: ServiceSetupStageId[] = [
      ...(access.subservices ? ['subservices' as const] : []),
      ...(access.pricing ? ['pricing' as const] : []),
      ...(access.requestForm ? ['request-form' as const] : []),
      ...(access.workflow ? ['workflow' as const] : []),
      ...(access.branches && effectiveSelectedBranchIds.length > 0 ? ['branches' as const] : []),
      ...(status !== 'draft' && access.publish ? ['publish' as const] : []),
    ]
    const selectedOwner = ownerRoles.find((role) => role.id === ownerRoleId)
    const selectedBranches = branchOptions.filter((branch) =>
      effectiveSelectedBranchIds.includes(branch.id),
    )

    setError('')
    setFieldErrors({})
    onSubmit({
      name: name.trim(),
      categoryId,
      code: code.trim(),
      division,
      description: description.trim(),
      owner: selectedOwner?.name ?? '',
      ownerRoleId,
      slaDays,
      fulfilmentMode,
      status,
      clientVisibility,
      branchNames: selectedBranches.map((branch) => branch.name),
      branchIds: effectiveSelectedBranchIds,
      subservices: serializeSubserviceDrafts(subserviceDrafts),
      pricing: { method: pricingMethod, rate, depositPercent, taxPercent, discountApprovalPercent },
      requestFields,
      workflowStages: splitLines(workflow),
      enabledStages,
    })
  }

  const addSubservice = () => {
    setEditingSubserviceId(null)
    setSubserviceEditorDraft(createSubserviceDraft(slaDays))
    setError('')
  }

  const editSubservice = (localId: string) => {
    const currentDraft = subserviceDrafts.find((item) => item.localId === localId)
    if (!currentDraft) return
    setEditingSubserviceId(localId)
    setSubserviceEditorDraft(currentDraft)
  }

  const removeSubservice = (localId: string) => {
    setSubserviceDrafts((current) => current.filter((item) => item.localId !== localId))
    if (editingSubserviceId === localId) {
      setEditingSubserviceId(null)
      setSubserviceEditorDraft(null)
    }
    setError('')
  }

  const saveSubserviceDraft = (draft: CreateSubserviceDraft) => {
    if (editingSubserviceId) {
      setSubserviceDrafts((current) =>
        current.map((item) => (item.localId === editingSubserviceId ? draft : item)),
      )
    } else {
      setSubserviceDrafts((current) => [...current, draft])
    }
    setEditingSubserviceId(null)
    setSubserviceEditorDraft(null)
    setError('')
  }

  const next = () => {
    const problem = validateStage(currentStage)
    if (problem) {
      failValidation(problem.message, problem.field)
      return
    }
    setError('')
    setFieldErrors({})
    if (currentStage === 'review') {
      submit()
      return
    }
    const following = Math.min(steps.length - 1, step + 1)
    setMaxReachedStep((current) => Math.max(current, following))
    setStep(following)
  }

  const retryable = progress.filter((item) => item.state === 'failed' || item.state === 'skipped')
  const successful = progress.filter((item) => item.state === 'success').length
  const progressPercent = progress.length ? Math.round((successful / progress.length) * 100) : 0
  const symbol = (state: ServiceSetupStageProgress['state']) => {
    if (state === 'success') return '✓'
    if (state === 'failed') return '✕'
    if (state === 'running') return '→'
    if (state === 'skipped') return '○'
    return '·'
  }

  return (
    <>
      <ModalShell
        title="Create & Activate Service"
        wide
        variant="wizard"
        onClose={onClose}
        footer={
          <>
            <button
              type="button"
              className="service-admin-button service-admin-wizard-nav-btn"
              disabled={step === 0 || pending || Boolean(setupServiceId)}
              onClick={() => setStep((current) => Math.max(0, current - 1))}
            >
              Previous
            </button>
            {setupServiceId ? (
              <button
                type="button"
                className="service-admin-button service-admin-wizard-nav-btn"
                disabled={pending}
                onClick={onClose}
              >
                Finish for now
              </button>
            ) : (
              <button
                type="button"
                className="service-admin-button service-admin-button-primary service-admin-wizard-nav-btn service-admin-wizard-nav-btn--primary"
                disabled={pending}
                onClick={next}
              >
                {pending ? 'Setting up…' : currentStage === 'review' ? 'Create Service' : 'Next'}
              </button>
            )}
          </>
        }
      >
        <div
          className="service-admin-wizard-steps"
          role="tablist"
          aria-label="Create service steps"
        >
          {steps.map((item, index) => {
            const reached = index <= maxReachedStep
            return (
              <button
                key={item.id}
                type="button"
                role="tab"
                aria-selected={index === step}
                aria-disabled={!reached}
                disabled={!reached || pending || Boolean(setupServiceId)}
                className={[
                  'service-admin-wizard-step',
                  index === step ? 'service-admin-wizard-step--active' : '',
                  index < step ? 'service-admin-wizard-step--complete' : '',
                  reached ? 'service-admin-wizard-step--reachable' : '',
                ]
                  .filter(Boolean)
                  .join(' ')}
                onClick={() => {
                  if (!reached) return
                  setError('')
                  setStep(index)
                }}
              >
                {index + 1}. {item.label}
              </button>
            )
          })}
        </div>

        {error ? (
          <div
            ref={errorNoticeRef}
            tabIndex={-1}
            className="service-admin-notice service-admin-notice-red"
          >
            {error}
          </div>
        ) : null}

        {currentStage === 'basic' ? (
          <>
            <div className="service-admin-form-grid">
              <Field label="Service name" required error={fieldErrors.name}>
                <input
                  ref={(node) => {
                    fieldRefs.current.name = node
                  }}
                  aria-invalid={fieldErrors.name ? true : undefined}
                  value={name}
                  onChange={(event) => {
                    clearFieldError('name')
                    setName(event.target.value)
                  }}
                />
              </Field>
              <Field label="Service code" required error={fieldErrors.code}>
                <input
                  ref={(node) => {
                    fieldRefs.current.code = node
                  }}
                  aria-invalid={fieldErrors.code ? true : undefined}
                  value={code}
                  onChange={(event) => {
                    clearFieldError('code')
                    setCode(event.target.value)
                  }}
                />
              </Field>
              <Field label="Category" required error={fieldErrors.categoryId}>
                <select
                  ref={(node) => {
                    fieldRefs.current.categoryId = node
                  }}
                  aria-invalid={fieldErrors.categoryId ? true : undefined}
                  value={categoryId || ''}
                  onChange={(event) => {
                    clearFieldError('categoryId')
                    setCategoryId(Number(event.target.value))
                  }}
                >
                  <option value="">Select a category</option>
                  {categories.map((item) => (
                    <option key={item.id} value={item.id}>
                      {categoryLabel(item.name)}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="Division" required error={fieldErrors.division}>
                <select
                  ref={(node) => {
                    fieldRefs.current.division = node
                  }}
                  aria-invalid={fieldErrors.division ? true : undefined}
                  value={division}
                  onChange={(event) => {
                    clearFieldError('division')
                    setDivision(event.target.value)
                  }}
                >
                  {divisions.map((item) => (
                    <option key={item}>{item}</option>
                  ))}
                </select>
              </Field>
              {access.ownerRoles ? (
                <Field label="Owner role">
                  <select
                    value={ownerRoleId ?? ''}
                    onChange={(event) =>
                      setOwnerRoleId(event.target.value ? Number(event.target.value) : null)
                    }
                  >
                    <option value="">Unassigned</option>
                    {ownerRoles.map((role) => (
                      <option key={role.id} value={role.id}>
                        {role.name}
                      </option>
                    ))}
                  </select>
                </Field>
              ) : null}
            </div>
            <Field label="Description" required error={fieldErrors.description}>
              <textarea
                ref={(node) => {
                  fieldRefs.current.description = node
                }}
                aria-invalid={fieldErrors.description ? true : undefined}
                className="service-admin-description-textarea"
                value={description}
                rows={4}
                placeholder="Describe what this service covers, who it is for, the expected delivery outcome, and any important scope notes."
                onChange={(event) => {
                  clearFieldError('description')
                  setDescription(event.target.value)
                }}
              />
            </Field>
            <div className="service-admin-form-grid">
              <Field label="SLA (days)" required error={fieldErrors.slaDays}>
                <input
                  ref={(node) => {
                    fieldRefs.current.slaDays = node
                  }}
                  aria-invalid={fieldErrors.slaDays ? true : undefined}
                  type="number"
                  min={1}
                  value={formatNumberFieldValue(slaDays)}
                  onChange={(event) => {
                    clearFieldError('slaDays')
                    setSlaDays(parseNumberFieldValue(event.target.value))
                  }}
                />
              </Field>
              <Field label="Fulfillment mode" required error={fieldErrors.fulfilmentMode}>
                <select
                  ref={(node) => {
                    fieldRefs.current.fulfilmentMode = node
                  }}
                  aria-invalid={fieldErrors.fulfilmentMode ? true : undefined}
                  value={fulfilmentMode}
                  onChange={(event) => {
                    clearFieldError('fulfilmentMode')
                    setFulfilmentMode(event.target.value)
                  }}
                >
                  <option>Quick service order</option>
                  <option>Managed service case</option>
                  <option>Project & worksite</option>
                  <option>Transaction & allocation</option>
                  <option>Supply order</option>
                </select>
              </Field>
            </div>
          </>
        ) : null}

        {currentStage === 'subservices' ? (
          <SubserviceStagePanel
            drafts={subserviceDrafts}
            pending={pending}
            error={fieldErrors.subservices}
            addButtonRef={(node) => {
              fieldRefs.current.subservices = node
            }}
            onAdd={addSubservice}
            onEdit={editSubservice}
            onRemove={removeSubservice}
          />
        ) : null}

        {currentStage === 'pricing' ? (
          <div className="service-admin-form-grid">
            <Field label="Pricing method" required error={fieldErrors.pricingMethod}>
              <select
                ref={(node) => {
                  fieldRefs.current.pricingMethod = node
                }}
                aria-invalid={fieldErrors.pricingMethod ? true : undefined}
                value={pricingMethod}
                onChange={(event) => {
                  clearFieldError('pricingMethod')
                  setPricingMethod(event.target.value)
                }}
              >
                <option>Fixed</option>
                <option>Unit rate</option>
                <option>Area rate</option>
                <option>Percentage</option>
              </select>
            </Field>
            <Field label="Base / unit price" required error={fieldErrors.rate}>
              <input
                ref={(node) => {
                  fieldRefs.current.rate = node
                }}
                aria-invalid={fieldErrors.rate ? true : undefined}
                type="number"
                min={0}
                value={formatNumberFieldValue(rate)}
                onChange={(event) => {
                  clearFieldError('rate')
                  setRate(parseNumberFieldValue(event.target.value))
                }}
              />
            </Field>
            <Field label="Deposit (%)" required error={fieldErrors.depositPercent}>
              <input
                ref={(node) => {
                  fieldRefs.current.depositPercent = node
                }}
                aria-invalid={fieldErrors.depositPercent ? true : undefined}
                type="number"
                min={0}
                max={100}
                value={formatNumberFieldValue(depositPercent)}
                onChange={(event) => {
                  clearFieldError('depositPercent')
                  setDepositPercent(parseNumberFieldValue(event.target.value))
                }}
              />
            </Field>
            <Field label="Tax (%)" required error={fieldErrors.taxPercent}>
              <input
                ref={(node) => {
                  fieldRefs.current.taxPercent = node
                }}
                aria-invalid={fieldErrors.taxPercent ? true : undefined}
                type="number"
                min={0}
                max={100}
                value={formatNumberFieldValue(taxPercent)}
                onChange={(event) => {
                  clearFieldError('taxPercent')
                  setTaxPercent(parseNumberFieldValue(event.target.value))
                }}
              />
            </Field>
            <Field
              label="Discount approval above (%)"
              required
              error={fieldErrors.discountApprovalPercent}
            >
              <input
                ref={(node) => {
                  fieldRefs.current.discountApprovalPercent = node
                }}
                aria-invalid={fieldErrors.discountApprovalPercent ? true : undefined}
                type="number"
                min={0}
                max={100}
                value={formatNumberFieldValue(discountApprovalPercent)}
                onChange={(event) => {
                  clearFieldError('discountApprovalPercent')
                  setDiscountApprovalPercent(parseNumberFieldValue(event.target.value))
                }}
              />
            </Field>
          </div>
        ) : null}

        {currentStage === 'request-form' ? (
          <>
            <div
              ref={(node) => {
                fieldRefs.current.requestFields = node
              }}
              tabIndex={-1}
              className="service-admin-check-grid"
            >
              {requestFieldOptions.map((field) => (
                <label key={field} className="service-admin-check-option">
                  <input
                    type="checkbox"
                    checked={requestFields.includes(field)}
                    onChange={(event) => {
                      clearFieldError('requestFields')
                      setRequestFields((current) =>
                        event.target.checked
                          ? [...current, field]
                          : current.filter((item) => item !== field),
                      )
                    }}
                  />
                  {field}
                </label>
              ))}
            </div>
            {fieldErrors.requestFields ? (
              <small className="service-admin-field-error">{fieldErrors.requestFields}</small>
            ) : null}
          </>
        ) : null}

        {currentStage === 'workflow' ? (
          <Field label="Workflow stages — one per line" full required error={fieldErrors.workflow}>
            <textarea
              ref={(node) => {
                fieldRefs.current.workflow = node
              }}
              aria-invalid={fieldErrors.workflow ? true : undefined}
              className="service-admin-wizard-textarea"
              value={workflow}
              placeholder={
                'Request Review\nTechnical Assessment\nQuotation\nApproval\nExecution\nQuality Review\nCompletion'
              }
              onChange={(event) => {
                clearFieldError('workflow')
                setWorkflow(event.target.value)
              }}
            />
          </Field>
        ) : null}

        {currentStage === 'branches' ? (
          <Field
            label="Active branches"
            full
            required={status === 'active'}
            error={fieldErrors.branches}
          >
            {branchOptions.length > 0 ? (
              <div
                ref={(node) => {
                  fieldRefs.current.branches = node
                }}
                tabIndex={-1}
                className="service-admin-check-grid service-admin-check-grid--branches"
              >
                {branchOptions.map((branch) => (
                  <label key={branch.id} className="service-admin-check-option">
                    <input
                      type="checkbox"
                      checked={effectiveSelectedBranchIds.includes(branch.id)}
                      onChange={(event) => {
                        clearFieldError('branches')
                        setSelectedBranchIds((current) =>
                          event.target.checked
                            ? [...(current ?? effectiveSelectedBranchIds), branch.id]
                            : (current ?? effectiveSelectedBranchIds).filter(
                                (item) => item !== branch.id,
                              ),
                        )
                      }}
                    />
                    {branch.name}
                  </label>
                ))}
              </div>
            ) : (
              <div className="service-admin-notice service-admin-notice-blue">
                No active branches are available yet. You can save this service as a draft and add
                branches before publishing. Publishing requires at least one active branch.
              </div>
            )}

            {branchOptions.length > 0 && effectiveSelectedBranchIds.length === 0 ? (
              <div className="service-admin-notice service-admin-notice-blue">
                No branch selected. This is allowed for Draft or Paused services. Select at least
                one branch before choosing Active / Publish.
              </div>
            ) : null}
          </Field>
        ) : null}

        {currentStage === 'review' ? (
          <>
            <div className="service-admin-form-grid service-admin-publish-grid">
              {access.publish ? (
                <Field label="Status" required error={fieldErrors.status}>
                  <select
                    ref={(node) => {
                      fieldRefs.current.status = node
                    }}
                    aria-invalid={fieldErrors.status ? true : undefined}
                    value={status}
                    onChange={(event) => {
                      clearFieldError('status')
                      setStatus(event.target.value as typeof status)
                    }}
                  >
                    <option value="draft">Draft</option>
                    {canPublishActive ? <option value="active">Active / Publish</option> : null}
                    <option value="inactive">Paused</option>
                  </select>
                </Field>
              ) : null}
              <Field label="Client visibility" required error={fieldErrors.clientVisibility}>
                <select
                  ref={(node) => {
                    fieldRefs.current.clientVisibility = node
                  }}
                  aria-invalid={fieldErrors.clientVisibility ? true : undefined}
                  value={clientVisibility}
                  onChange={(event) => {
                    clearFieldError('clientVisibility')
                    setClientVisibility(event.target.value as typeof clientVisibility)
                  }}
                >
                  <option value="visible">Visible in catalogue</option>
                  <option value="internal">Internal only</option>
                  <option value="hidden">Hidden</option>
                </select>
              </Field>
            </div>
            <div className="service-admin-notice service-admin-notice-green">
              <b>Ready to create.</b> This setup will submit the sections available for your role.
            </div>

            {progress.length > 0 ? (
              <div className="service-admin-card">
                <div className="service-admin-card-header">
                  <div>
                    <div className="service-admin-card-title">Setup progress</div>
                    <div className="service-admin-card-subtitle">
                      {setupServiceId ? `Service #${setupServiceId}` : 'Creating Service'}
                    </div>
                  </div>
                  <strong>{progressPercent}%</strong>
                </div>
                <progress max={100} value={progressPercent} style={{ width: '100%' }} />
                <div className="service-admin-stack">
                  {progress.map((item) => (
                    <div key={item.id} className="service-admin-row">
                      <div>
                        <b>
                          {symbol(item.state)} {item.label}
                        </b>
                        {item.error ? (
                          <div className="service-admin-row-subtitle">{item.error}</div>
                        ) : null}
                      </div>
                      <span>{item.state}</span>
                    </div>
                  ))}
                </div>
                {retryable.length > 0 && onRetryFailed ? (
                  <button
                    type="button"
                    className="service-admin-button service-admin-button-primary"
                    disabled={pending}
                    onClick={onRetryFailed}
                  >
                    {pending ? 'Retrying…' : 'Retry failed setup'}
                  </button>
                ) : null}
              </div>
            ) : null}
          </>
        ) : null}
      </ModalShell>
      {subserviceEditorDraft ? (
        <SubserviceEditorModal
          draft={subserviceEditorDraft}
          pending={pending}
          title={editingSubserviceId ? 'Edit Sub-service' : 'Add Sub-service'}
          onClose={() => {
            setEditingSubserviceId(null)
            setSubserviceEditorDraft(null)
          }}
          onSave={saveSubserviceDraft}
        />
      ) : null}
    </>
  )
}

export function ConfigureServiceWorkspace({
  service,
  calculator,
  requestForm,
  workflow,
  branches: branchOptions = [],
  ownerRoles = [],
  pending,
  onClose,
  onSave,
  readOnly = false,
}: {
  service: ServiceCatalogueItem
  calculator?: PricingCalculator
  requestForm?: ServiceRequestForm
  workflow?: ServiceWorkflow
  branches?: Array<{ id: number; name: string; code: string }>
  ownerRoles?: WorkflowOwnerRoleOption[]
  pending: boolean
  onClose: () => void
  onSave?: (input: ConfigureServiceInput) => void
  readOnly?: boolean
}) {
  const [step, setStep] = useState(0)
  const [name, setName] = useState(service.name)
  const [code, setCode] = useState(service.code)
  const [division, setDivision] = useState(service.division)
  const [owner, setOwner] = useState(service.owner)
  const [ownerRoleId, setOwnerRoleId] = useState<number | null>(() => {
    const matchedRole = ownerRoles.find((role) => role.name === service.owner)
    return matchedRole?.id ?? null
  })
  const [description, setDescription] = useState(service.description)
  const [slaDays, setSlaDays] = useState(service.slaDays ?? 5)
  const [fulfilmentMode, setFulfilmentMode] = useState(
    service.fulfilmentMode ?? 'Quick service order',
  )
  const [subserviceDrafts, setSubserviceDrafts] = useState<CreateSubserviceDraft[]>(() =>
    buildSubserviceDraftsFromNames(service.subservices ?? [], service.slaDays ?? 5, service.status),
  )
  const [subserviceEditorDraft, setSubserviceEditorDraft] = useState<CreateSubserviceDraft | null>(
    null,
  )
  const [editingSubserviceId, setEditingSubserviceId] = useState<string | null>(null)
  const [pricingMethod, setPricingMethod] = useState(
    calculator?.charges.some((charge) => charge.kind === 'formula') ? 'Custom formula' : 'Fixed',
  )
  const [rate, setRate] = useState(
    typeof calculator?.charges.find((charge) => charge.kind === 'fixed')?.value === 'number'
      ? Number(calculator?.charges.find((charge) => charge.kind === 'fixed')?.value)
      : Math.max(0, calculator?.sampleTotal ?? 100000),
  )
  const [depositPercent, setDepositPercent] = useState(() => {
    const value = calculator?.charges.find((charge) =>
      charge.label.toLowerCase().includes('deposit'),
    )?.value
    return typeof value === 'number' ? value : 70
  })
  const [taxPercent, setTaxPercent] = useState(() => {
    const value = calculator?.charges.find((charge) =>
      charge.label.toLowerCase().includes('tax'),
    )?.value
    return typeof value === 'number' ? value : 0
  })
  const [discountApprovalPercent, setDiscountApprovalPercent] = useState(5)
  const [requestFields, setRequestFields] = useState<string[]>(
    requestForm?.fields.map((field) => field.label) ??
      service.requestFields ?? [
        'Client identity',
        'Phone & email',
        'Customer type',
        'Location / site',
        'Budget',
        'Preferred date',
        'Scope / message',
        'Document uploads',
      ],
  )
  const [workflowText, setWorkflowText] = useState(
    (
      workflow?.stages.map((stage) => stage.name) ??
      service.workflowStages ?? [
        'Request Review',
        'Technical Assessment',
        'Quotation',
        'Approval',
        'Invoice & Payment',
        'Service Order',
        'Execution',
        'Quality Review',
        'Client Acceptance',
        'Completion & Feedback',
      ]
    ).join('\n'),
  )
  const [selectedBranches, setSelectedBranches] = useState<string[]>(
    service.branchNames.length
      ? [...service.branchNames]
      : branchOptions.map((branch) => branch.name),
  )
  const [status, setStatus] = useState(service.status)
  const [clientVisibility, setClientVisibility] = useState('Visible in catalogue')
  const [error, setError] = useState('')
  const [fieldErrors, setFieldErrors] = useState<ServiceWizardFieldErrors>({})
  const fieldRefs = useRef<Record<string, HTMLElement | null>>({})
  const errorNoticeRef = useRef<HTMLDivElement | null>(null)

  const buildPayload = (): ConfigureServiceInput => ({
    id: service.id,
    name: name.trim(),
    code: code.trim(),
    division,
    owner: owner.trim(),
    ownerRoleId,
    description: description.trim(),
    slaDays,
    fulfilmentMode,
    status,
    branchNames: selectedBranches,
    subservices: serializeSubserviceDrafts(subserviceDrafts),
    pricing: {
      method: pricingMethod,
      rate,
      depositPercent,
      taxPercent,
      discountApprovalPercent,
    },
    requestFields,
    workflowStages: splitLines(workflowText),
  })

  const clearFieldError = (field: ServiceWizardFieldName) => {
    setFieldErrors((current) => {
      if (!current[field]) return current
      const next = { ...current }
      delete next[field]
      return next
    })
  }

  const failValidation = (message: string, field?: ServiceWizardFieldName) => {
    setError(message)
    setFieldErrors(field ? { [field]: message } : {})
    if (field) {
      focusField(fieldRefs, field)
      return
    }
    focusNotice(errorNoticeRef)
  }

  const validateStep = (
    index: number,
  ): { message: string; field?: ServiceWizardFieldName } | null => {
    if (index === 0) {
      if (!name.trim()) return { message: 'Service name is required.', field: 'name' }
      if (!code.trim()) return { message: 'Service code is required.', field: 'code' }
      if (!division.trim()) return { message: 'Division is required.', field: 'division' }
      if (!owner.trim()) return { message: 'Owner role is required.', field: 'ownerRoleId' }
      if (!description.trim()) return { message: 'Description is required.', field: 'description' }
      if (!Number.isFinite(slaDays) || slaDays < 1) {
        return { message: 'SLA must be at least 1 day.', field: 'slaDays' }
      }
      if (!fulfilmentMode.trim()) {
        return { message: 'Fulfillment mode is required.', field: 'fulfilmentMode' }
      }
      return null
    }
    if (index === 1) {
      const subserviceError = validateSubserviceDrafts(subserviceDrafts)
      return subserviceError ? { message: subserviceError, field: 'subservices' } : null
    }
    if (index === 2) {
      if (!pricingMethod.trim()) {
        return { message: 'Pricing method is required.', field: 'pricingMethod' }
      }
      if (!Number.isFinite(rate) || rate < 0) {
        return { message: 'Base / unit price is required.', field: 'rate' }
      }
      if (!Number.isFinite(depositPercent) || depositPercent < 0 || depositPercent > 100) {
        return { message: 'Deposit (%) must be between 0 and 100.', field: 'depositPercent' }
      }
      if (!Number.isFinite(taxPercent) || taxPercent < 0 || taxPercent > 100) {
        return { message: 'Tax (%) must be between 0 and 100.', field: 'taxPercent' }
      }
      if (
        !Number.isFinite(discountApprovalPercent) ||
        discountApprovalPercent < 0 ||
        discountApprovalPercent > 100
      ) {
        return {
          message: 'Discount approval (%) must be between 0 and 100.',
          field: 'discountApprovalPercent',
        }
      }
      return null
    }
    if (index === 3 && requestFields.length === 0) {
      return { message: 'Select at least one request form field.', field: 'requestFields' }
    }
    if (index === 4 && splitLines(workflowText).length === 0) {
      return { message: 'Add at least one workflow stage.', field: 'workflow' }
    }
    if (index === 5 && selectedBranches.length === 0) {
      return { message: 'Select at least one active branch.', field: 'branches' }
    }
    return null
  }

  const save = () => {
    for (let index = 0; index < wizardSteps.length; index += 1) {
      const validationError = validateStep(index)
      if (validationError) {
        setStep(index)
        failValidation(validationError.message, validationError.field)
        return
      }
    }
    setError('')
    setFieldErrors({})
    if (!onSave) return
    onSave(buildPayload())
  }

  const next = () => {
    const validationError = validateStep(step)
    if (validationError) {
      failValidation(validationError.message, validationError.field)
      return
    }
    setError('')
    setFieldErrors({})
    if (step === wizardSteps.length - 1) {
      save()
      return
    }
    setStep((current) => Math.min(wizardSteps.length - 1, current + 1))
  }

  const addSubservice = () => {
    setEditingSubserviceId(null)
    setSubserviceEditorDraft(
      createSubserviceDraft(slaDays, {
        status: subserviceStatusForServiceStatus(status),
      }),
    )
    setError('')
  }

  const editSubservice = (localId: string) => {
    const currentDraft = subserviceDrafts.find((item) => item.localId === localId)
    if (!currentDraft) return
    setEditingSubserviceId(localId)
    setSubserviceEditorDraft(currentDraft)
  }

  const removeSubservice = (localId: string) => {
    setSubserviceDrafts((current) => current.filter((item) => item.localId !== localId))
    if (editingSubserviceId === localId) {
      setEditingSubserviceId(null)
      setSubserviceEditorDraft(null)
    }
    setError('')
  }

  const saveSubserviceDraft = (draft: CreateSubserviceDraft) => {
    if (editingSubserviceId) {
      setSubserviceDrafts((current) =>
        current.map((item) => (item.localId === editingSubserviceId ? draft : item)),
      )
    } else {
      setSubserviceDrafts((current) => [...current, draft])
    }
    setEditingSubserviceId(null)
    setSubserviceEditorDraft(null)
    setError('')
  }

  return (
    <>
      <ModalShell
        title={readOnly ? service.name : `Configure ${service.name}`}
        wide
        variant="wizard"
        onClose={onClose}
        footer={
          <>
            <button
              type="button"
              className="service-admin-button service-admin-wizard-nav-btn"
              disabled={pending}
              onClick={onClose}
            >
              Cancel
            </button>
            <button
              type="button"
              className="service-admin-button service-admin-wizard-nav-btn"
              disabled={step === 0 || pending}
              onClick={() => {
                setError('')
                setStep((current) => Math.max(0, current - 1))
              }}
            >
              Previous
            </button>
            <button
              type="button"
              className="service-admin-button service-admin-wizard-nav-btn"
              disabled={step === wizardSteps.length - 1 || pending}
              onClick={next}
            >
              Next
            </button>
            {!readOnly ? (
              <button
                type="button"
                className="service-admin-button service-admin-button-primary service-admin-wizard-nav-btn service-admin-wizard-nav-btn--primary"
                disabled={pending}
                onClick={save}
              >
                {pending ? 'Saving…' : 'Save Configuration'}
              </button>
            ) : null}
          </>
        }
      >
        <div
          className="service-admin-wizard-steps"
          role="tablist"
          aria-label="Configure service steps"
        >
          {wizardSteps.map((item, index) => {
            const isActive = index === step
            return (
              <button
                key={item}
                type="button"
                role="tab"
                aria-selected={isActive}
                disabled={pending}
                className={[
                  'service-admin-wizard-step',
                  'service-admin-wizard-step--reachable',
                  isActive
                    ? 'service-admin-wizard-step--active'
                    : 'service-admin-wizard-step--complete',
                ]
                  .filter(Boolean)
                  .join(' ')}
                onClick={() => {
                  setError('')
                  setStep(index)
                }}
              >
                {index + 1}. {item}
              </button>
            )
          })}
        </div>

        {error ? (
          <div
            ref={errorNoticeRef}
            tabIndex={-1}
            className="service-admin-notice service-admin-notice-red"
          >
            {error}
          </div>
        ) : null}

        {readOnly ? (
          <div className="service-admin-notice service-admin-notice-blue">
            This service view is currently read-only. Use the dedicated setup screens to update its
            configuration, pricing, workflow, request form, or branch activation.
          </div>
        ) : null}

        <fieldset disabled={readOnly} style={{ border: 0, padding: 0, margin: 0, minWidth: 0 }}>
          {step === 0 ? (
            <>
              <div className="service-admin-form-grid">
                <Field label="Service name" required error={fieldErrors.name}>
                  <input
                    ref={(node) => {
                      fieldRefs.current.name = node
                    }}
                    aria-invalid={fieldErrors.name ? true : undefined}
                    value={name}
                    required
                    onChange={(event) => {
                      clearFieldError('name')
                      setName(event.target.value)
                    }}
                  />
                </Field>
                <Field label="Service code" required error={fieldErrors.code}>
                  <input
                    ref={(node) => {
                      fieldRefs.current.code = node
                    }}
                    aria-invalid={fieldErrors.code ? true : undefined}
                    value={code}
                    required
                    onChange={(event) => {
                      clearFieldError('code')
                      setCode(event.target.value)
                    }}
                  />
                </Field>
                <Field label="Division" required error={fieldErrors.division}>
                  <select
                    ref={(node) => {
                      fieldRefs.current.division = node
                    }}
                    aria-invalid={fieldErrors.division ? true : undefined}
                    value={division}
                    required
                    onChange={(event) => {
                      clearFieldError('division')
                      setDivision(event.target.value)
                    }}
                  >
                    {divisions.map((item) => (
                      <option key={item}>{item}</option>
                    ))}
                  </select>
                </Field>
                <Field label="Owner role" required error={fieldErrors.ownerRoleId}>
                  <select
                    ref={(node) => {
                      fieldRefs.current.ownerRoleId = node
                    }}
                    aria-invalid={fieldErrors.ownerRoleId ? true : undefined}
                    value={ownerRoleId ?? ''}
                    required
                    onChange={(event) => {
                      clearFieldError('ownerRoleId')
                      const nextOwnerRoleId = event.target.value ? Number(event.target.value) : null
                      const selectedOwnerRole = ownerRoles.find(
                        (role) => role.id === nextOwnerRoleId,
                      )
                      setOwnerRoleId(nextOwnerRoleId)
                      setOwner(selectedOwnerRole?.name ?? '')
                    }}
                  >
                    <option value="" disabled>
                      Select an owner role
                    </option>
                    {ownerRoles.map((role) => (
                      <option key={role.id} value={role.id}>
                        {role.name}
                      </option>
                    ))}
                  </select>
                </Field>
              </div>
              <Field label="Description" required error={fieldErrors.description}>
                <textarea
                  ref={(node) => {
                    fieldRefs.current.description = node
                  }}
                  aria-invalid={fieldErrors.description ? true : undefined}
                  className="service-admin-description-textarea"
                  value={description}
                  required
                  rows={4}
                  placeholder="Describe what this service covers, who it is for, the expected delivery outcome, and any important scope notes."
                  onChange={(event) => {
                    clearFieldError('description')
                    setDescription(event.target.value)
                  }}
                />
              </Field>
              <div className="service-admin-form-grid">
                <Field label="SLA (days)" required error={fieldErrors.slaDays}>
                  <input
                    ref={(node) => {
                      fieldRefs.current.slaDays = node
                    }}
                    aria-invalid={fieldErrors.slaDays ? true : undefined}
                    type="number"
                    min={1}
                    required
                    value={formatNumberFieldValue(slaDays)}
                    onChange={(event) => {
                      clearFieldError('slaDays')
                      setSlaDays(parseNumberFieldValue(event.target.value))
                    }}
                  />
                </Field>
                <Field label="Fulfillment mode" required error={fieldErrors.fulfilmentMode}>
                  <select
                    ref={(node) => {
                      fieldRefs.current.fulfilmentMode = node
                    }}
                    aria-invalid={fieldErrors.fulfilmentMode ? true : undefined}
                    value={fulfilmentMode}
                    required
                    onChange={(event) => {
                      clearFieldError('fulfilmentMode')
                      setFulfilmentMode(event.target.value)
                    }}
                  >
                    <option>Quick service order</option>
                    <option>Managed service case</option>
                    <option>Project & worksite</option>
                    <option>Transaction & allocation</option>
                    <option>Supply order</option>
                  </select>
                </Field>
              </div>
            </>
          ) : null}

          {step === 1 ? (
            <SubserviceStagePanel
              drafts={subserviceDrafts}
              pending={pending}
              error={fieldErrors.subservices}
              addButtonRef={(node) => {
                fieldRefs.current.subservices = node
              }}
              onAdd={addSubservice}
              onEdit={editSubservice}
              onRemove={removeSubservice}
            />
          ) : null}

          {step === 2 ? (
            <div className="service-admin-form-grid">
              <Field label="Pricing method" required error={fieldErrors.pricingMethod}>
                <select
                  ref={(node) => {
                    fieldRefs.current.pricingMethod = node
                  }}
                  aria-invalid={fieldErrors.pricingMethod ? true : undefined}
                  value={pricingMethod}
                  required
                  onChange={(event) => {
                    clearFieldError('pricingMethod')
                    setPricingMethod(event.target.value)
                  }}
                >
                  <option>Fixed</option>
                  <option>Unit rate</option>
                  <option>Area rate</option>
                  <option>Percentage</option>
                  <option>Custom formula</option>
                </select>
              </Field>
              <Field label="Base / unit price" required error={fieldErrors.rate}>
                <input
                  ref={(node) => {
                    fieldRefs.current.rate = node
                  }}
                  aria-invalid={fieldErrors.rate ? true : undefined}
                  type="number"
                  min={0}
                  required
                  value={formatNumberFieldValue(rate)}
                  onChange={(event) => {
                    clearFieldError('rate')
                    setRate(parseNumberFieldValue(event.target.value))
                  }}
                />
              </Field>
              <Field label="Deposit (%)" required error={fieldErrors.depositPercent}>
                <input
                  ref={(node) => {
                    fieldRefs.current.depositPercent = node
                  }}
                  aria-invalid={fieldErrors.depositPercent ? true : undefined}
                  type="number"
                  min={0}
                  max={100}
                  required
                  value={formatNumberFieldValue(depositPercent)}
                  onChange={(event) => {
                    clearFieldError('depositPercent')
                    setDepositPercent(parseNumberFieldValue(event.target.value))
                  }}
                />
              </Field>
              <Field label="Tax (%)" required error={fieldErrors.taxPercent}>
                <input
                  ref={(node) => {
                    fieldRefs.current.taxPercent = node
                  }}
                  aria-invalid={fieldErrors.taxPercent ? true : undefined}
                  type="number"
                  min={0}
                  max={100}
                  required
                  value={formatNumberFieldValue(taxPercent)}
                  onChange={(event) => {
                    clearFieldError('taxPercent')
                    setTaxPercent(parseNumberFieldValue(event.target.value))
                  }}
                />
              </Field>
              <Field
                label="Discount approval above (%)"
                required
                error={fieldErrors.discountApprovalPercent}
              >
                <input
                  ref={(node) => {
                    fieldRefs.current.discountApprovalPercent = node
                  }}
                  aria-invalid={fieldErrors.discountApprovalPercent ? true : undefined}
                  type="number"
                  min={0}
                  max={100}
                  required
                  value={formatNumberFieldValue(discountApprovalPercent)}
                  onChange={(event) => {
                    clearFieldError('discountApprovalPercent')
                    setDiscountApprovalPercent(parseNumberFieldValue(event.target.value))
                  }}
                />
              </Field>
            </div>
          ) : null}

          {step === 3 ? (
            <>
              <div className="service-admin-notice service-admin-notice-blue">
                Select information required before submission.
                <em className="service-admin-required">*</em>
              </div>
              <div
                ref={(node) => {
                  fieldRefs.current.requestFields = node
                }}
                tabIndex={-1}
                className="service-admin-check-grid"
              >
                {requestFieldOptions.map((field) => (
                  <label key={field} className="service-admin-check-option">
                    <input
                      type="checkbox"
                      checked={requestFields.includes(field)}
                      onChange={(event) => {
                        clearFieldError('requestFields')
                        setRequestFields((current) =>
                          event.target.checked
                            ? [...current, field]
                            : current.filter((item) => item !== field),
                        )
                      }}
                    />
                    {field}
                  </label>
                ))}
              </div>
              {fieldErrors.requestFields ? (
                <small className="service-admin-field-error">{fieldErrors.requestFields}</small>
              ) : null}
            </>
          ) : null}

          {step === 4 ? (
            <Field
              label="Workflow stages — one per line"
              full
              required
              error={fieldErrors.workflow}
            >
              <textarea
                ref={(node) => {
                  fieldRefs.current.workflow = node
                }}
                aria-invalid={fieldErrors.workflow ? true : undefined}
                className="service-admin-wizard-textarea"
                value={workflowText}
                required
                placeholder={
                  'Request Review\nTechnical Assessment\nQuotation\nApproval\nExecution\nQuality Review\nCompletion'
                }
                onChange={(event) => {
                  clearFieldError('workflow')
                  setWorkflowText(event.target.value)
                }}
              />
            </Field>
          ) : null}

          {step === 5 ? (
            <>
              <Field label="Active branches" full required error={fieldErrors.branches}>
                <div
                  ref={(node) => {
                    fieldRefs.current.branches = node
                  }}
                  tabIndex={-1}
                  className="service-admin-check-grid service-admin-check-grid--branches"
                >
                  {branchOptions.map((branch) => (
                    <label key={branch.id} className="service-admin-check-option">
                      <input
                        type="checkbox"
                        checked={selectedBranches.includes(branch.name)}
                        onChange={(event) => {
                          clearFieldError('branches')
                          setSelectedBranches((current) =>
                            event.target.checked
                              ? [...current, branch.name]
                              : current.filter((item) => item !== branch.name),
                          )
                        }}
                      />
                      {branch.name}
                    </label>
                  ))}
                </div>
              </Field>
              <div className="service-admin-form-grid service-admin-publish-grid">
                <Field label="Status" required>
                  <select
                    value={status}
                    required
                    onChange={(event) => setStatus(event.target.value as typeof status)}
                  >
                    <option value="draft">Draft</option>
                    <option value="active">Active</option>
                    <option value="inactive">Paused</option>
                  </select>
                </Field>
                <Field label="Client visibility" required>
                  <select
                    value={clientVisibility}
                    required
                    onChange={(event) => setClientVisibility(event.target.value)}
                  >
                    <option>Visible in catalogue</option>
                    <option>Internal only</option>
                    <option>Hidden</option>
                  </select>
                </Field>
              </div>
              <div className="service-admin-notice service-admin-notice-green">
                <b>Ready to update.</b> Changes across basic setup, pricing, request form, workflow
                and branch activation will be saved together.
              </div>
            </>
          ) : null}
        </fieldset>
      </ModalShell>
      {subserviceEditorDraft ? (
        <SubserviceEditorModal
          draft={subserviceEditorDraft}
          pending={pending}
          title={editingSubserviceId ? 'Edit Sub-service' : 'Add Sub-service'}
          onClose={() => {
            setEditingSubserviceId(null)
            setSubserviceEditorDraft(null)
          }}
          onSave={saveSubserviceDraft}
        />
      ) : null}
    </>
  )
}
