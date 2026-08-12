import { IconBuilding, IconHome, IconMap2, IconX } from '@tabler/icons-react'
import { useState } from 'react'

import {
  propertyStatuses,
  propertyTypes,
  type CreatePropertyInput,
  type Property,
  type PropertyType,
} from '../real-estate/real-estate.types'
import { validateProperty } from '../real-estate/real-estate.validation'

const residentialTypeOptions = [
  { value: 'house', label: 'House' },
  { value: 'villa', label: 'Villa' },
  { value: 'apartment', label: 'Apartment' },
  { value: 'townhouse', label: 'Townhouse' },
  { value: 'duplex', label: 'Duplex' },
  { value: 'bungalow', label: 'Bungalow' },
  { value: 'penthouse', label: 'Penthouse' },
] as const

const commercialTypeOptions = [
  { value: 'office', label: 'Office' },
  { value: 'retail', label: 'Retail Space' },
  { value: 'warehouse', label: 'Warehouse' },
  { value: 'shopping_mall', label: 'Shopping Mall' },
  { value: 'hotel', label: 'Hotel' },
  { value: 'mixed_use', label: 'Mixed Use' },
] as const

function parsePositiveInteger(value: string, fallback: number | null = null) {
  if (value.trim() === '') return fallback

  const parsed = Number(value)
  if (!Number.isFinite(parsed)) return fallback
  return Math.max(0, Math.trunc(parsed))
}

function parseNonNegativeNumber(value: string, fallback: number | null = null) {
  if (value.trim() === '') return fallback

  const parsed = Number(value)
  return Number.isFinite(parsed) && parsed >= 0 ? parsed : fallback
}

function numberInputValue(value: number | null | undefined) {
  return value == null || value === 0 ? '' : String(value)
}

function mapPropertyToInput(property: Property): CreatePropertyInput {
  return {
    isOurProperty: property.isOurProperty,
    propertyType: property.propertyType,
    propertyName: property.propertyName,
    price: property.price,
    description: property.description,
    status: property.status,
    plotNumber: property.plotNumber,
    clientName: property.clientName,
    plotSize: property.plotSize,
    plotSizeUnit: property.plotSizeUnit || 'sqm',
    buildingTypeResidential: property.buildingTypeResidential,
    bedrooms: property.bedrooms,
    bathrooms: property.bathrooms,
    floorsResidential: property.floorsResidential,
    totalAreaResidential: property.totalAreaResidential,
    buildingTypeCommercial: property.buildingTypeCommercial,
    totalAreaCommercial: property.totalAreaCommercial,
    numberOfFloors: property.numberOfFloors,
    unitsOffices: property.unitsOffices,
  }
}

function propertyTypeIcon(propertyType: PropertyType) {
  if (propertyType === 'plot') return <IconMap2 size={16} />
  if (propertyType === 'residential') return <IconHome size={16} />
  return <IconBuilding size={16} />
}

