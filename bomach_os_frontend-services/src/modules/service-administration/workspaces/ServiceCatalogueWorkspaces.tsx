import { IconX } from '@tabler/icons-react'
import { useState } from 'react'

import type {
  ConfigureServiceInput,
  CreateServiceWizardInput,
  PricingCalculator,
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
      className={`service-admin-config-field${full ? ' service-admin-config-field--full' : ''}`}
    >
      <span>
        {label}
        {required ? <em className="service-admin-required">*</em> : null}
      </span>
      {children}
    </label>
  )
}

export function CreateServiceWizard({
  open,
  pending,
  onClose,
  onSubmit,
}: {
  open: boolean
  pending: boolean
  onClose: () => void
  onSubmit: (input: CreateServiceWizardInput) => void
}) {
  const [step, setStep] = useState(0)
  const [maxReachedStep, setMaxReachedStep] = useState(0)
  const [name, setName] = useState('')
  const [code, setCode] = useState('')
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
            <input
              value={name}
              required
              onChange={(event) => setName(event.target.value)}
            />
          </Field>
          <Field label="Service code" required>
            <input
              value={code}
              required
              placeholder="ENG-REN"
              onChange={(event) => setCode(event.target.value)}
            />
          </Field>
          <Field label="Division" required>
            <select value={division} required onChange={(event) => setDivision(event.target.value)}>
              {divisions.map((item) => (
                <option key={item}>{item}</option>
              ))}
            </select>
          </Field>
          <Field label="Owner role" required>
            <input
              value={owner}
              required
              onChange={(event) => setOwner(event.target.value)}
            />
          </Field>
          <Field label="Description" full required>
            <textarea
              value={description}
              required
              onChange={(event) => setDescription(event.target.value)}
            />
          </Field>
          <Field label="SLA (days)" required>
            <input
              type="number"
              min={1}
              required
              value={slaDays}
              onChange={(event) => setSlaDays(Number(event.target.value))}
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
              value={rate}
              onChange={(event) => setRate(Number(event.target.value))}
            />
          </Field>
          <Field label="Deposit (%)" required>
            <input
              type="number"
              min={0}
              max={100}
              required
              value={depositPercent}
              onChange={(event) => setDepositPercent(Number(event.target.value))}
            />
          </Field>
          <Field label="Tax (%)" required>
            <input
              type="number"
              min={0}
              max={100}
              required
              value={taxPercent}
              onChange={(event) => setTaxPercent(Number(event.target.value))}
            />
          </Field>
          <Field label="Discount approval above (%)" required>
            <input
              type="number"
              min={0}
              max={100}
              required
              value={discountApprovalPercent}
              onChange={(event) => setDiscountApprovalPercent(Number(event.target.value))}
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
            <b>Ready to create.</b> The service, calculator, request form, workflow and branch
            activation will be created together.
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
}: {
  service: ServiceCatalogueItem
  calculator?: PricingCalculator
  requestForm?: ServiceRequestForm
  workflow?: ServiceWorkflow
  pending: boolean
  onClose: () => void
  onSave: (input: ConfigureServiceInput) => void
}) {
  const [name, setName] = useState(service.name)
  const [code, setCode] = useState(service.code)
  const [division, setDivision] = useState(service.division)
  const [owner, setOwner] = useState(service.owner)
  const [description, setDescription] = useState(service.description)
  const [slaDays, setSlaDays] = useState(service.slaDays ?? 5)
  const [status, setStatus] = useState(service.status)

  const subservices = service.subservices ?? []
  const requestFields =
    requestForm?.fields.map((field) => field.label) ?? service.requestFields ?? []
  const workflowStages = workflow?.stages.map((stage) => stage.name) ?? service.workflowStages ?? []

  const save = () => {
    onSave({
      id: service.id,
      name,
      code,
      division,
      owner,
      description,
      slaDays,
      status,
      subservices,
      requestFields,
      workflowStages,
    })
  }

  return (
    <ModalShell
      title={`Configure ${service.name}`}
      wide
      onClose={onClose}
      footer={
        <>
          <button type="button" className="service-admin-button" onClick={onClose}>
            Cancel
          </button>
          <button
            type="button"
            className="service-admin-button service-admin-button-primary"
            disabled={pending}
            onClick={save}
          >
            {pending ? 'Saving…' : 'Save Configuration'}
          </button>
        </>
      }
    >
      <div className="service-admin-configure-html">
        <div className="service-admin-configure-tabs" aria-label="Service configuration sections">
          <div className="service-admin-configure-tab service-admin-configure-tab--active">
            Overview
          </div>
          <div className="service-admin-configure-tab">Sub-services</div>
          <div className="service-admin-configure-tab">Pricing</div>
          <div className="service-admin-configure-tab">Request Form</div>
          <div className="service-admin-configure-tab">Workflow</div>
        </div>

        <div className="service-admin-configure-form-grid">
          <Field label="Service name">
            <input value={name} onChange={(event) => setName(event.target.value)} />
          </Field>
          <Field label="Code">
            <input value={code} onChange={(event) => setCode(event.target.value)} />
          </Field>
          <Field label="Division">
            <select value={division} onChange={(event) => setDivision(event.target.value)}>
              {divisions.map((item) => (
                <option key={item}>{item}</option>
              ))}
            </select>
          </Field>
          <Field label="Owner role">
            <input value={owner} onChange={(event) => setOwner(event.target.value)} />
          </Field>
          <Field label="Description" full>
            <textarea
              value={description}
              onChange={(event) => setDescription(event.target.value)}
            />
          </Field>
          <Field label="SLA (days)">
            <input
              type="number"
              min={1}
              value={slaDays}
              onChange={(event) => setSlaDays(Number(event.target.value))}
            />
          </Field>
          <Field label="Status">
            <select
              value={status}
              onChange={(event) => setStatus(event.target.value as typeof status)}
            >
              <option value="active">Active</option>
              <option value="draft">Draft</option>
              <option value="inactive">Paused</option>
            </select>
          </Field>
        </div>

        <div className="service-admin-configure-two-column">
          <div className="service-admin-configure-notice service-admin-configure-notice--blue">
            <b>Sub-services</b>
            <br />
            {subservices.length ? subservices.join(' · ') : 'None'}
          </div>
          <div className="service-admin-configure-notice service-admin-configure-notice--green">
            <b>Assigned calculator</b>
            <br />
            {calculator?.name ?? 'None'}
          </div>
        </div>

        <div className="service-admin-configure-notice service-admin-configure-notice--yellow">
          <b>Request fields:</b> {requestFields.join(', ')}
        </div>

        <div className="service-admin-configure-notice service-admin-configure-notice--blue">
          <b>Workflow:</b> {workflowStages.join(' → ')}
        </div>
      </div>
    </ModalShell>
  )
}
