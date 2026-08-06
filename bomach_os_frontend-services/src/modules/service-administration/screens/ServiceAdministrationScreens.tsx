import { IconApps, IconCopy, IconForms, IconSettings } from '@tabler/icons-react'
import { useMemo, useState } from 'react'

import type {
  PricingCalculator,
  ServiceCatalogueItem,
  ServiceRequestForm,
  ServiceWorkflow,
} from '../types/service-administration.types'
import '../styles/service-administration.css'

const divisionClassNames: Record<string, string> = {
  'Real Estate': 'service-admin-service-icon--real-estate',
  Engineering: 'service-admin-service-icon--engineering',
  'Engineering & Construction': 'service-admin-service-icon--engineering',
  Survey: 'service-admin-service-icon--survey',
  'Land Surveying & Geospatial': 'service-admin-service-icon--survey',
  ICT: 'service-admin-service-icon--ict',
  'Information Technology': 'service-admin-service-icon--ict',
}

function statusClass(status: string) {
  if (status.toLowerCase() === 'active') return 'service-admin-pill-green'
  if (status.toLowerCase() === 'draft') return 'service-admin-pill-yellow'
  return 'service-admin-pill-gray'
}

export function ServiceCatalogueScreen({
  services,
  onConfigure,
  onDuplicate,
}: {
  services: ServiceCatalogueItem[]
  onConfigure: (service: ServiceCatalogueItem) => void
  onDuplicate: (service: ServiceCatalogueItem) => void
}) {
  const [query, setQuery] = useState('')
  const [division, setDivision] = useState('')
  const [status, setStatus] = useState('')

  const divisions = useMemo(
    () => Array.from(new Set(services.map((service) => service.division))),
    [services],
  )

  const filtered = services.filter((service) => {
    const text = `${service.name} ${service.description}`.toLowerCase()
    return (
      (!query || text.includes(query.toLowerCase())) &&
      (!division || service.division === division) &&
      (!status || service.status === status)
    )
  })

  return (
    <div className="service-admin-page service-admin-content">
      <div className="service-admin-card">
        <div className="service-admin-card-header">
          <div>
            <div className="service-admin-card-title">Service Catalogue</div>
            <div className="service-admin-card-subtitle">
              Configure, activate and manage Bomach services
            </div>
          </div>
        </div>

        <div className="service-admin-filter-group">
          <input
            className="service-admin-grow"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search services..."
          />
          <select value={division} onChange={(event) => setDivision(event.target.value)}>
            <option value="">All divisions</option>
            {divisions.map((item) => (
              <option key={item}>{item}</option>
            ))}
          </select>
          <select value={status} onChange={(event) => setStatus(event.target.value)}>
            <option value="">All statuses</option>
            <option value="active">Active</option>
            <option value="draft">Draft</option>
            <option value="inactive">Inactive</option>
          </select>
        </div>

        <div className="service-admin-service-grid">
          {filtered.map((service) => {
            const divisionClassName =
              divisionClassNames[service.division] ?? 'service-admin-service-icon--default'

            return (
              <article key={service.id} className="service-admin-service-card">
                <div className={`service-admin-service-icon ${divisionClassName}`}>
                  <IconApps size={18} />
                </div>
                <div className="service-admin-service-name">{service.name}</div>
                <div className="service-admin-row-subtitle">
                  {service.code} · {service.division}
                </div>
                <p className="service-admin-service-description">{service.description}</p>
                <div className="flex flex-wrap gap-1.5">
                  <span className={`service-admin-pill ${statusClass(service.status)}`}>
                    {service.status}
                  </span>
                  <span className="service-admin-pill service-admin-pill-gray">
                    {service.branchNames.length} branches
                  </span>
                  <span className="service-admin-pill service-admin-pill-gray">
                    {service.subserviceCount} sub-services
                  </span>
                </div>
                <div className="service-admin-service-footer">
                  <span className="service-admin-row-subtitle">{service.owner}</span>
                  <div className="flex gap-1">
                    <button
                      type="button"
                      className="service-admin-button service-admin-button-small"
                      onClick={() => onDuplicate(service)}
                    >
                      <IconCopy size={13} />
                      Duplicate
                    </button>
                    <button
                      type="button"
                      className="service-admin-button service-admin-button-small service-admin-button-primary"
                      onClick={() => onConfigure(service)}
                    >
                      <IconSettings size={13} />
                      Configure
                    </button>
                  </div>
                </div>
              </article>
            )
          })}
        </div>
      </div>
    </div>
  )
}

