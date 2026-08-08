import { IconX } from '@tabler/icons-react'
import { useState } from 'react'

import { formatNumberFieldValue, parseNumberFieldValue } from '@/shared/lib/number-input'

import type {
  ConfigureServiceInput,
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

const branches = ['Enugu', 'Port Harcourt', 'Lagos', 'Abuja']

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
  onClose,
  onSubmit,
}: {
  open: boolean
  pending: boolean
  categories: ServiceCategoryOption[]
  onClose: () => void
  onSubmit: (input: CreateServiceWizardInput) => void
}) {
  const [step, setStep] = useState(0)
  const [maxReachedStep, setMaxReachedStep] = useState(0)
  const [name, setName] = useState('')
  const [code, setCode] = useState('')
  const [categoryId, setCategoryId] = useState<number>(0)
  const [division, setDivision] = useState(divisions[0] ?? '')
  const [owner, setOwner] = useState('Service Manager')
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
  const [selectedBranches, setSelectedBranches] = useState<string[]>([...branches])
  const [status, setStatus] = useState<'active' | 'draft' | 'inactive'>('draft')
  const [clientVisibility, setClientVisibility] = useState('Visible in catalogue')
  const [error, setError] = useState('')

  if (!open) return null

  const selectedCategoryId = categoryId

  const validateStep = (index: number): string | null => {
    if (index === 0) {
      if (!name.trim()) return 'Service name is required.'
      if (!code.trim()) return 'Service code is required.'
      if (!selectedCategoryId) return 'Service category is required.'
      if (!division.trim()) return 'Division is required.'
      if (!description.trim()) return 'Description is required.'
      if (!Number.isFinite(slaDays) || slaDays < 1) return 'SLA must be at least 1 day.'
      if (!fulfilmentMode.trim()) return 'Fulfillment mode is required.'
      return null
    }

    if (index === 1) {
      if (splitLines(subservices).length === 0) return 'Add at least one sub-service.'
      return null
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

    if (index === 3) {
      if (requestFields.length === 0) return 'Select at least one request form field.'
      return null
    }

    if (index === 4) {
      if (splitLines(workflow).length === 0) return 'Add at least one workflow stage.'
      return null
    }

    if (index === 5) {
      if (selectedBranches.length === 0) return 'Select at least one active branch.'
      return null
    }

    return null
  }

  const goToStep = (index: number) => {
    if (index === step) return
    if (index > maxReachedStep) {
      setError('Complete the current step before opening a later step.')
      return
    }
    setError('')
    setStep(index)
  }

  const next = () => {
    const validationError = validateStep(step)
    if (validationError) {
      setError(validationError)
      return
    }

    setError('')
    if (step === wizardSteps.length - 1) {
      onSubmit({
        name: name.trim(),
        categoryId: selectedCategoryId,
        code: code.trim(),
        division,
        description: description.trim(),
        owner: owner.trim(),
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
        workflowStages: splitLines(workflow),
      })
      return
    }

    const following = Math.min(wizardSteps.length - 1, step + 1)
    setMaxReachedStep((current) => Math.max(current, following))
    setStep(following)
  }

  const previous = () => {
    setError('')
    setStep((current) => Math.max(0, current - 1))
  }

  const handleClose = () => {
    setStep(0)
    setMaxReachedStep(0)
    setError('')
    onClose()
  }

  return (
    <ModalShell
      title="Create & Activate Service"
      wide
      variant="wizard"
      onClose={handleClose}
      footer={
        <>
          <button
            type="button"
            className="service-admin-button service-admin-wizard-nav-btn"
            disabled={step === 0 || pending}
            onClick={previous}
          >
            Previous
          </button>
          <button
            type="button"
            className="service-admin-button service-admin-button-primary service-admin-wizard-nav-btn service-admin-wizard-nav-btn--primary"
            disabled={pending}
            onClick={next}
          >
            {pending ? 'Creating…' : step === wizardSteps.length - 1 ? 'Create Service' : 'Next'}
          </button>
        </>
      }
    >
      <div className="service-admin-wizard-steps" role="tablist" aria-label="Create service steps">
        {wizardSteps.map((item, index) => {
          const isActive = index === step
          const isReached = index <= maxReachedStep
          const isComplete = index < step || (index < maxReachedStep && index !== step)

          return (
            <button
              key={item}
              type="button"
              role="tab"
              aria-selected={isActive}
              aria-disabled={!isReached}
              disabled={!isReached || pending}
              className={[
                'service-admin-wizard-step',
                isActive ? 'service-admin-wizard-step--active' : '',
                isComplete ? 'service-admin-wizard-step--complete' : '',
                isReached ? 'service-admin-wizard-step--reachable' : '',
              ]
                .filter(Boolean)
                .join(' ')}
              onClick={() => goToStep(index)}
            >
              {index + 1}. {item}
            </button>
          )
        })}
      </div>

      {error ? <div className="service-admin-notice service-admin-notice-red">{error}</div> : null}

      {step === 0 ? (
        <div className="service-admin-form-grid">
          <Field label="Service name" required>
            <input value={name} required onChange={(event) => setName(event.target.value)} />
          </Field>
          <Field label="Service code" required>
            <input
              value={code}
              required
              placeholder="ENG-REN"
              onChange={(event) => setCode(event.target.value)}
            />
          </Field>
          <Field label="Category" required>
            <select
              value={selectedCategoryId || ''}
              required
              disabled={categories.length === 0}
              onChange={(event) => setCategoryId(Number(event.target.value))}
            >
              {categories.length === 0 ? (
                <option value="">No categories available</option>
              ) : (
                <>
                  <option value="">Select a category</option>
                  {categories.map((item) => (
                    <option key={item.id} value={item.id}>
                      {categoryLabel(item.name)}
                    </option>
                  ))}
                </>
              )}
            </select>
          </Field>
          <Field label="Division" required>
            <select value={division} required onChange={(event) => setDivision(event.target.value)}>
              {divisions.map((item) => (
                <option key={item}>{item}</option>
              ))}
            </select>
          </Field>
          <Field label="Owner role">
            <input
              value={owner}
              placeholder="Assigned later when role lookup is integrated"
              onChange={(event) => setOwner(event.target.value)}
            />
          </Field>
          <Field label="Description" full required>
            <textarea
              className="service-admin-description-textarea"
              value={description}
              required
              rows={4}
              placeholder="Describe what this service covers, who it is for, and typical delivery outcomes"
              onChange={(event) => setDescription(event.target.value)}
            />
          </Field>
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
      ) : null}

      {step === 1 ? (
        <Field label="Sub-services — one per line" full required>
          <textarea
            className="service-admin-wizard-textarea"
            value={subservices}
            required
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
            value={workflow}
            required
            onChange={(event) => setWorkflow(event.target.value)}
          />
        </Field>
      ) : null}

      {step === 5 ? (
        <>
          <Field label="Active branches" full required>
            <div className="service-admin-check-grid service-admin-check-grid--branches">
              {branches.map((branch) => (
                <label key={branch} className="service-admin-check-option">
                  <input
                    type="checkbox"
                    checked={selectedBranches.includes(branch)}
                    onChange={(event) =>
                      setSelectedBranches((current) =>
                        event.target.checked
                          ? [...current, branch]
                          : current.filter((item) => item !== branch),
                      )
                    }
                  />
                  {branch}
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
            <b>Ready to create.</b> Your service will be saved as a draft with the sub-services and
            request form from this wizard. Pricing, workflow, and branch availability can be
            finished from the service catalogue afterward.
          </div>
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
  pending,
  onClose,
  onSave,
  readOnly = false,
}: {
  service: ServiceCatalogueItem
  calculator?: PricingCalculator
  requestForm?: ServiceRequestForm
  workflow?: ServiceWorkflow
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
    service.branchNames.length ? [...service.branchNames] : [...branches],
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
      title={`Configure ${service.name}`}
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
          View-only access. Your role can inspect this service but cannot change its configuration.
        </div>
      ) : null}

      <fieldset disabled={readOnly} style={{ border: 0, padding: 0, margin: 0, minWidth: 0 }}>
        {step === 0 ? (
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
              <input value={owner} required onChange={(event) => setOwner(event.target.value)} />
            </Field>
            <Field label="Description" full required>
              <textarea
                className="service-admin-description-textarea"
                value={description}
                required
                rows={4}
                placeholder="Describe what this service covers, who it is for, and typical delivery outcomes"
                onChange={(event) => setDescription(event.target.value)}
              />
            </Field>
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
        ) : null}

        {step === 1 ? (
          <Field label="Sub-services — one per line" full required>
            <textarea
              className="service-admin-wizard-textarea"
              value={subservices}
              required
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
              onChange={(event) => setWorkflowText(event.target.value)}
            />
          </Field>
        ) : null}

        {step === 5 ? (
          <>
            <Field label="Active branches" full required>
              <div className="service-admin-check-grid service-admin-check-grid--branches">
                {branches.map((branch) => (
                  <label key={branch} className="service-admin-check-option">
                    <input
                      type="checkbox"
                      checked={selectedBranches.includes(branch)}
                      onChange={(event) =>
                        setSelectedBranches((current) =>
                          event.target.checked
                            ? [...current, branch]
                            : current.filter((item) => item !== branch),
                        )
                      }
                    />
                    {branch}
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
