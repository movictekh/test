import { getAllStates, getCities, getLocalGovernments } from '@eh1z/nigerian-locations'
import { useState } from 'react'
import { IconX } from '@tabler/icons-react'
import { useForm } from '@tanstack/react-form'

import {
  estateStatuses,
  estateTypes,
  type CreateEstateInput,
} from '../real-estate/real-estate.types'
import { validateEstate } from '../real-estate/real-estate.validation'

function parseNonNegativeNumber(value: string) {
  if (value.trim() === '') return 0

  const parsed = Number(value)
  return Number.isFinite(parsed) && parsed >= 0 ? parsed : 0
}

function numberInputValue(value: number | null | undefined) {
  return !value ? '' : String(value)
}

export function CreateEstateLiveWorkspace({
  saving,
  onClose,
  onSubmit,
}: {
  saving: boolean
  onClose: () => void
  onSubmit: (i: CreateEstateInput) => void
}) {
  const [error, setError] = useState('')
  const [selectedLga, setSelectedLga] = useState('')
  const [fallbackCityTown, setFallbackCityTown] = useState('')
  const stateOptions = getAllStates()
  const form = useForm({
    defaultValues: {
      isOurEstate: true,
      estateName: '',
      estateCode: '',
      estateType: 'residential' as const,
      developerCompanyName: 'Bomach',
      estateDescription: '',
      country: 'Nigeria',
      countryCode: 'NGA',
      state: '',
      cityTown: '',
      preciseAddress: '',
      hasCOfO: false,
      hasDeedOfAssignment: false,
      hasSurveyPlan: false,
      zoningInformation: '',
      hasPlanningPermit: false,
      hasBuildingApproval: false,
      hasEnvironmentalClearance: false,
      pricePerSqm: 0,
      availablePlotSizes: '',
      minPriceOtherProperties: 0,
      maxPriceOtherProperties: 0,
      estateStatus: 'available' as const,
      totalArea: 0,
      areaUnit: 'sqm',
      hasRoads: false,
      hasElectricity: false,
      hasWater: false,
      hasFencing: false,
      hasSecurity: false,
      hasDrainage: false,
      hasRecreation: false,
      legalFee: 0,
      developmentFee: 0,
      receiptFee: 0,
      tags: '',
    },
    onSubmit: ({ value }) => {
      const cityTownValue = value.cityTown.trim() || fallbackCityTown.trim()
      const input: CreateEstateInput = {
        ...value,
        country: 'Nigeria',
        countryCode: 'NGA',
        cityTown: cityTownValue ? `${cityTownValue}, ${selectedLga}` : selectedLga,
        minPriceOtherProperties: value.minPriceOtherProperties || null,
        maxPriceOtherProperties: value.maxPriceOtherProperties || null,
        totalArea: value.totalArea || null,
        legalFee: value.legalFee || null,
        developmentFee: value.developmentFee || null,
        receiptFee: value.receiptFee || null,
        tags: value.tags
          .split(',')
          .map((item) => item.trim())
          .filter(Boolean),
      }
      const nextError = validateEstate(input)
      setError(nextError)
      if (!selectedLga.trim()) {
        setError('Local Government Area is required.')
        return
      }
      if (!cityTownValue.trim()) {
        setError('City / town is required.')
        return
      }
      if (!nextError) onSubmit(input)
    },
  })

  return (
    <div className="commercial-modal-backdrop" role="presentation" onMouseDown={onClose}>
      <form
        className="commercial-modal commercial-modal--xl specialized-real-estate-modal"
        role="dialog"
        aria-modal="true"
        aria-label="Add Estate"
        onMouseDown={(event) => event.stopPropagation()}
        onSubmit={(event) => {
          event.preventDefault()
          void form.handleSubmit()
        }}
      >
        <header className="commercial-modal-header">
          <div>
            <h2>Add Estate</h2>
            <p>Create the estate record first, then add its property inventory in a second step.</p>
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
                <h3>Estate identity</h3>
                <p>Name, code, estate category and commercial positioning.</p>
              </div>
            </div>

            <div className="commercial-form-grid">
              <form.Field name="estateName">
                {(field) => (
                  <label className="commercial-field">
                    <span>
                      Estate name <em>*</em>
                    </span>
                    <input
                      autoFocus
                      value={field.state.value}
                      onChange={(event) => field.handleChange(event.target.value)}
                    />
                  </label>
                )}
              </form.Field>
              <form.Field name="estateCode">
                {(field) => (
                  <label className="commercial-field">
                    <span>
                      Estate code <em>*</em>
                    </span>
                    <input
                      value={field.state.value}
                      onChange={(event) => field.handleChange(event.target.value)}
                      placeholder="EST-001"
                    />
                  </label>
                )}
              </form.Field>
              <form.Field name="estateType">
                {(field) => (
                  <label className="commercial-field">
                    <span>Estate type</span>
                    <select
                      value={field.state.value}
                      onChange={(event) =>
                        field.handleChange(event.target.value as typeof field.state.value)
                      }
                    >
                      {estateTypes.map((item) => (
                        <option key={item.value} value={item.value}>
                          {item.label}
                        </option>
                      ))}
                    </select>
                  </label>
                )}
              </form.Field>
              <form.Field name="estateStatus">
                {(field) => (
                  <label className="commercial-field">
                    <span>Status</span>
                    <select
                      value={field.state.value}
                      onChange={(event) =>
                        field.handleChange(event.target.value as typeof field.state.value)
                      }
                    >
                      {estateStatuses.map((item) => (
                        <option key={item.value} value={item.value}>
                          {item.label}
                        </option>
                      ))}
                    </select>
                  </label>
                )}
              </form.Field>
              <form.Field name="developerCompanyName">
                {(field) => (
                  <label className="commercial-field">
                    <span>
                      Developer / company <em>*</em>
                    </span>
                    <input
                      value={field.state.value}
                      onChange={(event) => field.handleChange(event.target.value)}
                    />
                  </label>
                )}
              </form.Field>
              <form.Field name="pricePerSqm">
                {(field) => (
                  <label className="commercial-field">
                    <span>
                      Price per sqm <em>*</em>
                    </span>
                    <input
                      className="commercial-number-input"
                      type="number"
                      min={0}
                      step="any"
                      inputMode="decimal"
                      value={numberInputValue(field.state.value)}
                      onChange={(event) =>
                        field.handleChange(parseNonNegativeNumber(event.target.value))
                      }
                    />
                  </label>
                )}
              </form.Field>
              <form.Field name="estateDescription">
                {(field) => (
                  <label className="commercial-field commercial-form-span">
                    <span>
                      Description <em>*</em>
                    </span>
                    <textarea
                      value={field.state.value}
                      onChange={(event) => field.handleChange(event.target.value)}
                    />
                  </label>
                )}
              </form.Field>
            </div>
          </section>

          <section className="commercial-form-section">
            <div className="commercial-form-section-heading">
              <div>
                <h3>Location and inventory setup</h3>
                <p>Core location, plot sizing and estate-level pricing inputs.</p>
              </div>
            </div>

            <div className="commercial-form-grid">
              <form.Field name="state">
                {(field) => {
                  const lgaOptions = field.state.value ? getLocalGovernments(field.state.value) : []
                  const cityOptions =
                    field.state.value && selectedLga
                      ? getCities(field.state.value, selectedLga)
                      : []
                  const citySelectionDisabled = !field.state.value || !selectedLga
                  const useCityFallback = !citySelectionDisabled && cityOptions.length === 0

                  return (
                    <>
                      <label className="commercial-field">
                        <span>
                          State <em>*</em>
                        </span>
                        <select
                          value={field.state.value}
                          onChange={(event) => {
                            const nextState = event.target.value
                            field.handleChange(nextState)
                            setSelectedLga('')
                            setFallbackCityTown('')
                            form.setFieldValue('cityTown', '')
                          }}
                        >
                          <option value="">Select state</option>
                          {stateOptions.map((state) => (
                            <option key={state} value={state}>
                              {state}
                            </option>
                          ))}
                        </select>
                      </label>

                      <label className="commercial-field">
                        <span>
                          LGA <em>*</em>
                        </span>
                        <select
                          value={selectedLga}
                          disabled={!field.state.value}
                          onChange={(event) => {
                            setSelectedLga(event.target.value)
                            setFallbackCityTown('')
                            form.setFieldValue('cityTown', '')
                          }}
                        >
                          <option value="">Select LGA</option>
                          {lgaOptions.map((lga) => (
                            <option key={lga} value={lga}>
                              {lga}
                            </option>
                          ))}
                        </select>
                      </label>

                      <form.Field name="cityTown">
                        {(cityField) => (
                          <label className="commercial-field">
                            <span>
                              City / town <em>*</em>
                            </span>
                            {useCityFallback ? (
                              <input
                                value={fallbackCityTown}
                                disabled={citySelectionDisabled}
                                onChange={(event) => {
                                  const nextValue = event.target.value
                                  setFallbackCityTown(nextValue)
                                  cityField.handleChange(nextValue)
                                }}
                                placeholder="Enter city or town"
                              />
                            ) : (
                              <select
                                value={cityField.state.value}
                                disabled={citySelectionDisabled}
                                onChange={(event) => cityField.handleChange(event.target.value)}
                              >
                                <option value="">Select city / town</option>
                                {cityOptions.map((city) => (
                                  <option key={city} value={city}>
                                    {city}
                                  </option>
                                ))}
                              </select>
                            )}
                          </label>
                        )}
                      </form.Field>
                    </>
                  )
                }}
              </form.Field>
              <form.Field name="preciseAddress">
                {(field) => (
                  <label className="commercial-field">
                    <span>
                      Precise address <em>*</em>
                    </span>
                    <input
                      value={field.state.value}
                      onChange={(event) => field.handleChange(event.target.value)}
                    />
                  </label>
                )}
              </form.Field>
              <form.Field name="availablePlotSizes">
                {(field) => (
                  <label className="commercial-field">
                    <span>Available plot sizes</span>
                    <input
                      value={field.state.value}
                      onChange={(event) => field.handleChange(event.target.value)}
                      placeholder="500, 600, 1000"
                    />
                  </label>
                )}
              </form.Field>
              <form.Field name="totalArea">
                {(field) => (
                  <label className="commercial-field">
                    <span>Total area</span>
                    <input
                      className="commercial-number-input"
                      type="number"
                      min={0}
                      step="any"
                      inputMode="decimal"
                      value={numberInputValue(field.state.value)}
                      onChange={(event) =>
                        field.handleChange(parseNonNegativeNumber(event.target.value))
                      }
                    />
                  </label>
                )}
              </form.Field>
              <form.Field name="tags">
                {(field) => (
                  <label className="commercial-field commercial-form-span">
                    <span>Tags</span>
                    <input
                      value={field.state.value}
                      onChange={(event) => field.handleChange(event.target.value)}
                      placeholder="premium, gated, phase-1"
                    />
                  </label>
                )}
              </form.Field>
            </div>
          </section>

          <section className="commercial-form-section">
            <div className="commercial-form-section-heading">
              <div>
                <h3>Legal, approvals and infrastructure</h3>
                <p>Mark the documents, approvals and site utilities already available.</p>
              </div>
            </div>

            <div className="specialized-check-grid">
              {(
                [
                  ['hasCOfO', 'C of O'],
                  ['hasDeedOfAssignment', 'Deed of Assignment'],
                  ['hasSurveyPlan', 'Survey Plan'],
                  ['hasPlanningPermit', 'Planning Permit'],
                  ['hasBuildingApproval', 'Building Approval'],
                  ['hasEnvironmentalClearance', 'Environmental Clearance'],
                  ['hasRoads', 'Roads'],
                  ['hasElectricity', 'Electricity'],
                  ['hasWater', 'Water'],
                  ['hasFencing', 'Fencing'],
                  ['hasSecurity', 'Security'],
                  ['hasDrainage', 'Drainage'],
                  ['hasRecreation', 'Recreation'],
                ] as const
              ).map(([name, label]) => (
                <form.Field key={name} name={name}>
                  {(field) => (
                    <label className="commercial-check">
                      <input
                        type="checkbox"
                        checked={field.state.value}
                        onChange={(event) => field.handleChange(event.target.checked)}
                      />
                      <span>{label}</span>
                    </label>
                  )}
                </form.Field>
              ))}
            </div>
          </section>
        </div>

        <footer className="commercial-modal-footer">
          <button type="button" className="commercial-btn" onClick={onClose} disabled={saving}>
            Cancel
          </button>
          <button type="submit" className="commercial-btn commercial-btn-primary" disabled={saving}>
            {saving ? 'Creating...' : 'Create Estate'}
          </button>
        </footer>
      </form>
    </div>
  )
}