function calculatorNumericFields(calculator: PricingCalculator) {
  return calculator.variables
    .filter((variable) => variable.type === 'number')
    .map((variable, index) => ({
      key: variable.key,
      label: variable.label,
      value: index === 0 ? Math.max(1, calculator.sampleTotal / 1000) : 1,
    }))
}

export function CalculatorLibraryScreen({
  calculators,
  onCreate,
}: {
  calculators: PricingCalculator[]
  onCreate: () => void
}) {
  const [activeId, setActiveId] = useState(calculators[0]?.id ?? '')
  const active = calculators.find((calculator) => calculator.id === activeId) ?? calculators[0]
  const [inputs, setInputs] = useState<Record<string, number>>({})

  if (!active) return null

  const fields = calculatorNumericFields(active)
  const estimated =
    Object.keys(inputs).length === 0
      ? active.sampleTotal
      : Object.values(inputs).reduce((total, value) => total + Number(value || 0), 0)

  const formula =
    active.charges.find((charge) => charge.kind === 'formula')?.value ??
    active.charges.map((charge) => charge.label).join(' + ')

  return (
    <div className="service-admin-page service-admin-content">
      <div className="service-admin-grid-2-1">
        <section className="service-admin-card">
          <div className="service-admin-card-header">
            <div>
              <div className="service-admin-card-title">Service Calculator Library</div>
              <div className="service-admin-card-subtitle">
                Reusable formulas for estimates, quotes and invoices
              </div>
            </div>
            <button
              type="button"
              className="service-admin-button service-admin-button-primary"
              onClick={onCreate}
            >
              New Calculator
            </button>
          </div>

          <div className="service-admin-table-wrap">
            <table className="service-admin-table">
              <thead>
                <tr>
                  <th>Calculator</th>
                  <th>Service</th>
                  <th>Template</th>
                  <th>Fields</th>
                  <th>Deposit</th>
                  <th>Approval</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {calculators.map((calculator) => (
                  <tr key={calculator.id}>
                    <td>
                      <b>{calculator.name}</b>
                      <div className="service-admin-row-subtitle">{calculator.code}</div>
                    </td>
                    <td>{calculator.serviceName}</td>
                    <td>
                      {calculator.charges.some((charge) => charge.kind === 'formula')
                        ? 'Formula'
                        : calculator.charges.some((charge) => charge.kind === 'percentage')
                          ? 'Percentage'
                          : 'Fixed'}
                    </td>
                    <td>{calculator.variables.length}</td>
                    <td>
                      {calculator.charges.find((charge) =>
                        charge.label.toLowerCase().includes('deposit'),
                      )?.value ?? '—'}
                    </td>
                    <td>
                      &gt;{' '}
                      {calculator.charges.find((charge) =>
                        charge.label.toLowerCase().includes('approval'),
                      )?.value ?? '—'}
                    </td>
                    <td>
                      <button
                        type="button"
                        className="service-admin-button service-admin-button-small"
                        onClick={() => {
                          setActiveId(calculator.id)
                          setInputs({})
                        }}
                      >
                        Test
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <section className="service-admin-card">
          <div className="service-admin-card-header">
            <div>
              <div className="service-admin-card-title">Live Calculator Test</div>
              <div className="service-admin-card-subtitle">{active.name}</div>
            </div>
          </div>

          {fields.map((field) => (
            <div className="service-admin-field" key={field.key}>
              <label>{field.label}</label>
              <input
                type="number"
                value={inputs[field.key] ?? field.value}
                onChange={(event) =>
                  setInputs((current) => ({
                    ...current,
                    [field.key]: Number(event.target.value),
                  }))
                }
              />
            </div>
          ))}

          <div className="service-admin-notice service-admin-notice-blue">
            <b>Formula</b>
            <br />
            <code>{String(formula)}</code>
          </div>

          <div className="service-admin-kpi service-admin-kpi-blue">
            <div className="service-admin-kpi-label">Estimated client price</div>
            <div className="service-admin-kpi-value">
              {new Intl.NumberFormat('en-NG', {
                style: 'currency',
                currency: 'NGN',
                maximumFractionDigits: 0,
              }).format(estimated)}
            </div>
            <div className="service-admin-kpi-subtitle">
              Tax, deposit and approval rules apply as configured.
            </div>
          </div>
        </section>
      </div>
    </div>
  )
}

const palette = [
  ['Short text', 'text'],
  ['Long text', 'textarea'],
  ['Number', 'number'],
  ['Date', 'date'],
  ['Select', 'select'],
  ['File upload', 'file'],
  ['Checkbox', 'checkbox'],
] as const

export function RequestFormBuilderScreen({
  forms,
  onCreate,
}: {
  forms: ServiceRequestForm[]
  onCreate: () => void
}) {
  const [activeId, setActiveId] = useState(forms[0]?.id ?? '')
  const active = forms.find((form) => form.id === activeId) ?? forms[0]

  return (
    <div className="service-admin-page service-admin-content">
      <div className="service-admin-card">
        <div className="service-admin-card-header">
          <div>
            <div className="service-admin-card-title">Request Form Builder</div>
            <div className="service-admin-card-subtitle">Design service-specific intake forms</div>
          </div>
          <button
            type="button"
            className="service-admin-button service-admin-button-primary"
            onClick={onCreate}
          >
            New Request Form
          </button>
        </div>

        <div className="service-admin-filter-group">
          <select value={activeId} onChange={(event) => setActiveId(event.target.value)}>
            {forms.map((form) => (
              <option key={form.id} value={form.id}>
                {form.name} · {form.serviceName}
              </option>
            ))}
          </select>
        </div>

        {active ? (
          <div className="service-admin-builder">
            <aside className="service-admin-palette">
              <div className="service-admin-card-title">Field palette</div>
              <div className="service-admin-card-subtitle mb-3">Add fields to the request form</div>
              {palette.map(([label]) => (
                <div key={label} className="service-admin-palette-item">
                  <IconForms size={14} />
                  {label}
                </div>
              ))}
            </aside>

            <section className="service-admin-canvas">
              <div className="service-admin-card-title">{active.name}</div>
              <div className="service-admin-card-subtitle mb-3">
                {active.serviceName} · Version {active.version}
              </div>
              {active.fields.map((field, index) => (
                <div key={field.id} className="service-admin-canvas-field">
                  <span className="service-admin-row-subtitle">{index + 1}</span>
                  <IconForms size={14} />
                  <div className="service-admin-grow">
                    <b className="text-[9px]">{field.label}</b>
                    <div className="service-admin-row-subtitle">
                      {field.type}
                      {field.required ? ' · Required' : ''}
                    </div>
                  </div>
                  <button type="button" className="service-admin-button service-admin-button-small">
                    Configure
                  </button>
                </div>
              ))}
            </section>
          </div>
        ) : null}
      </div>
    </div>
  )
}

export function WorkflowDesignerScreen({
  workflows,
  onCreate,
}: {
  workflows: ServiceWorkflow[]
  onCreate: () => void
}) {
  const [activeId, setActiveId] = useState(workflows[0]?.id ?? '')
  const active = workflows.find((workflow) => workflow.id === activeId) ?? workflows[0]

  return (
    <div className="service-admin-page service-admin-content">
      <div className="service-admin-card">
        <div className="service-admin-card-header">
          <div>
            <div className="service-admin-card-title">Workflow Designer</div>
            <div className="service-admin-card-subtitle">
              Configure service fulfillment automation
            </div>
          </div>
          <button
            type="button"
            className="service-admin-button service-admin-button-primary"
            onClick={onCreate}
          >
            New Workflow
          </button>
        </div>

        <div className="service-admin-filter-group">
          <select value={activeId} onChange={(event) => setActiveId(event.target.value)}>
            {workflows.map((workflow) => (
              <option key={workflow.id} value={workflow.id}>
                {workflow.name} · {workflow.serviceName}
              </option>
            ))}
          </select>
        </div>

        {active ? (
          <>
            <div className="service-admin-life">
              {active.stages
                .slice()
                .sort((a, b) => a.order - b.order)
                .map((stage, index) => (
                  <article key={stage.id} className="service-admin-step">
                    <small>{String(index + 1).padStart(2, '0')}</small>
                    <b>{stage.name}</b>
                    <span>{stage.ownerRole}</span>
                  </article>
                ))}
            </div>

            <div className="service-admin-table-wrap mt-3">
              <table className="service-admin-table">
                <thead>
                  <tr>
                    <th>Stage</th>
                    <th>Owner</th>
                    <th>SLA</th>
                    <th>Evidence</th>
                    <th>Approval</th>
                    <th>Client visible</th>
                  </tr>
                </thead>
                <tbody>
                  {active.stages.map((stage) => (
                    <tr key={stage.id}>
                      <td>
                        <b>
                          {stage.order}. {stage.name}
                        </b>
                      </td>
                      <td>{stage.ownerRole}</td>
                      <td>{stage.slaHours} hours</td>
                      <td>{stage.requiresEvidence ? 'Yes' : 'No'}</td>
                      <td>{stage.requiresApproval ? 'Yes' : 'No'}</td>
                      <td>{stage.clientVisible ? 'Yes' : 'No'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        ) : null}
      </div>
    </div>
  )
}
