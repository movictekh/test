import { IconX } from '@tabler/icons-react'
import { useState } from 'react'

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
}: {
  label: string
  children: React.ReactNode
  full?: boolean
  required?: boolean
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
    </label>
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
  const [subservices, setSubservices] = useState('Standard Package\nPremium Package')
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

  const validateStage = (stage: WizardStage): string | null => {
    if (stage === 'basic') {
      if (!name.trim()) return 'Service name is required.'
      if (!code.trim()) return 'Service code is required.'
      if (!categoryId) return 'Service category is required.'
      if (!division.trim()) return 'Division is required.'
      if (!description.trim()) return 'Description is required.'
      if (!Number.isFinite(slaDays) || slaDays < 1) return 'SLA must be at least 1 day.'
      if (!fulfilmentMode.trim()) return 'Fulfillment mode is required.'
    }
    if (stage === 'subservices' && splitLines(subservices).length === 0)
      return 'Add at least one sub-service.'
    if (stage === 'pricing') {
      if (!pricingMethod.trim()) return 'Pricing method is required.'
      if (!Number.isFinite(rate) || rate < 0) return 'Base / unit price is required.'
      if (!Number.isFinite(depositPercent) || depositPercent < 0 || depositPercent > 100)
        return 'Deposit (%) must be between 0 and 100.'
      if (!Number.isFinite(taxPercent) || taxPercent < 0 || taxPercent > 100)
        return 'Tax (%) must be between 0 and 100.'
      if (
        !Number.isFinite(discountApprovalPercent) ||
        discountApprovalPercent < 0 ||
        discountApprovalPercent > 100
      )
        return 'Discount approval (%) must be between 0 and 100.'
    }
    if (stage === 'request-form' && requestFields.length === 0)
      return 'Select at least one request form field.'
    if (stage === 'workflow' && splitLines(workflow).length === 0)
      return 'Add at least one workflow stage.'
    if (stage === 'branches' && status === 'active' && effectiveSelectedBranchIds.length === 0) {
      return 'Select at least one active branch before publishing.'
    }
    return null
  }

  const submit = () => {
    for (const stage of steps) {
      if (stage.id === 'review') continue
      const problem = validateStage(stage.id)
      if (problem) {
        setError(problem)
        setStep(steps.findIndex((item) => item.id === stage.id))
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
      subservices: splitLines(subservices),
      pricing: { method: pricingMethod, rate, depositPercent, taxPercent, discountApprovalPercent },
      requestFields,
      workflowStages: splitLines(workflow),
      enabledStages,
    })
  }

  const next = () => {
    const problem = validateStage(currentStage)
    if (problem) {
      setError(problem)
      return
    }
    setError('')
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
      <div className="service-admin-wizard-steps" role="tablist" aria-label="Create service steps">
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

      {error ? <div className="service-admin-notice service-admin-notice-red">{error}</div> : null}

      {currentStage === 'basic' ? (
        <>
          <div className="service-admin-form-grid">
            <Field label="Service name" required>
              <input value={name} onChange={(event) => setName(event.target.value)} />
            </Field>
            <Field label="Service code" required>
              <input value={code} onChange={(event) => setCode(event.target.value)} />
            </Field>
            <Field label="Category" required>
              <select
                value={categoryId || ''}
                onChange={(event) => setCategoryId(Number(event.target.value))}
              >
                <option value="">Select a category</option>
                {categories.map((item) => (
                  <option key={item.id} value={item.id}>
                    {categoryLabel(item.name)}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Division" required>
              <select value={division} onChange={(event) => setDivision(event.target.value)}>
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
          <Field label="Description" required>
            <textarea
              className="service-admin-description-textarea"
              value={description}
              rows={4}
              placeholder="Describe what this service covers, who it is for, the expected delivery outcome, and any important scope notes."
              onChange={(event) => setDescription(event.target.value)}
            />
          </Field>
          <div className="service-admin-form-grid">
            <Field label="SLA (days)" required>
              <input
                type="number"
                min={1}
                value={formatNumberFieldValue(slaDays)}
                onChange={(event) => setSlaDays(parseNumberFieldValue(event.target.value))}
              />
            </Field>
            <Field label="Fulfillment mode" required>
              <select
                value={fulfilmentMode}
                onChange={(event) => setFulfilmentMode(event.target.value)}
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
        <Field label="Sub-services — one per line" full required>
          <textarea
            className="service-admin-wizard-textarea"
            value={subservices}
            placeholder={'Standard Package\nPremium Package\nEnterprise Package'}
            onChange={(event) => setSubservices(event.target.value)}
          />
        </Field>
      ) : null}

      {currentStage === 'pricing' ? (
        <div className="service-admin-form-grid">
          <Field label="Pricing method" required>
            <select
              value={pricingMethod}
              onChange={(event) => setPricingMethod(event.target.value)}
            >
              <option>Fixed</option>
              <option>Unit rate</option>
              <option>Area rate</option>
              <option>Percentage</option>
            </select>
          </Field>
          <Field label="Base / unit price" required>
            <input
              type="number"
              min={0}
              value={formatNumberFieldValue(rate)}
              onChange={(event) => setRate(parseNumberFieldValue(event.target.value))}
            />
          </Field>
          <Field label="Deposit (%)" required>
            <input
              type="number"
              min={0}
              max={100}
              value={formatNumberFieldValue(depositPercent)}
              onChange={(event) => setDepositPercent(parseNumberFieldValue(event.target.value))}
            />
          </Field>
          <Field label="Tax (%)" required>
            <input
              type="number"
              min={0}
              max={100}
              value={formatNumberFieldValue(taxPercent)}
              onChange={(event) => setTaxPercent(parseNumberFieldValue(event.target.value))}
            />
          </Field>
          <Field label="Discount approval above (%)" required>
            <input
              type="number"
              min={0}
              max={100}
              value={formatNumberFieldValue(discountApprovalPercent)}
              onChange={(event) =>
                setDiscountApprovalPercent(parseNumberFieldValue(event.target.value))
              }
            />
          </Field>
        </div>
      ) : null}

      {currentStage === 'request-form' ? (
        <div className="service-admin-check-grid">
          {requestFieldOptions.map((field) => (
            <label key={field} className="service-admin-check-option">
              <input
                type="checkbox"
                checked={requestFields.includes(field)}
                onChange={(event) =>
                  setRequestFields((current) =>
                    event.target.checked
                      ? [...current, field]
                      : current.filter((item) => item !== field),
                  )
                }
              />
              {field}
            </label>
          ))}
        </div>
      ) : null}

      {currentStage === 'workflow' ? (
        <Field label="Workflow stages — one per line" full required>
          <textarea
            className="service-admin-wizard-textarea"
            value={workflow}
            placeholder={
              'Request Review\nTechnical Assessment\nQuotation\nApproval\nExecution\nQuality Review\nCompletion'
            }
            onChange={(event) => setWorkflow(event.target.value)}
          />
        </Field>
      ) : null}

      {currentStage === 'branches' ? (
        <Field label="Active branches" full required={status === 'active'}>
          {branchOptions.length > 0 ? (
            <div className="service-admin-check-grid service-admin-check-grid--branches">
              {branchOptions.map((branch) => (
                <label key={branch.id} className="service-admin-check-option">
                  <input
                    type="checkbox"
                    checked={effectiveSelectedBranchIds.includes(branch.id)}
                    onChange={(event) =>
                      setSelectedBranchIds((current) =>
                        event.target.checked
                          ? [...(current ?? effectiveSelectedBranchIds), branch.id]
                          : (current ?? effectiveSelectedBranchIds).filter(
                              (item) => item !== branch.id,
                            ),
                      )
                    }
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
              No branch selected. This is allowed for Draft or Paused services. Select at least one
              branch before choosing Active / Publish.
            </div>
          ) : null}
        </Field>
      ) : null}

      {currentStage === 'review' ? (
        <>
          <div className="service-admin-form-grid service-admin-publish-grid">
            {access.publish ? (
              <Field label="Status" required>
                <select
                  value={status}
                  onChange={(event) => setStatus(event.target.value as typeof status)}
                >
                  <option value="draft">Draft</option>
                  {canPublishActive ? <option value="active">Active / Publish</option> : null}
                  <option value="inactive">Paused</option>
                </select>
              </Field>
            ) : null}
            <Field label="Client visibility" required>
              <select
                value={clientVisibility}
                onChange={(event) =>
                  setClientVisibility(event.target.value as typeof clientVisibility)
                }
              >
                <option value="visible">Visible in catalogue</option>
                <option value="internal">Internal only</option>
                <option value="hidden">Hidden</option>
              </select>
            </Field>
          </div>
          <div className="service-admin-notice service-admin-notice-green">
            <b>Ready to create.</b> Only stages your role can perform are included. A failed nested
            stage does not roll back successful independent stages.
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
  const [subservices, setSubservices] = useState(
    (service.subservices ?? []).join('\n') || 'Standard Package\nPremium Package',
  )
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
    subservices: splitLines(subservices),
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

  const validateStep = (index: number): string | null => {
    if (index === 0) {
      if (!name.trim()) return 'Service name is required.'
      if (!code.trim()) return 'Service code is required.'
      if (!division.trim()) return 'Division is required.'
      if (!owner.trim()) return 'Owner role is required.'
      if (!description.trim()) return 'Description is required.'
      if (!Number.isFinite(slaDays) || slaDays < 1) return 'SLA must be at least 1 day.'
      if (!fulfilmentMode.trim()) return 'Fulfillment mode is required.'
      return null
    }
    if (index === 1 && splitLines(subservices).length === 0) {
      return 'Add at least one sub-service.'
    }
    if (index === 2) {
      if (!pricingMethod.trim()) return 'Pricing method is required.'
      if (!Number.isFinite(rate) || rate < 0) return 'Base / unit price is required.'
      if (!Number.isFinite(depositPercent) || depositPercent < 0 || depositPercent > 100) {
        return 'Deposit (%) must be between 0 and 100.'
      }
      if (!Number.isFinite(taxPercent) || taxPercent < 0 || taxPercent > 100) {
        return 'Tax (%) must be between 0 and 100.'
      }
      if (
        !Number.isFinite(discountApprovalPercent) ||
        discountApprovalPercent < 0 ||
        discountApprovalPercent > 100
      ) {
        return 'Discount approval (%) must be between 0 and 100.'
      }
      return null
    }
    if (index === 3 && requestFields.length === 0) {
      return 'Select at least one request form field.'
    }
    if (index === 4 && splitLines(workflowText).length === 0) {
      return 'Add at least one workflow stage.'
    }
    if (index === 5 && selectedBranches.length === 0) {
      return 'Select at least one active branch.'
    }
    return null
  }

  const save = () => {
    for (let index = 0; index < wizardSteps.length; index += 1) {
      const validationError = validateStep(index)
      if (validationError) {
        setError(validationError)
        setStep(index)
        return
      }
    }
    setError('')
    if (!onSave) return
    onSave(buildPayload())
  }

  const next = () => {
    const validationError = validateStep(step)
    if (validationError) {
      setError(validationError)
      return
    }
    setError('')
    if (step === wizardSteps.length - 1) {
      save()
      return
    }
    setStep((current) => Math.min(wizardSteps.length - 1, current + 1))
  }

  return (
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

      {error ? <div className="service-admin-notice service-admin-notice-red">{error}</div> : null}

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
              <Field label="Service name" required>
                <input value={name} required onChange={(event) => setName(event.target.value)} />
              </Field>
              <Field label="Service code" required>
                <input value={code} required onChange={(event) => setCode(event.target.value)} />
              </Field>
              <Field label="Division" required>
                <select
                  value={division}
                  required
                  onChange={(event) => setDivision(event.target.value)}
                >
                  {divisions.map((item) => (
                    <option key={item}>{item}</option>
                  ))}
                </select>
              </Field>
              <Field label="Owner role" required>
                <select
                  value={ownerRoleId ?? ''}
                  required
                  onChange={(event) => {
                    const nextOwnerRoleId = event.target.value ? Number(event.target.value) : null
                    const selectedOwnerRole = ownerRoles.find((role) => role.id === nextOwnerRoleId)
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
            <Field label="Description" required>
              <textarea
                className="service-admin-description-textarea"
                value={description}
                required
                rows={4}
                placeholder="Describe what this service covers, who it is for, the expected delivery outcome, and any important scope notes."
                onChange={(event) => setDescription(event.target.value)}
              />
            </Field>
            <div className="service-admin-form-grid">
              <Field label="SLA (days)" required>
                <input
                  type="number"
                  min={1}
                  required
                  value={formatNumberFieldValue(slaDays)}
                  onChange={(event) => setSlaDays(parseNumberFieldValue(event.target.value))}
                />
              </Field>
              <Field label="Fulfillment mode" required>
                <select
                  value={fulfilmentMode}
                  required
                  onChange={(event) => setFulfilmentMode(event.target.value)}
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
          <Field label="Sub-services — one per line" full required>
            <textarea
              className="service-admin-wizard-textarea"
              value={subservices}
              required
              placeholder={'Standard Package\nPremium Package\nEnterprise Package'}
              onChange={(event) => setSubservices(event.target.value)}
            />
          </Field>
        ) : null}

        {step === 2 ? (
          <div className="service-admin-form-grid">
            <Field label="Pricing method" required>
              <select
                value={pricingMethod}
                required
                onChange={(event) => setPricingMethod(event.target.value)}
              >
                <option>Fixed</option>
                <option>Unit rate</option>
                <option>Area rate</option>
                <option>Percentage</option>
                <option>Custom formula</option>
              </select>
            </Field>
            <Field label="Base / unit price" required>
              <input
                type="number"
                min={0}
                required
                value={formatNumberFieldValue(rate)}
                onChange={(event) => setRate(parseNumberFieldValue(event.target.value))}
              />
            </Field>
            <Field label="Deposit (%)" required>
              <input
                type="number"
                min={0}
                max={100}
                required
                value={formatNumberFieldValue(depositPercent)}
                onChange={(event) => setDepositPercent(parseNumberFieldValue(event.target.value))}
              />
            </Field>
            <Field label="Tax (%)" required>
              <input
                type="number"
                min={0}
                max={100}
                required
                value={formatNumberFieldValue(taxPercent)}
                onChange={(event) => setTaxPercent(parseNumberFieldValue(event.target.value))}
              />
            </Field>
            <Field label="Discount approval above (%)" required>
              <input
                type="number"
                min={0}
                max={100}
                required
                value={formatNumberFieldValue(discountApprovalPercent)}
                onChange={(event) =>
                  setDiscountApprovalPercent(parseNumberFieldValue(event.target.value))
                }
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
            <div className="service-admin-check-grid">
              {requestFieldOptions.map((field) => (
                <label key={field} className="service-admin-check-option">
                  <input
                    type="checkbox"
                    checked={requestFields.includes(field)}
                    onChange={(event) =>
                      setRequestFields((current) =>
                        event.target.checked
                          ? [...current, field]
                          : current.filter((item) => item !== field),
                      )
                    }
                  />
                  {field}
                </label>
              ))}
            </div>
          </>
        ) : null}

        {step === 4 ? (
          <Field label="Workflow stages — one per line" full required>
            <textarea
              className="service-admin-wizard-textarea"
              value={workflowText}
              required
              placeholder={
                'Request Review\nTechnical Assessment\nQuotation\nApproval\nExecution\nQuality Review\nCompletion'
              }
              onChange={(event) => setWorkflowText(event.target.value)}
            />
          </Field>
        ) : null}

        {step === 5 ? (
          <>
            <Field label="Active branches" full required>
              <div className="service-admin-check-grid service-admin-check-grid--branches">
                {branchOptions.map((branch) => (
                  <label key={branch.id} className="service-admin-check-option">
                    <input
                      type="checkbox"
                      checked={selectedBranches.includes(branch.name)}
                      onChange={(event) =>
                        setSelectedBranches((current) =>
                          event.target.checked
                            ? [...current, branch.name]
                            : current.filter((item) => item !== branch.name),
                        )
                      }
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
  )
}
