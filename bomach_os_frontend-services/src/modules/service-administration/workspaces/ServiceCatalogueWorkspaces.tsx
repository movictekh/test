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
  children,
  footer,
  onClose,
}: {
  title: string
  wide?: boolean
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
        className={`service-admin-modal ${wide ? 'service-admin-modal--wide' : ''}`}
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
}: {
  label: string
  children: React.ReactNode
  full?: boolean
}) {
  return (
    <div className={`f ${full ? 'full' : ''}`}>
      <label>{label}</label>
      {children}
    </div>
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
  const [error, setError] = useState('')

  if (!open) return null

  const next = () => {
    if (step === 0 && (!name.trim() || !code.trim())) {
      setError('Service name and code are required.')
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
    setStep((current) => Math.min(wizardSteps.length - 1, current + 1))
  }

  return (
    <ModalShell
      title="Create & Activate Service"
      wide
      onClose={onClose}
      footer={
        <>
          <button type="button" className="service-admin-button" onClick={onClose}>
            Cancel
          </button>
          <button
            type="button"
            className="service-admin-button"
            disabled={step === 0}
            onClick={() => setStep((current) => Math.max(0, current - 1))}
          >
            Previous
          </button>
          <button
            type="button"
            className="service-admin-button service-admin-button-primary"
            disabled={pending}
            onClick={next}
          >
            {pending ? 'Creating…' : step === wizardSteps.length - 1 ? 'Create Service' : 'Next'}
          </button>
        </>
      }
    >
      <div className="service-admin-wizard-steps">
        {wizardSteps.map((item, index) => (
          <div
            key={item}
            className={`service-admin-wizard-step ${
              index === step ? 'service-admin-wizard-step--active' : ''
            }`}
          >
            {index + 1}. {item}
          </div>
        ))}
      </div>

      {error ? <div className="service-admin-notice service-admin-notice-red">{error}</div> : null}

      {step === 0 ? (
        <div className="service-admin-form-grid">
          <Field label="Service name">
            <input value={name} onChange={(event) => setName(event.target.value)} />
          </Field>
          <Field label="Service code">
            <input
              value={code}
              placeholder="ENG-REN"
              onChange={(event) => setCode(event.target.value)}
            />
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
          <Field label="Fulfillment mode">
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
      ) : null}

      {step === 1 ? (
        <Field label="Sub-services — one per line" full>
          <textarea
            className="service-admin-wizard-textarea"
            value={subservices}
            onChange={(event) => setSubservices(event.target.value)}
          />
        </Field>
      ) : null}

      {step === 2 ? (
        <div className="service-admin-form-grid">
          <Field label="Pricing method">
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
          <Field label="Base / unit price">
            <input
              type="number"
              value={rate}
              onChange={(event) => setRate(Number(event.target.value))}
            />
          </Field>
          <Field label="Deposit (%)">
            <input
              type="number"
              value={depositPercent}
              onChange={(event) => setDepositPercent(Number(event.target.value))}
            />
          </Field>
          <Field label="Tax (%)">
            <input
              type="number"
              value={taxPercent}
              onChange={(event) => setTaxPercent(Number(event.target.value))}
            />
          </Field>
          <Field label="Discount approval above (%)">
            <input
              type="number"
              value={discountApprovalPercent}
              onChange={(event) => setDiscountApprovalPercent(Number(event.target.value))}
            />
          </Field>
        </div>
      ) : null}

      {step === 3 ? (
        <>
          <div className="service-admin-notice service-admin-notice-blue">
            Select information required from clients when they submit this service request.
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
        <Field label="Workflow stages — one per line" full>
          <textarea
            className="service-admin-wizard-textarea"
            value={workflow}
            onChange={(event) => setWorkflow(event.target.value)}
          />
        </Field>
      ) : null}

      {step === 5 ? (
        <>
          <div className="service-admin-notice service-admin-notice-green">
            Review branch availability and choose the initial publication state.
          </div>
          <div className="service-admin-check-grid">
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
          <div className="service-admin-form-grid service-admin-publish-grid">
            <Field label="Publication status">
              <select
                value={status}
                onChange={(event) => setStatus(event.target.value as typeof status)}
              >
                <option value="draft">Draft</option>
                <option value="active">Active</option>
                <option value="inactive">Paused</option>
              </select>
            </Field>
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
