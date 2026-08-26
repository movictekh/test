import { IconX } from '@tabler/icons-react'
import { useState } from 'react'

import {
  brokerageStatuses,
  brokerageVerificationStatuses,
  type CreateBrokerageInput,
  type Estate,
} from '../real-estate/real-estate.types'
import { validateBrokerage } from '../real-estate/real-estate.validation'
import { BoundaryFields } from './BoundaryFields'

function parseNonNegativeNumber(value: string, fallback = 0) {
  if (value.trim() === '') return fallback

  const parsed = Number(value)
  return Number.isFinite(parsed) && parsed >= 0 ? parsed : fallback
}

function parsePercentageNumber(value: string, fallback = 0) {
  if (value.trim() === '') return fallback

  const parsed = Number(value)
  if (!Number.isFinite(parsed)) return fallback
  return Math.min(100, Math.max(0, parsed))
}

function numberInputValue(value: number | null | undefined) {
  return !value ? '' : String(value)
}

export function CreateBrokerageLiveWorkspace({
  estates,
  saving,
  onClose,
  onSubmit,
}: {
  estates: Estate[]
  saving: boolean
  onClose: () => void
  onSubmit: (i: CreateBrokerageInput) => void
}) {
  const [value, setValue] = useState<CreateBrokerageInput>({
    title: '',
    description: '',
    location: '',
    boundary: {},
    price: 0,
    propertyType: 'land',
    ownerName: '',
    ownerPhone: '',
    ownerEmail: '',
    commissionRate: 5,
    verificationStatus: 'pending',
    status: 'available',
    estateId: null,
    tags: [],
  })
  const [tags, setTags] = useState('')
  const [error, setError] = useState('')

  const setField = <K extends keyof CreateBrokerageInput>(
    key: K,
    nextValue: CreateBrokerageInput[K],
  ) => setValue((current) => ({ ...current, [key]: nextValue }))

  return (
    <div className="commercial-modal-backdrop" role="presentation" onMouseDown={onClose}>
      <form
        className="commercial-modal specialized-real-estate-modal"
        role="dialog"
        aria-modal="true"
        aria-label="Add Brokerage Property"
        onMouseDown={(event) => event.stopPropagation()}
        onSubmit={(event) => {
          event.preventDefault()
          const input = {
            ...value,
            tags: tags
              .split(',')
              .map((item) => item.trim())
              .filter(Boolean),
          }
          const validationError = validateBrokerage(input)
          setError(validationError)
          if (!validationError) onSubmit(input)
        }}
      >
        <header className="commercial-modal-header">
          <div>
            <h2>Add Brokerage Listing</h2>
            <p>Third-party property offered on commission, with verification and estate linking.</p>
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
                <h3>Listing profile</h3>
                <p>Market-facing listing information, pricing and brokerage positioning.</p>
              </div>
            </div>

            <div className="commercial-form-grid">
              <label className="commercial-field">
                <span>
                  Property title <em>*</em>
                </span>
                <input
                  autoFocus
                  value={value.title}
                  onChange={(event) => setField('title', event.target.value)}
                />
              </label>

              <label className="commercial-field">
                <span>Property type</span>
                <select
                  value={value.propertyType}
                  onChange={(event) =>
                    setField('propertyType', event.target.value as typeof value.propertyType)
                  }
                >
                  <option value="land">Land</option>
                  <option value="residential">Residential</option>
                  <option value="commercial">Commercial</option>
                </select>
              </label>

              <label className="commercial-field commercial-form-span">
                <span>
                  Location <em>*</em>
                </span>
                <input
                  value={value.location}
                  onChange={(event) => setField('location', event.target.value)}
                />
              </label>

              <BoundaryFields
                value={value.boundary}
                onChange={(boundary) => setField('boundary', boundary)}
                title="Brokerage property boundary"
                description="Optional. Add any available NW, NE, SE or SW corners for this listing."
              />

              <label className="commercial-field">
                <span>
                  Asking price <em>*</em>
                </span>
                <input
                  className="commercial-number-input"
                  type="number"
                  min={1}
                  step="any"
                  inputMode="decimal"
                  value={numberInputValue(value.price)}
                  onChange={(event) =>
                    setField('price', parseNonNegativeNumber(event.target.value))
                  }
                />
              </label>

              <label className="commercial-field">
                <span>Commission rate (%)</span>
                <input
                  className="commercial-number-input"
                  type="number"
                  min={0}
                  max={100}
                  step="any"
                  inputMode="decimal"
                  value={numberInputValue(value.commissionRate)}
                  onChange={(event) =>
                    setField('commissionRate', parsePercentageNumber(event.target.value))
                  }
                />
              </label>

              <label className="commercial-field">
                <span>Verification</span>
                <select
                  value={value.verificationStatus}
                  onChange={(event) =>
                    setField(
                      'verificationStatus',
                      event.target.value as typeof value.verificationStatus,
                    )
                  }
                >
                  {brokerageVerificationStatuses.map((item) => (
                    <option key={item.value} value={item.value}>
                      {item.label}
                    </option>
                  ))}
                </select>
              </label>

              <label className="commercial-field">
                <span>Market status</span>
                <select
                  value={value.status}
                  onChange={(event) =>
                    setField('status', event.target.value as typeof value.status)
                  }
                >
                  {brokerageStatuses.map((item) => (
                    <option key={item.value} value={item.value}>
                      {item.label}
                    </option>
                  ))}
                </select>
              </label>

              <label className="commercial-field commercial-form-span">
                <span>Description</span>
                <textarea
                  value={value.description}
                  onChange={(event) => setField('description', event.target.value)}
                />
              </label>
            </div>
          </section>

          <section className="commercial-form-section">
            <div className="commercial-form-section-heading">
              <div>
                <h3>Ownership and linkage</h3>
                <p>Mandate giver details, contact data and optional estate relationship.</p>
              </div>
            </div>

            <div className="commercial-form-grid">
              <label className="commercial-field">
                <span>
                  Owner / mandate giver <em>*</em>
                </span>
                <input
                  value={value.ownerName}
                  onChange={(event) => setField('ownerName', event.target.value)}
                />
              </label>

              <label className="commercial-field">
                <span>Owner phone</span>
                <input
                  value={value.ownerPhone}
                  onChange={(event) => setField('ownerPhone', event.target.value)}
                />
              </label>

              <label className="commercial-field">
                <span>Owner email</span>
                <input
                  type="email"
                  value={value.ownerEmail}
                  onChange={(event) => setField('ownerEmail', event.target.value)}
                />
              </label>

              <label className="commercial-field">
                <span>Related estate</span>
                <select
                  value={value.estateId ?? 0}
                  onChange={(event) => setField('estateId', Number(event.target.value) || null)}
                >
                  <option value={0}>No Estate link</option>
                  {estates.map((estate) => (
                    <option key={estate.id} value={estate.id}>
                      {estate.estateCode} · {estate.estateName}
                    </option>
                  ))}
                </select>
              </label>

              <label className="commercial-field commercial-form-span">
                <span>Tags</span>
                <input
                  value={tags}
                  onChange={(event) => setTags(event.target.value)}
                  placeholder="brokerage, exclusive, urgent"
                />
              </label>
            </div>
          </section>
        </div>

        <footer className="commercial-modal-footer">
          <button type="button" className="commercial-btn" onClick={onClose} disabled={saving}>
            Cancel
          </button>
          <button type="submit" className="commercial-btn commercial-btn-primary" disabled={saving}>
            {saving ? 'Adding...' : 'Add Listing'}
          </button>
        </footer>
      </form>
    </div>
  )
}
