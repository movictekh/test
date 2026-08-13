import { IconBuilding, IconHome, IconMap2, IconRefresh } from '@tabler/icons-react'
import { useMemo, useState } from 'react'

import { presentError } from '@/shared/errors'

import { realEstateApi } from '../real-estate/real-estate.api'
import { buildPropertyBatch } from '../real-estate/property-batch'
import {
  propertyStatuses,
  type CreatePropertyInput,
  type PropertyBatchItem,
  type PropertyType,
} from '../real-estate/real-estate.types'
import { validateProperty } from '../real-estate/real-estate.validation'

const propertyTypeOptions = [
  {
    value: 'plot' as const,
    label: 'Plot of Land',
    description: 'Land plots with number, size, price and inventory status.',
    Icon: IconMap2,
  },
  {
    value: 'residential' as const,
    label: 'Residential Building',
    description: 'Houses, villas, apartments, duplexes, bungalows and related units.',
    Icon: IconHome,
  },
  {
    value: 'commercial' as const,
    label: 'Commercial Building',
    description: 'Offices, retail spaces, warehouses, hotels, malls and mixed-use assets.',
    Icon: IconBuilding,
  },
]

function parsePositiveInteger(value: string, fallback = 0) {
  if (value.trim() === '') return fallback

  const parsed = Number(value)
  if (!Number.isFinite(parsed)) return fallback
  return Math.max(0, Math.trunc(parsed))
}

function parseNonNegativeNumber(value: string, fallback = 0) {
  if (value.trim() === '') return fallback

  const parsed = Number(value)
  return Number.isFinite(parsed) && parsed >= 0 ? parsed : fallback
}

function numberInputValue(value: number | null | undefined) {
  return !value ? '' : String(value)
}

