import { IconApps, IconCopy } from '@tabler/icons-react'
import { useEffect, useMemo, useRef, useState } from 'react'

import { AccessLockIcon } from '@/shared/ui/module-controls'
import type {
  PricingCalculator,
  PricingType,
  RequestFieldTypeOption,
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
  totalCount,
  query,
  division,
  status,
  page,
  pageSize,
  onFiltersChange,
  onPageChange,
  onConfigure,
  configureLabel = 'Configure',
  onCreate,
  createDisabled = false,
  onBranchAvailability,
  branchAvailabilityDisabled = false,
  onDuplicate,
}: {
  services: ServiceCatalogueItem[]
  totalCount: number
  query: string
  division: string
  status: string
  page: number
  pageSize: number
  onFiltersChange: (filters: { query: string; division: string; status: string }) => void
  onPageChange: (page: number) => void
  onConfigure?: ((service: ServiceCatalogueItem) => void) | undefined
  configureLabel?: 'Configure' | 'View'
  onCreate?: (() => void) | undefined
  createDisabled?: boolean
  onBranchAvailability?: (() => void) | undefined
  branchAvailabilityDisabled?: boolean
  onDuplicate?: ((service: ServiceCatalogueItem) => void) | undefined
}) {
  const hasActiveFilters = query.trim().length > 0 || division.length > 0 || status.length > 0
  const divisions = useMemo(
    () => Array.from(new Set(services.map((service) => service.division))),
    [services],
  )
  const pageCount = Math.max(1, Math.ceil(totalCount / pageSize))
  const [searchDraft, setSearchDraft] = useState(query)
  const [syncedQuery, setSyncedQuery] = useState(query)
  const onFiltersChangeRef = useRef(onFiltersChange)
  const divisionRef = useRef(division)
  const statusRef = useRef(status)

  if (query !== syncedQuery) {
    setSyncedQuery(query)
    setSearchDraft(query)
  }

  useEffect(() => {
    onFiltersChangeRef.current = onFiltersChange
  }, [onFiltersChange])

  useEffect(() => {
    divisionRef.current = division
    statusRef.current = status
  }, [division, status])

  useEffect(() => {
    if (searchDraft === query) return

    const timeoutId = window.setTimeout(() => {
      onFiltersChangeRef.current({
        query: searchDraft,
        division: divisionRef.current,
        status: statusRef.current,
      })
    }, 350)

    return () => window.clearTimeout(timeoutId)
  }, [searchDraft, query])

  const recordCountLabel = `${totalCount} service${totalCount === 1 ? '' : 's'}`

  return (
    <div className="service-admin-page service-admin-content">
      <div className="service-admin-card service-admin-catalog-shell">
        <div className="service-admin-filter-group service-admin-catalog-filter">
          <input
            className="service-admin-grow"
            value={searchDraft}
            onChange={(event) => setSearchDraft(event.target.value)}
            onKeyDown={(event) => {
              if (event.key !== 'Enter') return
              event.preventDefault()
              if (searchDraft === query) return
              onFiltersChange({ query: searchDraft, division, status })
            }}
            placeholder="Search services..."
          />
          <select
            value={division}
            onChange={(event) =>
              onFiltersChange({ query: searchDraft, division: event.target.value, status })
            }
          >
            <option value="">All divisions</option>
            {divisions.map((item) => (
              <option key={item}>{item}</option>
            ))}
          </select>
          <select
            value={status}
            onChange={(event) =>
              onFiltersChange({ query: searchDraft, division, status: event.target.value })
            }
          >
            <option value="">All statuses</option>
            <option value="active">Active</option>
            <option value="draft">Draft</option>
            <option value="inactive">Inactive</option>
          </select>
          <span className="service-admin-grow" />
          <button
            type="button"
            className="service-admin-button"
            disabled={branchAvailabilityDisabled || !onBranchAvailability}
            title={
              branchAvailabilityDisabled
                ? 'You do not have permission to view branch availability'
                : undefined
            }
            onClick={() => onBranchAvailability?.()}
          >
            <AccessLockIcon show={branchAvailabilityDisabled} />
            Branch Availability
          </button>
          <button
            type="button"
            className="service-admin-button service-admin-button-primary"
            disabled={createDisabled || !onCreate}
            title={createDisabled ? 'You do not have permission to create services' : undefined}
            onClick={() => onCreate?.()}
          >
            <AccessLockIcon show={createDisabled} />
            Create Service
          </button>
        </div>

        <div className="service-admin-service-grid">
          {services.length === 0 ? (
            <section className="service-admin-card col-span-full border-dashed p-6 sm:p-8">
              <div className="mx-auto max-w-xl text-center">
                <div className="service-admin-card-title">
                  {hasActiveFilters
                    ? 'No services match the current filters'
                    : 'No services in the catalogue yet'}
                </div>
                <div className="service-admin-card-subtitle mt-1">
                  {hasActiveFilters
                    ? 'Try clearing or adjusting the search and filter settings to see more services.'
                    : 'Service cards will appear here after the first Service is created. You can still search, filter, review branch availability, and start the setup flow from this page.'}
                </div>
                <div className="mt-4 flex flex-wrap justify-center gap-2">
                  {hasActiveFilters ? (
                    <button
                      type="button"
                      className="service-admin-button service-admin-button-primary"
                      onClick={() => onFiltersChange({ query: '', division: '', status: '' })}
                    >
                      Clear filters
                    </button>
                  ) : (
                    <button
                      type="button"
                      className="service-admin-button service-admin-button-primary"
                      disabled={createDisabled || !onCreate}
                      title={
                        createDisabled ? 'You do not have permission to create services' : undefined
                      }
                      onClick={() => onCreate?.()}
                    >
                      <AccessLockIcon show={createDisabled} />
                      Create first Service
                    </button>
                  )}
                  <button
                    type="button"
                    className="service-admin-button"
                    disabled={branchAvailabilityDisabled || !onBranchAvailability}
                    title={
                      branchAvailabilityDisabled
                        ? 'You do not have permission to view branch availability'
                        : undefined
                    }
                    onClick={() => onBranchAvailability?.()}
                  >
                    <AccessLockIcon show={branchAvailabilityDisabled} />
                    Branch Availability
                  </button>
                </div>
              </div>
            </section>
          ) : null}

          {services.map((service) => {
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
                    <button
                      type="button"
                      className="service-admin-button service-admin-button-small"
                      disabled={!onConfigure}
                      title={
                        !onConfigure ? 'You do not have permission to view this service' : undefined
                      }
                      onClick={() => onConfigure?.(service)}
                    >
                      <AccessLockIcon show={!onConfigure} size={11} />
                      {configureLabel}
                    </button>
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

        <div className="service-admin-table-pagination">
          <div className="service-admin-table-pagination-summary">
            <span className="service-admin-table-pagination-count">{recordCountLabel}</span>
            <span className="service-admin-table-pagination-divider" aria-hidden="true" />
            <span>
              Page <b>{page}</b> of <b>{pageCount}</b>
            </span>
          </div>
          <div className="service-admin-table-pagination-actions">
            <button
              type="button"
              className="service-admin-button"
              disabled={page <= 1}
              onClick={() => onPageChange(page - 1)}
            >
              Previous
            </button>
            <button
              type="button"
              className="service-admin-button"
              disabled={page >= pageCount}
              onClick={() => onPageChange(page + 1)}
            >
              Next
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

function pricingTypeLabel(type: PricingType | undefined) {
  switch (type) {
    case 'unit_rate':
      return 'Unit rate'
    case 'area_rate':
      return 'Area rate'
    case 'percentage':
      return 'Percentage'
    case 'formula':
      return 'Formula'
    default:
      return 'Fixed'
  }
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

function calculatorPreviewBase(calculator: PricingCalculator): number {
  if (calculator.sampleTotal > 0) return calculator.sampleTotal

  const fixedCharge = calculator.charges.find(
    (charge) => charge.kind === 'fixed' && typeof charge.value === 'number' && charge.value > 0,
  )
  if (fixedCharge && typeof fixedCharge.value === 'number') return fixedCharge.value

  return 0
}

export function CalculatorLibraryScreen({
  calculators,
  onCreate,
  createDisabled = false,
  createLocked = false,
  hasServices = true,
}: {
  calculators: PricingCalculator[]
  onCreate?: (() => void) | undefined
  createDisabled?: boolean
  /** True only when create is blocked by permission (not empty catalogue). */
  createLocked?: boolean
  hasServices?: boolean
}) {
  const [selectedActiveId, setActiveId] = useState(calculators[0]?.id ?? '')
  const activeId = calculators.some((calculator) => calculator.id === selectedActiveId)
    ? selectedActiveId
    : (calculators[0]?.id ?? '')

  const active = calculators.find((calculator) => calculator.id === activeId) ?? calculators[0]
  const [inputs, setInputs] = useState<Record<string, number>>({})

  const fields = active ? calculatorNumericFields(active) : []
  const previewBase = active ? calculatorPreviewBase(active) : 0
  const estimated = active
    ? Object.keys(inputs).length === 0
      ? previewBase
      : Object.values(inputs).reduce((total, value) => total + Number(value || 0), 0)
    : 0

  const formula = active
    ? (active.charges.find((charge) => charge.kind === 'formula')?.value ??
      (active.pricingType === 'fixed'
        ? 'Base amount + Deposit + Tax + Discount approval'
        : active.charges.map((charge) => charge.label).join(' + ')))
    : 'No calculator selected'

  const showCreateLock = createLocked && (createDisabled || !onCreate)

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
              disabled={createDisabled || !onCreate}
              title={
                showCreateLock
                  ? 'You do not have permission to create calculators'
                  : !hasServices
                    ? 'Create a service in the catalogue before adding a calculator'
                    : undefined
              }
              onClick={() => onCreate?.()}
            >
              <AccessLockIcon show={showCreateLock} />
              New Calculator
            </button>
          </div>

          <div className="service-admin-table-wrap">
            <table className="service-admin-table service-admin-calculator-table">
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
                {calculators.length === 0 ? (
                  <tr>
                    <td colSpan={7}>
                      <div className="py-8 text-center">
                        <div className="service-admin-card-title">No calculators configured</div>
                        <div className="service-admin-card-subtitle mt-1">
                          {!hasServices
                            ? 'Create a service in the catalogue first, then add a calculator for it.'
                            : 'Calculator configurations will appear here once a service has pricing set up.'}
                        </div>
                      </div>
                    </td>
                  </tr>
                ) : null}
                {calculators.map((calculator) => {
                  const isActive = calculator.id === active?.id

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
                      <td>{pricingTypeLabel(calculator.pricingType)}</td>
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
                            isActive ? 'service-admin-calculator-test-button--active' : ''
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
              <div className="service-admin-card-subtitle">
                {active?.name ?? 'Select or create a calculator to preview pricing'}
              </div>
            </div>
          </div>

          {!active ? (
            <div className="service-admin-notice service-admin-notice-blue">
              <b>No calculator selected yet</b>
              <br />
              Select or create a calculator to preview variables, formula rules, deposits, taxes,
              and approval thresholds in one place.
            </div>
          ) : null}

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

export function RequestFormBuilderScreen({
  services,
  selectedServiceId,
  onSelectedServiceChange,
  form,
  fieldTypes,
  saving = false,
  onSave,
}: {
  services: ServiceCatalogueItem[]
  selectedServiceId: string
  onSelectedServiceChange: (serviceId: string) => void
  form: ServiceRequestForm | null
  fieldTypes: RequestFieldTypeOption[]
  saving?: boolean
  onSave?: (input: SaveRequestFormInput) => void
}) {
  const canEdit = Boolean(onSave)
  const selectedService =
    services.find((service) => service.id === selectedServiceId) ?? services[0] ?? null
  const formSourceKey = `${selectedService?.id ?? ''}:${form?.id ?? 'new'}:${form?.updatedAt ?? ''}`

  const [draftKey, setDraftKey] = useState(formSourceKey)
  const [formStatus, setFormStatus] = useState<ServiceRequestForm['status']>(
    form?.status ?? 'draft',
  )
  const [fields, setFields] = useState<RequestFormField[]>(form?.fields ?? [])
  const [editingIndex, setEditingIndex] = useState<number | null>(null)

  if (formSourceKey !== draftKey) {
    setDraftKey(formSourceKey)
    setFormStatus(form?.status ?? 'draft')
    setFields(form?.fields ?? [])
    setEditingIndex(null)
  }

  const editingField = editingIndex === null ? undefined : fields[editingIndex]
  const paletteDisabled = !canEdit || !selectedService
  const saveDisabled = !canEdit || !selectedService || saving
  const saveLocked = !canEdit

  const saveForm = () => {
    if (!selectedService || !onSave) return

    onSave({
      ...(form?.id ? { id: form.id } : {}),
      name: form?.name ?? `${selectedService.name} Request Form`,
      serviceId: selectedService.id,
      status: formStatus,
      fields,
    })
  }

  return (
    <div className="service-admin-page service-admin-content">
      <div className="service-admin-request-builder">
        <aside className="service-admin-request-palette">
          <h2>Field Palette</h2>
          <div className="service-admin-request-palette-list">
            {fieldTypes.map((item) => (
              <button
                key={item.value}
                type="button"
                disabled={paletteDisabled}
                onClick={() =>
                  setFields((current) => [
                    ...current,
                    {
                      id: `field-${Date.now()}`,
                      label: item.label,
                      key: item.label.toLowerCase().replace(/[^a-z0-9]+/g, '_'),
                      type: item.value,
                      required: false,
                    },
                  ])
                }
              >
                <span>+</span>
                {item.label}
              </button>
            ))}
            {fieldTypes.length === 0 ? (
              <div className="service-admin-card-subtitle py-3">
                Field types will load once the form builder is available.
              </div>
            ) : null}
          </div>
          <label className="service-admin-field">
            <span>Form status</span>
            <select
              value={formStatus}
              disabled={!canEdit || !selectedService}
              onChange={(event) =>
                setFormStatus(event.target.value as ServiceRequestForm['status'])
              }
            >
              <option value="draft">Draft</option>
              <option value="active">Active</option>
              <option value="inactive">Inactive</option>
            </select>
          </label>
          <button
            type="button"
            className="service-admin-request-save"
            disabled={saveDisabled}
            title={
              saveLocked
                ? 'You do not have permission to save this form'
                : !selectedService
                  ? 'Select a service before saving'
                  : undefined
            }
            onClick={saveForm}
          >
            <AccessLockIcon show={saveLocked && saveDisabled} />
            {saving ? 'Saving…' : 'Save Form'}
          </button>
        </aside>

        <section className="service-admin-request-canvas">
          <div className="service-admin-request-canvas-header">
            <div>
              <h2>Service Request Form Builder</h2>
              <p>Create the exact information required per service</p>
            </div>
            <label className="service-admin-request-service-picker">
              <span>Service</span>
              <select
                aria-label="Select service"
                value={selectedService?.id ?? ''}
                disabled={services.length === 0}
                onChange={(event) => onSelectedServiceChange(event.target.value)}
              >
                {services.length === 0 ? (
                  <option value="">Create a service first</option>
                ) : (
                  services.map((service) => (
                    <option key={service.id} value={service.id}>
                      {service.name}
                    </option>
                  ))
                )}
              </select>
            </label>
          </div>

          {fields.length === 0 ? (
            <div className="service-admin-empty-table-state" role="status">
              <div className="service-admin-card-title">
                {selectedService ? 'No fields on this form yet' : 'No service selected'}
              </div>
              <div className="service-admin-card-subtitle mt-1">
                {selectedService
                  ? 'Add fields from the palette to define what clients must provide for this service.'
                  : 'Choose a service to start designing its request form.'}
              </div>
            </div>
          ) : (
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
                        setFields((current) =>
                          current.filter((_, itemIndex) => itemIndex !== index),
                        )
                      }
                    >
                      Delete
                    </button>
                  ) : null}
                </article>
              ))}
            </div>
          )}
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
                  {fieldTypes.length > 0 ? (
                    fieldTypes.map((type) => (
                      <option key={type.value} value={type.value}>
                        {type.label}
                      </option>
                    ))
                  ) : (
                    <>
                      <option value="text">Text</option>
                      <option value="textarea">Long text</option>
                      <option value="number">Number</option>
                      <option value="date">Date</option>
                      <option value="select">Dropdown</option>
                      <option value="file">File upload</option>
                      <option value="checkbox">Checkbox</option>
                    </>
                  )}
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
