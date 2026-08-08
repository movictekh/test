import { IconApps, IconCopy } from '@tabler/icons-react'
import { useMemo, useState } from 'react'

import type {
  PricingCalculator,
  RequestFormField,
  ServiceCatalogueItem,
  SaveRequestFormInput,
  ServiceRequestForm,
} from '../types/service-administration.types'
import { formatNumberFieldValue, parseNumberFieldValue } from '@/shared/lib/number-input'
import { formatCurrency } from '@/shared/lib/formatters'

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
  configureLabel = 'Configure',
  onCreate,
  onBranchAvailability,
  onDuplicate,
}: {
  services: ServiceCatalogueItem[]
  onConfigure?: (service: ServiceCatalogueItem) => void
  configureLabel?: 'Configure' | 'View'
  onCreate?: () => void
  onBranchAvailability?: () => void
  onDuplicate?: (service: ServiceCatalogueItem) => void
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
      <div className="service-admin-card service-admin-catalog-shell">
        <div className="service-admin-filter-group service-admin-catalog-filter">
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
          <span className="service-admin-grow" />
          {onBranchAvailability ? (
            <button type="button" className="service-admin-button" onClick={onBranchAvailability}>
              Branch Availability
            </button>
          ) : null}
          {onCreate ? (
            <button
              type="button"
              className="service-admin-button service-admin-button-primary"
              onClick={onCreate}
            >
              Create Service
            </button>
          ) : null}
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
                <p className="service-admin-service-description">{service.description}</p>
                <div className="service-admin-row-subtitle service-admin-service-meta">
                  {service.code} · {service.subserviceCount} sub-services · {service.slaDays ?? '—'}
                  d SLA
                </div>
                <div className="service-admin-service-footer">
                  <span className={`service-admin-pill ${statusClass(service.status)}`}>
                    {service.status}
                  </span>
                  <div className="flex gap-1">
                    {onConfigure ? (
                      <button
                        type="button"
                        className="service-admin-button service-admin-button-small"
                        onClick={() => onConfigure(service)}
                      >
                        {configureLabel}
                      </button>
                    ) : null}
                    {onDuplicate ? (
                      <button
                        type="button"
                        className="service-admin-button service-admin-button-small"
                        aria-label="Duplicate service"
                        onClick={() => onDuplicate(service)}
                      >
                        <IconCopy size={13} />
                      </button>
                    ) : null}
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
  onCreate?: () => void
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
            {onCreate ? (
              <button
                type="button"
                className="service-admin-button service-admin-button-primary"
                onClick={onCreate}
              >
                New Calculator
              </button>
            ) : null}
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
                {calculators.map((calculator) => {
                  const isActive = calculator.id === active.id

                  return (
                    <tr
                      key={calculator.id}
                      className={isActive ? 'service-admin-table-row--active' : undefined}
                      aria-selected={isActive}
                    >
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
                          className={`service-admin-button service-admin-button-small${
                            isActive ? 'service-admin-button-primary' : ''
                          }`}
                          aria-pressed={isActive}
                          onClick={() => {
                            setActiveId(calculator.id)
                            setInputs({})
                          }}
                        >
                          Test
                        </button>
                      </td>
                    </tr>
                  )
                })}
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
                value={formatNumberFieldValue(inputs[field.key] ?? field.value)}
                onChange={(event) =>
                  setInputs((current) => ({
                    ...current,
                    [field.key]: parseNumberFieldValue(event.target.value),
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
            <div className="service-admin-kpi-value">{formatCurrency(estimated)}</div>
            <div className="service-admin-kpi-subtitle">
              Tax, deposit and approval rules apply as configured.
            </div>
          </div>
        </section>
      </div>
    </div>
  )
}

const requestBuilderPalette: {
  label: string
  type: RequestFormField['type']
}[] = [
  { label: 'Text Field', type: 'text' },
  { label: 'Number Field', type: 'number' },
  { label: 'Dropdown', type: 'select' },
  { label: 'Date Field', type: 'date' },
  { label: 'File Upload', type: 'file' },
  { label: 'Consent Checkbox', type: 'checkbox' },
  { label: 'Location', type: 'text' },
  { label: 'Client Identity', type: 'text' },
  { label: 'Budget Range', type: 'number' },
]

export function RequestFormBuilderScreen({
  forms,
  onSave,
}: {
  forms: ServiceRequestForm[]
  onSave?: (input: SaveRequestFormInput) => void
}) {
  const canEdit = Boolean(onSave)
  const [activeId, setActiveId] = useState(forms[0]?.id ?? '')
  const active = forms.find((form) => form.id === activeId) ?? forms[0]
  const [fields, setFields] = useState<RequestFormField[]>(active?.fields ?? [])
  const [editingIndex, setEditingIndex] = useState<number | null>(null)

  const selectForm = (id: string) => {
    setActiveId(id)
    const next = forms.find((form) => form.id === id)
    setFields(next?.fields ?? [])
    setEditingIndex(null)
  }

  if (!active) return null
  const editingField = editingIndex === null ? undefined : fields[editingIndex]

  return (
    <div className="service-admin-page service-admin-content">
      <div className="service-admin-request-builder">
        <aside className="service-admin-request-palette">
          <h2>Field Palette</h2>
          <div className="service-admin-request-palette-list">
            {requestBuilderPalette.map((item) => (
              <button
                key={item.label}
                type="button"
                disabled={!canEdit}
                onClick={() =>
                  setFields((current) => [
                    ...current,
                    {
                      id: `field-${Date.now()}`,
                      label: item.label,
                      key: item.label.toLowerCase().replace(/[^a-z0-9]+/g, '_'),
                      type: item.type,
                      required: false,
                    },
                  ])
                }
              >
                <span>+</span>
                {item.label}
              </button>
            ))}
          </div>
          {onSave ? (
            <button
              type="button"
              className="service-admin-request-save"
              onClick={() =>
                onSave({
                  id: active.id,
                  name: active.name,
                  serviceId: active.serviceId,
                  status: active.status,
                  fields,
                })
              }
            >
              Save Form
            </button>
          ) : null}
        </aside>

        <section className="service-admin-request-canvas">
          <div className="service-admin-request-canvas-header">
            <div>
              <h2>Service Request Form Builder</h2>
              <p>Create the exact information required per service</p>
            </div>
            <select value={activeId} onChange={(event) => selectForm(event.target.value)}>
              {forms.map((form) => (
                <option key={form.id} value={form.id}>
                  {form.serviceName}
                </option>
              ))}
            </select>
          </div>

          <div className="service-admin-request-field-list">
            {fields.map((field, index) => (
              <article key={field.id} className="service-admin-request-field-row">
                <span className="service-admin-request-drag">::</span>
                <div className="service-admin-grow">
                  <b>{field.label}</b>
                  <small>
                    {field.type} · {field.required ? 'Required' : 'Optional'}
                  </small>
                </div>
                {canEdit ? (
                  <button type="button" onClick={() => setEditingIndex(index)}>
                    Edit
                  </button>
                ) : null}
                {canEdit ? (
                  <button
                    type="button"
                    onClick={() =>
                      setFields((current) => current.filter((_, itemIndex) => itemIndex !== index))
                    }
                  >
                    Delete
                  </button>
                ) : null}
              </article>
            ))}
          </div>
        </section>
      </div>

      {canEdit && editingField && editingIndex !== null ? (
        <div
          className="service-admin-editor-backdrop"
          role="presentation"
          onMouseDown={() => setEditingIndex(null)}
        >
          <section
            className="service-admin-field-editor-modal"
            role="dialog"
            aria-modal="true"
            aria-label={`Edit ${editingField.label}`}
            onMouseDown={(event) => event.stopPropagation()}
          >
            <header>
              <h2>Edit Field</h2>
              <button type="button" onClick={() => setEditingIndex(null)}>
                ×
              </button>
            </header>
            <div className="service-admin-field-editor-body">
              <label>
                <span>Label</span>
                <input
                  value={editingField.label}
                  onChange={(event) =>
                    setFields((current) =>
                      current.map((item, index) =>
                        index === editingIndex ? { ...item, label: event.target.value } : item,
                      ),
                    )
                  }
                />
              </label>
              <label>
                <span>Type</span>
                <select
                  value={editingField.type}
                  onChange={(event) =>
                    setFields((current) =>
                      current.map((item, index) =>
                        index === editingIndex
                          ? { ...item, type: event.target.value as RequestFormField['type'] }
                          : item,
                      ),
                    )
                  }
                >
                  <option value="text">Text</option>
                  <option value="textarea">Long text</option>
                  <option value="number">Number</option>
                  <option value="date">Date</option>
                  <option value="select">Dropdown</option>
                  <option value="file">File upload</option>
                  <option value="checkbox">Checkbox</option>
                </select>
              </label>
              <label className="service-admin-field-editor-check">
                <input
                  type="checkbox"
                  checked={editingField.required}
                  onChange={(event) =>
                    setFields((current) =>
                      current.map((item, index) =>
                        index === editingIndex ? { ...item, required: event.target.checked } : item,
                      ),
                    )
                  }
                />
                Required field
              </label>
            </div>
            <footer>
              <button type="button" onClick={() => setEditingIndex(null)}>
                Done
              </button>
            </footer>
          </section>
        </div>
      ) : null}
    </div>
  )
}