export function EditPropertyLiveWorkspace({
  property,
  saving,
  onClose,
  onSubmit,
}: {
  property: Property
  saving: boolean
  onClose: () => void
  onSubmit: (input: CreatePropertyInput) => void
}) {
  const [value, setValue] = useState<CreatePropertyInput>(() => mapPropertyToInput(property))
  const [error, setError] = useState('')

  const setField = <K extends keyof CreatePropertyInput>(
    key: K,
    nextValue: CreatePropertyInput[K],
  ) => setValue((current) => ({ ...current, [key]: nextValue }))

  const propertyType = value.propertyType

  return (
    <div className="commercial-modal-backdrop" role="presentation" onMouseDown={onClose}>
      <form
        className="commercial-modal commercial-modal--xl specialized-real-estate-modal"
        role="dialog"
        aria-modal="true"
        aria-label="Edit Property"
        onMouseDown={(event) => event.stopPropagation()}
        onSubmit={(event) => {
          event.preventDefault()
          const validationError = validateProperty(value)
          setError(validationError)
          if (!validationError) onSubmit(value)
        }}
      >
        <header className="commercial-modal-header">
          <div>
            <h2>Edit Property</h2>
            <p>Update full property details, including plot size and other type-specific fields.</p>
          </div>
          <button
            type="button"
            className="commercial-modal-close"
            onClick={onClose}
            aria-label="Close"
          >
            <IconX size={16} />
          </button>
        </header>

        <div className="commercial-modal-body">
          {error ? <div className="commercial-notice commercial-notice-red">{error}</div> : null}

          <section className="commercial-form-section">
            <div className="commercial-form-section-heading">
              <div>
                <h3>Property identity</h3>
                <p>Name, type, status and base commercial information.</p>
              </div>
              <div className="specialized-inline-chip">
                {propertyTypeIcon(propertyType)}
                <span>{property.propertyName}</span>
              </div>
            </div>

            <div className="commercial-form-grid">
              <label className="commercial-field">
                <span>
                  Property name <em>*</em>
                </span>
                <input
                  autoFocus
                  value={value.propertyName}
                  onChange={(event) => setField('propertyName', event.target.value)}
                />
              </label>

              <label className="commercial-field">
                <span>Property type</span>
                <select
                  value={value.propertyType}
                  onChange={(event) =>
                    setField(
                      'propertyType',
                      event.target.value as CreatePropertyInput['propertyType'],
                    )
                  }
                >
                  {propertyTypes.map((item) => (
                    <option key={item.value} value={item.value}>
                      {item.label}
                    </option>
                  ))}
                </select>
              </label>

              <label className="commercial-field">
                <span>Status</span>
                <select
                  value={value.status}
                  onChange={(event) =>
                    setField('status', event.target.value as CreatePropertyInput['status'])
                  }
                >
                  {propertyStatuses.map((item) => (
                    <option key={item.value} value={item.value}>
                      {item.label}
                    </option>
                  ))}
                </select>
              </label>

              <label className="commercial-field">
                <span>
                  Price <em>*</em>
                </span>
                <input
                  className="commercial-number-input"
                  type="number"
                  min={1}
                  step="any"
                  inputMode="decimal"
                  value={numberInputValue(value.price)}
                  onChange={(event) =>
                    setField('price', parseNonNegativeNumber(event.target.value, 0) ?? 0)
                  }
                />
              </label>

              <label className="commercial-field">
                <span>Plot number</span>
                <input
                  className="commercial-number-input"
                  type="number"
                  min={1}
                  inputMode="numeric"
                  value={numberInputValue(value.plotNumber)}
                  onChange={(event) =>
                    setField('plotNumber', parsePositiveInteger(event.target.value))
                  }
                />
              </label>

              <label className="commercial-field">
                <span>Client / holder</span>
                <input
                  value={value.clientName ?? ''}
                  onChange={(event) => setField('clientName', event.target.value)}
                />
              </label>

              <label className="commercial-field commercial-field--full">
                <span>Description</span>
                <textarea
                  value={value.description ?? ''}
                  onChange={(event) => setField('description', event.target.value)}
                />
              </label>
            </div>
          </section>

          {propertyType === 'plot' ? (
            <section className="commercial-form-section">
              <div className="commercial-form-section-heading">
                <div>
                  <h3>Plot details</h3>
                  <p>Land size and measurement settings for the plot record.</p>
                </div>
              </div>

              <div className="commercial-form-grid">
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
                    value={numberInputValue(value.plotSize)}
                    onChange={(event) =>
                      setField('plotSize', parseNonNegativeNumber(event.target.value))
                    }
                  />
                </label>

                <label className="commercial-field">
                  <span>Plot size unit</span>
                  <input
                    value={value.plotSizeUnit ?? 'sqm'}
                    onChange={(event) => setField('plotSizeUnit', event.target.value)}
                  />
                </label>
              </div>
            </section>
          ) : null}

          {propertyType === 'residential' ? (
            <section className="commercial-form-section">
              <div className="commercial-form-section-heading">
                <div>
                  <h3>Residential details</h3>
                  <p>Home classification, room counts and floor area.</p>
                </div>
              </div>

              <div className="commercial-form-grid">
                <label className="commercial-field">
                  <span>
                    Residential type <em>*</em>
                  </span>
                  <select
                    value={value.buildingTypeResidential ?? ''}
                    onChange={(event) => setField('buildingTypeResidential', event.target.value)}
                  >
                    <option value="">Select residential type</option>
                    {residentialTypeOptions.map((item) => (
                      <option key={item.value} value={item.value}>
                        {item.label}
                      </option>
                    ))}
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
                    value={numberInputValue(value.bedrooms)}
                    onChange={(event) =>
                      setField('bedrooms', parsePositiveInteger(event.target.value))
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
                    value={numberInputValue(value.bathrooms)}
                    onChange={(event) =>
                      setField('bathrooms', parsePositiveInteger(event.target.value))
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
                    value={numberInputValue(value.floorsResidential)}
                    onChange={(event) =>
                      setField('floorsResidential', parsePositiveInteger(event.target.value))
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
                    value={numberInputValue(value.totalAreaResidential)}
                    onChange={(event) =>
                      setField('totalAreaResidential', parseNonNegativeNumber(event.target.value))
                    }
                  />
                </label>
              </div>
            </section>
          ) : null}

          {propertyType === 'commercial' ? (
            <section className="commercial-form-section">
              <div className="commercial-form-section-heading">
                <div>
                  <h3>Commercial details</h3>
                  <p>Commercial classification, total area, floors and unit count.</p>
                </div>
              </div>

              <div className="commercial-form-grid">
                <label className="commercial-field">
                  <span>
                    Commercial type <em>*</em>
                  </span>
                  <select
                    value={value.buildingTypeCommercial ?? ''}
                    onChange={(event) => setField('buildingTypeCommercial', event.target.value)}
                  >
                    <option value="">Select commercial type</option>
                    {commercialTypeOptions.map((item) => (
                      <option key={item.value} value={item.value}>
                        {item.label}
                      </option>
                    ))}
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
                    value={numberInputValue(value.totalAreaCommercial)}
                    onChange={(event) =>
                      setField('totalAreaCommercial', parseNonNegativeNumber(event.target.value))
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
                    value={numberInputValue(value.numberOfFloors)}
                    onChange={(event) =>
                      setField('numberOfFloors', parsePositiveInteger(event.target.value))
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
                    value={numberInputValue(value.unitsOffices)}
                    onChange={(event) =>
                      setField('unitsOffices', parsePositiveInteger(event.target.value))
                    }
                  />
                </label>
              </div>
            </section>
          ) : null}
        </div>

        <footer className="commercial-modal-footer">
          <button type="button" className="commercial-btn" onClick={onClose} disabled={saving}>
            Cancel
          </button>
          <button type="submit" className="commercial-btn commercial-btn-primary" disabled={saving}>
            {saving ? 'Saving...' : 'Save Property'}
          </button>
        </footer>
      </form>
    </div>
  )
}