export function BatchCreatePropertiesWorkspace({
  estateId,
  estateName,
  onClose,
  onChanged,
}: {
  estateId: number
  estateName: string
  onClose: () => void
  onChanged: () => Promise<void> | void
}) {
  const [propertyType, setPropertyType] = useState<PropertyType>('plot')
  const [count, setCount] = useState(10)
  const [start, setStart] = useState(1)
  const [namePrefix, setNamePrefix] = useState('Plot')
  const [price, setPrice] = useState(5_000_000)
  const [status, setStatus] = useState<CreatePropertyInput['status']>('available')
  const [description, setDescription] = useState('')
  const [plotSize, setPlotSize] = useState(500)
  const [residentialType, setResidentialType] = useState('duplex')
  const [bedrooms, setBedrooms] = useState(4)
  const [bathrooms, setBathrooms] = useState(4)
  const [residentialFloors, setResidentialFloors] = useState(2)
  const [residentialArea, setResidentialArea] = useState(300)
  const [commercialType, setCommercialType] = useState('office')
  const [commercialArea, setCommercialArea] = useState(500)
  const [commercialFloors, setCommercialFloors] = useState(1)
  const [commercialUnits, setCommercialUnits] = useState(1)
  const [items, setItems] = useState<PropertyBatchItem[]>([])
  const [running, setRunning] = useState(false)
  const [error, setError] = useState('')

  const summary = useMemo(
    () => ({
      created: items.filter((item) => item.status === 'created').length,
      failed: items.filter((item) => item.status === 'failed').length,
      pending: items.filter((item) => item.status === 'queued' || item.status === 'creating')
        .length,
    }),
    [items],
  )

  const completed = summary.created + summary.failed
  const progress = items.length ? Math.round((completed / items.length) * 100) : 0

  const template = (): CreatePropertyInput => ({
    isOurProperty: true,
    propertyType,
    propertyName: namePrefix || 'Property',
    price,
    description,
    status,
    ...(propertyType === 'plot' ? { plotSize, plotSizeUnit: 'sqm' } : {}),
    ...(propertyType === 'residential'
      ? {
          buildingTypeResidential: residentialType,
          bedrooms,
          bathrooms,
          floorsResidential: residentialFloors,
          totalAreaResidential: residentialArea,
        }
      : {}),
    ...(propertyType === 'commercial'
      ? {
          buildingTypeCommercial: commercialType,
          totalAreaCommercial: commercialArea,
          numberOfFloors: commercialFloors,
          unitsOffices: commercialUnits,
        }
      : {}),
  })

  const createOne = async (item: PropertyBatchItem) => {
    setItems((rows) =>
      rows.map((row) => (row.key === item.key ? { ...row, status: 'creating', error: '' } : row)),
    )
    try {
      const created = await realEstateApi.createProperty(estateId, item.input)
      setItems((rows) =>
        rows.map((row) =>
          row.key === item.key
            ? { ...row, status: 'created', propertyId: created.id, error: '' }
            : row,
        ),
      )
    } catch (createError) {
      const message = presentError(createError, 'form-submit').message
      setItems((rows) =>
        rows.map((row) =>
          row.key === item.key ? { ...row, status: 'failed', error: message } : row,
        ),
      )
    }
  }

  const runBatch = async () => {
    const base = template()
    const validationError = validateProperty(base)
    if (validationError) return setError(validationError)
    if (!Number.isInteger(count) || count < 1 || count > 250)
      return setError('Batch size must be between 1 and 250 Properties.')
    if (!Number.isInteger(start) || start < 1)
      return setError('Starting number must be a positive whole number.')

    const rows = buildPropertyBatch(base, count, start, namePrefix)
    setItems(rows)
    setError('')
    setRunning(true)
    for (const item of rows) await createOne(item)
    setRunning(false)
    await onChanged()
  }

  const retryOne = async (item: PropertyBatchItem) => {
    setRunning(true)
    await createOne(item)
    setRunning(false)
    await onChanged()
  }

  const retryFailed = async () => {
    const failed = items.filter((item) => item.status === 'failed')
    if (!failed.length) return
    setRunning(true)
    for (const item of failed) await createOne(item)
    setRunning(false)
    await onChanged()
  }

  const changeType = (next: PropertyType) => {
    setPropertyType(next)
    setNamePrefix(
      next === 'plot' ? 'Plot' : next === 'residential' ? 'Residence' : 'Commercial Unit',
    )
  }

  return (
    <div
      className="commercial-modal-backdrop"
      role="presentation"
      onMouseDown={() => {
        if (!running) onClose()
      }}
    >
      <section
        className="commercial-modal commercial-modal--xl specialized-real-estate-modal"
        role="dialog"
        aria-modal="true"
        aria-label="Add Estate Properties"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <header className="commercial-modal-header">
          <div>
            <h2>Add Estate Properties</h2>
            <p>{estateName} · Create one property or a controlled batch of up to 250.</p>
          </div>
          <button
            type="button"
            className="commercial-modal-close"
            disabled={running}
            onClick={onClose}
            aria-label="Close"
          >
            ×
          </button>
        </header>

        <div className="commercial-modal-body">
          {error ? <div className="commercial-notice commercial-notice-red">{error}</div> : null}

          {!items.length ? (
            <>
              <section className="commercial-form-section">
                <div className="commercial-form-section-heading">
                  <div>
                    <h3>Property type</h3>
                    <p>Choose the asset class you want to create for this estate.</p>
                  </div>
                </div>

                <section className="specialized-property-type-picker">
                  {propertyTypeOptions.map(({ value, label, description, Icon }) => (
                    <button
                      key={value}
                      type="button"
                      className={
                        propertyType === value
                          ? 'specialized-property-type-option is-active'
                          : 'specialized-property-type-option'
                      }
                      onClick={() => changeType(value)}
                    >
                      <span className="specialized-property-type-icon">
                        <Icon size={20} />
                      </span>
                      <span>
                        <b>{label}</b>
                        <small>{description}</small>
                      </span>
                    </button>
                  ))}
                </section>
              </section>

              <section className="commercial-form-section">
                <div className="commercial-form-section-heading">
                  <div>
                    <h3>Batch setup</h3>
                    <p>Configure the volume, naming pattern and inventory defaults.</p>
                  </div>
                </div>

                <div className="commercial-form-grid">
                  <label className="commercial-field">
                    <span>
                      How many properties? <em>*</em>
                    </span>
                    <input
                      className="commercial-number-input"
                      type="number"
                      min={1}
                      max={250}
                      inputMode="numeric"
                      value={numberInputValue(count)}
                      onChange={(event) => setCount(parsePositiveInteger(event.target.value))}
                    />
                    <small>
                      Use `1` for a single property or a larger number for batch creation.
                    </small>
                  </label>
                  <label className="commercial-field">
                    <span>
                      Starting number <em>*</em>
                    </span>
                    <input
                      className="commercial-number-input"
                      type="number"
                      min={1}
                      inputMode="numeric"
                      value={numberInputValue(start)}
                      onChange={(event) => setStart(parsePositiveInteger(event.target.value))}
                    />
                  </label>
                  <label className="commercial-field">
                    <span>
                      Name prefix <em>*</em>
                    </span>
                    <input
                      value={namePrefix}
                      onChange={(event) => setNamePrefix(event.target.value)}
                    />
                    <small>
                      Example: {namePrefix || 'Property'} {String(start).padStart(2, '0')}
                    </small>
                  </label>
                  <label className="commercial-field">
                    <span>
                      Price per property <em>*</em>
                    </span>
                    <input
                      className="commercial-number-input"
                      type="number"
                      min={1}
                      step="any"
                      inputMode="decimal"
                      value={numberInputValue(price)}
                      onChange={(event) => setPrice(parseNonNegativeNumber(event.target.value))}
                    />
                  </label>
                  <label className="commercial-field">
                    <span>Initial status</span>
                    <select
                      value={status}
                      onChange={(event) =>
                        setStatus(event.target.value as CreatePropertyInput['status'])
                      }
                    >
                      {propertyStatuses.map((item) => (
                        <option key={item.value} value={item.value}>
                          {item.label}
                        </option>
                      ))}
                    </select>
                  </label>

                  {propertyType === 'plot' ? (
                    <label className="commercial-field">
                      <span>
                        Plot size (sqm) <em>*</em>
                      </span>
                      <input
                        className="commercial-number-input"
                        type="number"
                        min={1}
                        step="any"
                        inputMode="decimal"
                        value={numberInputValue(plotSize)}
                        onChange={(event) =>
                          setPlotSize(parseNonNegativeNumber(event.target.value))
                        }
                      />
                    </label>
                  ) : null}

                  {propertyType === 'residential' ? (
                    <>
                      <label className="commercial-field">
                        <span>
                          Residential type <em>*</em>
                        </span>
                        <select
                          value={residentialType}
                          onChange={(event) => setResidentialType(event.target.value)}
                        >
                          <option value="house">House</option>
                          <option value="villa">Villa</option>
                          <option value="apartment">Apartment</option>
                          <option value="townhouse">Townhouse</option>
                          <option value="duplex">Duplex</option>
                          <option value="bungalow">Bungalow</option>
                          <option value="penthouse">Penthouse</option>
                        </select>
                      </label>
                      <label className="commercial-field">
                        <span>
                          Bedrooms <em>*</em>
                        </span>
                        <input
                          className="commercial-number-input"
                          type="number"
                          min={1}
                          inputMode="numeric"
                          value={numberInputValue(bedrooms)}
                          onChange={(event) =>
                            setBedrooms(parsePositiveInteger(event.target.value))
                          }
                        />
                      </label>
                      <label className="commercial-field">
                        <span>
                          Bathrooms <em>*</em>
                        </span>
                        <input
                          className="commercial-number-input"
                          type="number"
                          min={1}
                          inputMode="numeric"
                          value={numberInputValue(bathrooms)}
                          onChange={(event) =>
                            setBathrooms(parsePositiveInteger(event.target.value))
                          }
                        />
                      </label>
                      <label className="commercial-field">
                        <span>Floors</span>
                        <input
                          className="commercial-number-input"
                          type="number"
                          min={1}
                          inputMode="numeric"
                          value={numberInputValue(residentialFloors)}
                          onChange={(event) =>
                            setResidentialFloors(parsePositiveInteger(event.target.value))
                          }
                        />
                      </label>
                      <label className="commercial-field">
                        <span>
                          Total area <em>*</em>
                        </span>
                        <input
                          className="commercial-number-input"
                          type="number"
                          min={1}
                          step="any"
                          inputMode="decimal"
                          value={numberInputValue(residentialArea)}
                          onChange={(event) =>
                            setResidentialArea(parseNonNegativeNumber(event.target.value))
                          }
                        />
                      </label>
                    </>
                  ) : null}

                  {propertyType === 'commercial' ? (
                    <>
                      <label className="commercial-field">
                        <span>
                          Commercial type <em>*</em>
                        </span>
                        <select
                          value={commercialType}
                          onChange={(event) => setCommercialType(event.target.value)}
                        >
                          <option value="office">Office</option>
                          <option value="retail">Retail Space</option>
                          <option value="warehouse">Warehouse</option>
                          <option value="shopping_mall">Shopping Mall</option>
                          <option value="hotel">Hotel</option>
                          <option value="mixed_use">Mixed Use</option>
                        </select>
                      </label>
                      <label className="commercial-field">
                        <span>
                          Total area <em>*</em>
                        </span>
                        <input
                          className="commercial-number-input"
                          type="number"
                          min={1}
                          step="any"
                          inputMode="decimal"
                          value={numberInputValue(commercialArea)}
                          onChange={(event) =>
                            setCommercialArea(parseNonNegativeNumber(event.target.value))
                          }
                        />
                      </label>
                      <label className="commercial-field">
                        <span>
                          Number of floors <em>*</em>
                        </span>
                        <input
                          className="commercial-number-input"
                          type="number"
                          min={1}
                          inputMode="numeric"
                          value={numberInputValue(commercialFloors)}
                          onChange={(event) =>
                            setCommercialFloors(parsePositiveInteger(event.target.value))
                          }
                        />
                      </label>
                      <label className="commercial-field">
                        <span>Units / offices</span>
                        <input
                          className="commercial-number-input"
                          type="number"
                          min={0}
                          inputMode="numeric"
                          value={numberInputValue(commercialUnits)}
                          onChange={(event) =>
                            setCommercialUnits(parsePositiveInteger(event.target.value))
                          }
                        />
                      </label>
                    </>
                  ) : null}

                  <label className="commercial-field commercial-form-span">
                    <span>Description</span>
                    <textarea
                      value={description}
                      onChange={(event) => setDescription(event.target.value)}
                    />
                  </label>
                </div>
              </section>
            </>
          ) : (
            <section className="commercial-form-section">
              <div className="commercial-form-section-heading">
                <div>
                  <h3>Batch progress</h3>
                  <p>
                    Creation runs sequentially. Failures can be retried individually or in one pass.
                  </p>
                </div>
              </div>

              <div className="specialized-batch-banner">
                <div className="specialized-batch-banner-heading">
                  <div>
                    <b>{running ? 'Creating estate properties...' : 'Property batch complete'}</b>
                    <span>
                      {summary.created} created · {summary.failed} failed · {summary.pending}{' '}
                      pending
                    </span>
                  </div>
                  <strong>{progress}%</strong>
                </div>
                <progress value={completed} max={items.length} />
                <small>
                  Each property is created in order. A failure does not stop later items.
                </small>
              </div>

              <div className="specialized-batch-list">
                {items.map((item) => {
                  const Icon =
                    item.input.propertyType === 'plot'
                      ? IconMap2
                      : item.input.propertyType === 'residential'
                        ? IconHome
                        : IconBuilding

                  return (
                    <article
                      key={item.key}
                      className={`specialized-batch-row specialized-batch-row--${item.status}`}
                    >
                      <div className="specialized-batch-row-icon">
                        <Icon size={16} />
                      </div>
                      <div className="specialized-batch-row-main">
                        <b>{item.input.propertyName}</b>
                        <small>
                          #{item.sequence} · {item.status}
                          {item.propertyId ? ` · Property ID ${item.propertyId}` : ''}
                        </small>
                        {item.error ? <p>{item.error}</p> : null}
                      </div>
                      {item.status === 'failed' ? (
                        <button
                          type="button"
                          className="commercial-btn commercial-btn-small"
                          disabled={running}
                          onClick={() => void retryOne(item)}
                        >
                          <IconRefresh size={13} /> Retry
                        </button>
                      ) : null}
                    </article>
                  )
                })}
              </div>
            </section>
          )}
        </div>

        <footer className="commercial-modal-footer">
          <button type="button" className="commercial-btn" disabled={running} onClick={onClose}>
            {items.length ? 'Close' : 'Cancel'}
          </button>
          {!items.length ? (
            <button
              type="button"
              className="commercial-btn commercial-btn-primary"
              disabled={running}
              onClick={() => void runBatch()}
            >
              Create {count} {count === 1 ? 'Property' : 'Properties'}
            </button>
          ) : summary.failed ? (
            <button
              type="button"
              className="commercial-btn commercial-btn-primary"
              disabled={running}
              onClick={() => void retryFailed()}
            >
              <IconRefresh size={13} /> Retry All Failed ({summary.failed})
            </button>
          ) : null}
        </footer>
      </section>
    </div>
  )
}
