import { IconApps, IconCopy, IconForms, IconSettings } from '@tabler/icons-react'
import { useMemo, useState } from 'react'

import type {
  PricingCalculator,
  ServiceCatalogueItem,
  ServiceRequestForm,
  ServiceWorkflow,
} from '../types/service-administration.types'
import './service-operations-prototype.css'

const divisionVisuals: Record<string, { background: string; color: string }> = {
  'Real Estate': { background: '#dbeafe', color: '#1e40af' },
  Engineering: { background: '#fef3c7', color: '#92400e' },
  'Engineering & Construction': { background: '#fef3c7', color: '#92400e' },
  Survey: { background: '#d1fae5', color: '#065f46' },
  'Land Surveying & Geospatial': { background: '#d1fae5', color: '#065f46' },
  ICT: { background: '#ccfbf1', color: '#115e59' },
  'Information Technology': { background: '#ccfbf1', color: '#115e59' },
}

function statusClass(status: string) {
  if (status.toLowerCase() === 'active') return 'prototype-pill-green'
  if (status.toLowerCase() === 'draft') return 'prototype-pill-yellow'
  return 'prototype-pill-gray'
}

export function ExactServiceCatalogue({
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
    <div className="prototype-page prototype-content">
      <div className="prototype-card">
        <div className="prototype-card-header">
          <div>
            <div className="prototype-card-title">Service Catalogue</div>
            <div className="prototype-card-subtitle">
              Configure, activate and manage Bomach services
            </div>
          </div>
        </div>

        <div className="prototype-filter-group">
          <input
            className="prototype-grow"
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

        <div className="prototype-service-grid">
          {filtered.map((service) => {
            const visual = divisionVisuals[service.division] ?? {
              background: '#edf1f6',
              color: '#566075',
            }

            return (
              <article key={service.id} className="prototype-service-card">
                <div
                  className="prototype-service-icon"
                  style={{
                    background: visual.background,
                    color: visual.color,
                  }}
                >
                  <IconApps size={18} />
                </div>
                <div className="prototype-service-name">{service.name}</div>
                <div className="prototype-row-subtitle">
                  {service.code} · {service.division}
                </div>
                <p className="prototype-service-description">{service.description}</p>
                <div className="flex flex-wrap gap-1.5">
                  <span className={`prototype-pill ${statusClass(service.status)}`}>
                    {service.status}
                  </span>
                  <span className="prototype-pill prototype-pill-gray">
                    {service.branchNames.length} branches
                  </span>
                  <span className="prototype-pill prototype-pill-gray">
                    {service.subserviceCount} sub-services
                  </span>
                </div>
                <div className="prototype-service-footer">
                  <span className="prototype-row-subtitle">{service.owner}</span>
                  <div className="flex gap-1">
                    <button
                      type="button"
                      className="prototype-button prototype-button-small"
                      onClick={() => onDuplicate(service)}
                    >
                      <IconCopy size={13} />
                      Duplicate
                    </button>
                    <button
                      type="button"
                      className="prototype-button prototype-button-small prototype-button-primary"
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

export function ExactCalculatorLibrary({
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
    <div className="prototype-page prototype-content">
      <div className="prototype-grid-2-1">
        <section className="prototype-card">
          <div className="prototype-card-header">
            <div>
              <div className="prototype-card-title">Service Calculator Library</div>
              <div className="prototype-card-subtitle">
                Reusable formulas for estimates, quotes and invoices
              </div>
            </div>
            <button
              type="button"
              className="prototype-button prototype-button-primary"
              onClick={onCreate}
            >
              New Calculator
            </button>
          </div>

          <div className="prototype-table-wrap">
            <table className="prototype-table">
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
                      <div className="prototype-row-subtitle">{calculator.code}</div>
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
                        className="prototype-button prototype-button-small"
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

        <section className="prototype-card">
          <div className="prototype-card-header">
            <div>
              <div className="prototype-card-title">Live Calculator Test</div>
              <div className="prototype-card-subtitle">{active.name}</div>
            </div>
          </div>

          {fields.map((field) => (
            <div className="prototype-field" key={field.key}>
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

          <div className="prototype-notice prototype-notice-blue">
            <b>Formula</b>
            <br />
            <code>{String(formula)}</code>
          </div>

          <div className="prototype-kpi prototype-kpi-blue">
            <div className="prototype-kpi-label">Estimated client price</div>
            <div className="prototype-kpi-value">
              {new Intl.NumberFormat('en-NG', {
                style: 'currency',
                currency: 'NGN',
                maximumFractionDigits: 0,
              }).format(estimated)}
            </div>
            <div className="prototype-kpi-subtitle">
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

export function ExactRequestFormBuilder({
  forms,
  onCreate,
}: {
  forms: ServiceRequestForm[]
  onCreate: () => void
}) {
  const [activeId, setActiveId] = useState(forms[0]?.id ?? '')
  const active = forms.find((form) => form.id === activeId) ?? forms[0]

  return (
    <div className="prototype-page prototype-content">
      <div className="prototype-card">
        <div className="prototype-card-header">
          <div>
            <div className="prototype-card-title">Request Form Builder</div>
            <div className="prototype-card-subtitle">Design service-specific intake forms</div>
          </div>
          <button
            type="button"
            className="prototype-button prototype-button-primary"
            onClick={onCreate}
          >
            New Request Form
          </button>
        </div>

        <div className="prototype-filter-group">
          <select value={activeId} onChange={(event) => setActiveId(event.target.value)}>
            {forms.map((form) => (
              <option key={form.id} value={form.id}>
                {form.name} · {form.serviceName}
              </option>
            ))}
          </select>
        </div>

        {active ? (
          <div className="prototype-builder">
            <aside className="prototype-palette">
              <div className="prototype-card-title">Field palette</div>
              <div className="prototype-card-subtitle mb-3">Add fields to the request form</div>
              {palette.map(([label]) => (
                <div key={label} className="prototype-palette-item">
                  <IconForms size={14} />
                  {label}
                </div>
              ))}
            </aside>

            <section className="prototype-canvas">
              <div className="prototype-card-title">{active.name}</div>
              <div className="prototype-card-subtitle mb-3">
                {active.serviceName} · Version {active.version}
              </div>
              {active.fields.map((field, index) => (
                <div key={field.id} className="prototype-canvas-field">
                  <span className="prototype-row-subtitle">{index + 1}</span>
                  <IconForms size={14} />
                  <div className="prototype-grow">
                    <b className="text-[9px]">{field.label}</b>
                    <div className="prototype-row-subtitle">
                      {field.type}
                      {field.required ? ' · Required' : ''}
                    </div>
                  </div>
                  <button type="button" className="prototype-button prototype-button-small">
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

export function ExactWorkflowDesigner({
  workflows,
  onCreate,
}: {
  workflows: ServiceWorkflow[]
  onCreate: () => void
}) {
  const [activeId, setActiveId] = useState(workflows[0]?.id ?? '')
  const active = workflows.find((workflow) => workflow.id === activeId) ?? workflows[0]

  return (
    <div className="prototype-page prototype-content">
      <div className="prototype-card">
        <div className="prototype-card-header">
          <div>
            <div className="prototype-card-title">Workflow Designer</div>
            <div className="prototype-card-subtitle">Configure service fulfillment automation</div>
          </div>
          <button
            type="button"
            className="prototype-button prototype-button-primary"
            onClick={onCreate}
          >
            New Workflow
          </button>
        </div>

        <div className="prototype-filter-group">
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
            <div className="prototype-life">
              {active.stages
                .slice()
                .sort((a, b) => a.order - b.order)
                .map((stage, index) => (
                  <article key={stage.id} className="prototype-step">
                    <small>{String(index + 1).padStart(2, '0')}</small>
                    <b>{stage.name}</b>
                    <span>{stage.ownerRole}</span>
                  </article>
                ))}
            </div>

            <div className="prototype-table-wrap mt-3">
              <table className="prototype-table">
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
