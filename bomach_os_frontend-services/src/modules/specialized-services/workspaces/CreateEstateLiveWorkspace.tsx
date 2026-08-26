import { getAllStates, getCities, getLocalGovernments } from '@eh1z/nigerian-locations'
import {
  IconExternalLink,
  IconFileTypePdf,
  IconPhoto,
  IconPlayerPlay,
  IconRefresh,
  IconTrash,
  IconUpload,
  IconWorldWww,
  IconX,
} from '@tabler/icons-react'
import { useForm } from '@tanstack/react-form'
import { useMemo, useRef, useState } from 'react'

import { presentError } from '@/shared/errors'

import { realEstateApi } from '../real-estate/real-estate.api'
import {
  estateStatuses,
  estateTypes,
  type CreateEstateInput,
} from '../real-estate/real-estate.types'
import { validateEstate } from '../real-estate/real-estate.validation'
import { BoundaryFields } from './BoundaryFields'

type EstateWorkspaceValues = Omit<CreateEstateInput, 'tags'> & { tags: string }

function parseNonNegativeNumber(value: string) {
  if (value.trim() === '') return 0

  const parsed = Number(value)
  return Number.isFinite(parsed) && parsed >= 0 ? parsed : 0
}

function numberInputValue(value: number | null | undefined) {
  return !value ? '' : String(value)
}

function uploadedAssetKind(url: string): 'pdf' | 'image' | 'tour' {
  const normalized = (() => {
    try {
      return new URL(url, window.location.origin).pathname.toLowerCase()
    } catch {
      return url.toLowerCase()
    }
  })()

  if (normalized.endsWith('.pdf')) return 'pdf'
  if (/\.(png|jpg|jpeg|webp|gif|svg)$/i.test(normalized)) return 'image'
  return 'tour'
}

function defaultEstateInput(): EstateWorkspaceValues {
  return {
    isOurEstate: true,
    estateName: '',
    estateCode: '',
    estateType: 'residential',
    developerCompanyName: 'Bomach',
    estateDescription: '',
    country: 'Nigeria',
    countryCode: 'NGA',
    state: '',
    cityTown: '',
    preciseAddress: '',
    latitude: null,
    longitude: null,
    boundary: {},
    estateMapUrl: '',
    virtualTourUrl: '',
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
    estateStatus: 'available',
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
    documents: [],
  }
}

function splitStoredCityTown(value: string) {
  const parts = value
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean)

  if (parts.length <= 1) {
    return { cityTown: value.trim(), lga: '' }
  }

  return {
    cityTown: parts.slice(0, -1).join(', '),
    lga: parts.at(-1) ?? '',
  }
}

function toWorkspaceInput(initialValue?: CreateEstateInput): EstateWorkspaceValues {
  if (!initialValue) return defaultEstateInput()

  const parsedLocation = splitStoredCityTown(initialValue.cityTown)

  return {
    ...defaultEstateInput(),
    ...initialValue,
    cityTown: parsedLocation.cityTown,
    tags: Array.isArray(initialValue.tags) ? initialValue.tags.join(', ') : '',
    documents: initialValue.documents ?? [],
  }
}

function buildEstateFieldErrors(input: CreateEstateInput, options: { selectedLga: string }) {
  const errors: Record<string, string> = {}
  if (!input.estateName.trim()) errors.estateName = 'Estate name is required.'
  if (!input.estateCode.trim()) errors.estateCode = 'Estate code is required.'
  if (!input.developerCompanyName.trim())
    errors.developerCompanyName = 'Developer / company name is required.'
  if (!input.estateDescription.trim()) errors.estateDescription = 'Estate description is required.'
  if (!input.state.trim()) errors.state = 'State is required.'
  if (!options.selectedLga.trim()) errors.selectedLga = 'Local Government Area is required.'
  if (!input.cityTown.trim()) errors.cityTown = 'City / town is required.'
  if (!input.preciseAddress.trim()) errors.preciseAddress = 'Precise address is required.'
  if (
    input.latitude != null &&
    (!Number.isFinite(input.latitude) || input.latitude < -90 || input.latitude > 90)
  )
    errors.latitude = 'Latitude must be between -90 and 90.'
  if (
    input.longitude != null &&
    (!Number.isFinite(input.longitude) || input.longitude < -180 || input.longitude > 180)
  )
    errors.longitude = 'Longitude must be between -180 and 180.'
  if (!Number.isFinite(input.pricePerSqm) || input.pricePerSqm < 0)
    errors.pricePerSqm = 'Price per square metre must be zero or greater.'
  if (
    input.minPriceOtherProperties != null &&
    input.maxPriceOtherProperties != null &&
    input.minPriceOtherProperties > input.maxPriceOtherProperties
  ) {
    errors.minPriceOtherProperties = 'Minimum property price cannot exceed maximum property price.'
    errors.maxPriceOtherProperties = 'Maximum property price must be greater than or equal to the minimum.'
  }
  if (input.virtualTourUrl?.trim()) {
    try {
      new URL(input.virtualTourUrl)
    } catch {
      errors.virtualTourUrl = 'Virtual tour link must be a valid URL.'
    }
  }
  return errors
}

export function CreateEstateLiveWorkspace({
  mode = 'create',
  saving,
  initialValue,
  onClose,
  onSubmit,
}: {
  mode?: 'create' | 'edit'
  saving: boolean
  initialValue?: CreateEstateInput
  onClose: () => void
  onSubmit: (i: CreateEstateInput) => void
}) {
  const initial = useMemo(() => toWorkspaceInput(initialValue), [initialValue])
  const [error, setError] = useState('')
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})
  const [mapUploadError, setMapUploadError] = useState('')
  const [mapUploading, setMapUploading] = useState(false)
  const [tourUploadError, setTourUploadError] = useState('')
  const [tourUploading, setTourUploading] = useState(false)
  const fieldRefs = useRef<Record<string, HTMLElement | null>>({})
  const [selectedLga, setSelectedLga] = useState(
    splitStoredCityTown(initialValue?.cityTown ?? '').lga,
  )
  const [fallbackCityTown, setFallbackCityTown] = useState(
    splitStoredCityTown(initialValue?.cityTown ?? '').cityTown,
  )
  const stateOptions = getAllStates()
  const form = useForm({
    defaultValues: initial,
    onSubmit: ({ value }) => {
      const cityTownValue = value.cityTown.trim() || fallbackCityTown.trim()
      const input: CreateEstateInput = {
        ...value,
        country: 'Nigeria',
        countryCode: 'NGA',
        cityTown: cityTownValue ? `${cityTownValue}, ${selectedLga}` : selectedLga,
        latitude: value.latitude ?? null,
        longitude: value.longitude ?? null,
        boundary: value.boundary ?? {},
        estateMapUrl: value.estateMapUrl?.trim() ?? '',
        virtualTourUrl: value.virtualTourUrl?.trim() ?? '',
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
      const nextFieldErrors = buildEstateFieldErrors(input, { selectedLga })
      const nextError = validateEstate(input)
      setFieldErrors(nextFieldErrors)
      setError(nextError)
      const firstErrorKey = Object.keys(nextFieldErrors)[0]
      if (firstErrorKey) {
        const element = fieldRefs.current[firstErrorKey]
        if (element) {
          element.scrollIntoView({ behavior: 'smooth', block: 'center' })
          window.setTimeout(() => {
            if ('focus' in element && typeof element.focus === 'function') element.focus()
          }, 30)
        }
        return
      }
      onSubmit(input)
    },
  })

  const title = mode === 'edit' ? 'Edit Estate' : 'Add Estate'
  const subtitle =
    mode === 'edit'
      ? 'Update the estate record, map file and virtual-tour link without changing the rest of the inventory flow.'
      : 'Create the estate record first, then add its property inventory in a second step.'

  const uploadMap = async (file: File | null) => {
    if (!file) return
    setMapUploadError('')
    setMapUploading(true)

    try {
      const url = await realEstateApi.uploadEstateAsset(file)
      form.setFieldValue('estateMapUrl', url)
      setFieldErrors((current) => {
        const next = { ...current }
        delete next.estateMapUrl
        return next
      })
    } catch (uploadError) {
      setMapUploadError(presentError(uploadError, 'form-submit').message)
    } finally {
      setMapUploading(false)
    }
  }

  const uploadTour = async (file: File | null) => {
    if (!file) return
    setTourUploadError('')
    setTourUploading(true)

    try {
      const url = await realEstateApi.uploadEstateAsset(file)
      form.setFieldValue('virtualTourUrl', url)
      setFieldErrors((current) => {
        const next = { ...current }
        delete next.virtualTourUrl
        return next
      })
    } catch (uploadError) {
      setTourUploadError(presentError(uploadError, 'form-submit').message)
    } finally {
      setTourUploading(false)
    }
  }

  return (
    <div className="commercial-modal-backdrop" role="presentation" onMouseDown={onClose}>
      <form
        className="commercial-modal commercial-modal--xl specialized-real-estate-modal"
        role="dialog"
        aria-modal="true"
        aria-label={title}
        onMouseDown={(event) => event.stopPropagation()}
        onSubmit={(event) => {
          event.preventDefault()
          void form.handleSubmit()
        }}
      >
        <header className="commercial-modal-header">
          <div>
            <h2>{title}</h2>
            <p>{subtitle}</p>
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
                      ref={(node) => {
                        fieldRefs.current.estateName = node
                      }}
                      value={field.state.value}
                      onChange={(event) => {
                        field.handleChange(event.target.value)
                        setFieldErrors((current) => {
                          const next = { ...current }
                          delete next.estateName
                          return next
                        })
                      }}
                    />
                    {fieldErrors.estateName ? (
                      <small className="commercial-field-error">{fieldErrors.estateName}</small>
                    ) : null}
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
                      ref={(node) => {
                        fieldRefs.current.estateCode = node
                      }}
                      value={field.state.value}
                      onChange={(event) => {
                        field.handleChange(event.target.value)
                        setFieldErrors((current) => {
                          const next = { ...current }
                          delete next.estateCode
                          return next
                        })
                      }}
                      placeholder="EST-001"
                    />
                    {fieldErrors.estateCode ? (
                      <small className="commercial-field-error">{fieldErrors.estateCode}</small>
                    ) : null}
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
                      ref={(node) => {
                        fieldRefs.current.developerCompanyName = node
                      }}
                      value={field.state.value}
                      onChange={(event) => {
                        field.handleChange(event.target.value)
                        setFieldErrors((current) => {
                          const next = { ...current }
                          delete next.developerCompanyName
                          return next
                        })
                      }}
                    />
                    {fieldErrors.developerCompanyName ? (
                      <small className="commercial-field-error">
                        {fieldErrors.developerCompanyName}
                      </small>
                    ) : null}
                  </label>
                )}
              </form.Field>
              <form.Field name="pricePerSqm">
                {(field) => (
                  <label className="commercial-field">
                    <span>
                      unit_price_per_sqm <em>*</em>
                    </span>
                    <input
                      className="commercial-number-input"
                      type="number"
                      min={0}
                      step="any"
                      inputMode="decimal"
                      ref={(node) => {
                        fieldRefs.current.pricePerSqm = node
                      }}
                      value={numberInputValue(field.state.value)}
                      onChange={(event) => {
                        field.handleChange(parseNonNegativeNumber(event.target.value))
                        setFieldErrors((current) => {
                          const next = { ...current }
                          delete next.pricePerSqm
                          return next
                        })
                      }}
                    />
                    {fieldErrors.pricePerSqm ? (
                      <small className="commercial-field-error">{fieldErrors.pricePerSqm}</small>
                    ) : null}
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
                      ref={(node) => {
                        fieldRefs.current.estateDescription = node
                      }}
                      rows={5}
                      value={field.state.value}
                      onChange={(event) => {
                        field.handleChange(event.target.value)
                        setFieldErrors((current) => {
                          const next = { ...current }
                          delete next.estateDescription
                          return next
                        })
                      }}
                    />
                    {fieldErrors.estateDescription ? (
                      <small className="commercial-field-error">
                        {fieldErrors.estateDescription}
                      </small>
                    ) : null}
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
                          ref={(node) => {
                            fieldRefs.current.state = node
                          }}
                          value={field.state.value}
                          onChange={(event) => {
                            const nextState = event.target.value
                            field.handleChange(nextState)
                            setSelectedLga('')
                            setFallbackCityTown('')
                            form.setFieldValue('cityTown', '')
                            setFieldErrors((current) => {
                              const next = { ...current }
                              delete next.state
                              delete next.selectedLga
                              delete next.cityTown
                              return next
                            })
                          }}
                        >
                          <option value="">Select state</option>
                          {stateOptions.map((state) => (
                            <option key={state} value={state}>
                              {state}
                            </option>
                          ))}
                        </select>
                        {fieldErrors.state ? (
                          <small className="commercial-field-error">{fieldErrors.state}</small>
                        ) : null}
                      </label>

                      <label className="commercial-field">
                        <span>
                          LGA <em>*</em>
                        </span>
                        <select
                          ref={(node) => {
                            fieldRefs.current.selectedLga = node
                          }}
                          value={selectedLga}
                          disabled={!field.state.value}
                          onChange={(event) => {
                            setSelectedLga(event.target.value)
                            setFallbackCityTown('')
                            form.setFieldValue('cityTown', '')
                            setFieldErrors((current) => {
                              const next = { ...current }
                              delete next.selectedLga
                              delete next.cityTown
                              return next
                            })
                          }}
                        >
                          <option value="">Select LGA</option>
                          {lgaOptions.map((lga) => (
                            <option key={lga} value={lga}>
                              {lga}
                            </option>
                          ))}
                        </select>
                        {fieldErrors.selectedLga ? (
                          <small className="commercial-field-error">{fieldErrors.selectedLga}</small>
                        ) : null}
                      </label>

                      <form.Field name="cityTown">
                        {(cityField) => (
                          <label className="commercial-field">
                            <span>
                              City / town <em>*</em>
                            </span>
                            {useCityFallback ? (
                              <input
                                ref={(node) => {
                                  fieldRefs.current.cityTown = node
                                }}
                                value={fallbackCityTown}
                                disabled={citySelectionDisabled}
                                onChange={(event) => {
                                  const nextValue = event.target.value
                                  setFallbackCityTown(nextValue)
                                  cityField.handleChange(nextValue)
                                  setFieldErrors((current) => {
                                    const next = { ...current }
                                    delete next.cityTown
                                    return next
                                  })
                                }}
                                placeholder="Enter city or town"
                              />
                            ) : (
                              <select
                                ref={(node) => {
                                  fieldRefs.current.cityTown = node
                                }}
                                value={cityField.state.value}
                                disabled={citySelectionDisabled}
                                onChange={(event) => {
                                  cityField.handleChange(event.target.value)
                                  setFieldErrors((current) => {
                                    const next = { ...current }
                                    delete next.cityTown
                                    return next
                                  })
                                }}
                              >
                                <option value="">Select city / town</option>
                                {cityOptions.map((city) => (
                                  <option key={city} value={city}>
                                    {city}
                                  </option>
                                ))}
                              </select>
                            )}
                            {fieldErrors.cityTown ? (
                              <small className="commercial-field-error">{fieldErrors.cityTown}</small>
                            ) : null}
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
                      ref={(node) => {
                        fieldRefs.current.preciseAddress = node
                      }}
                      value={field.state.value}
                      onChange={(event) => {
                        field.handleChange(event.target.value)
                        setFieldErrors((current) => {
                          const next = { ...current }
                          delete next.preciseAddress
                          return next
                        })
                      }}
                    />
                    {fieldErrors.preciseAddress ? (
                      <small className="commercial-field-error">{fieldErrors.preciseAddress}</small>
                    ) : null}
                  </label>
                )}
              </form.Field>
              <form.Field name="latitude">
                {(field) => (
                  <label className="commercial-field">
                    <span>Latitude</span>
                    <input
                      className="commercial-number-input"
                      type="number"
                      step="any"
                      inputMode="decimal"
                      ref={(node) => {
                        fieldRefs.current.latitude = node
                      }}
                      value={numberInputValue(field.state.value)}
                      onChange={(event) => {
                        field.handleChange(
                          event.target.value.trim() === '' ? null : Number(event.target.value),
                        )
                        setFieldErrors((current) => {
                          const next = { ...current }
                          delete next.latitude
                          return next
                        })
                      }}
                      placeholder="Optional"
                    />
                    {fieldErrors.latitude ? (
                      <small className="commercial-field-error">{fieldErrors.latitude}</small>
                    ) : null}
                  </label>
                )}
              </form.Field>
              <form.Field name="longitude">
                {(field) => (
                  <label className="commercial-field">
                    <span>Longitude</span>
                    <input
                      className="commercial-number-input"
                      type="number"
                      step="any"
                      inputMode="decimal"
                      ref={(node) => {
                        fieldRefs.current.longitude = node
                      }}
                      value={numberInputValue(field.state.value)}
                      onChange={(event) => {
                        field.handleChange(
                          event.target.value.trim() === '' ? null : Number(event.target.value),
                        )
                        setFieldErrors((current) => {
                          const next = { ...current }
                          delete next.longitude
                          return next
                        })
                      }}
                      placeholder="Optional"
                    />
                    {fieldErrors.longitude ? (
                      <small className="commercial-field-error">{fieldErrors.longitude}</small>
                    ) : null}
                  </label>
                )}
              </form.Field>
              <form.Field name="boundary">
                {(field) => (
                  <BoundaryFields
                    value={field.state.value}
                    onChange={(boundary) => field.handleChange(boundary)}
                    title="Estate boundary"
                    description="Optional. Add any available NW, NE, SE or SW corners. The saved map view can still use latitude and longitude when provided."
                  />
                )}
              </form.Field>
              <form.Field name="availablePlotSizes">
                {(field) => (
                  <label className="commercial-field">
                    <span>Available plot sizes</span>
                    <input
                      ref={(node) => {
                        fieldRefs.current.minPriceOtherProperties = node
                      }}
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
                <h3>Estate map and virtual tour</h3>
                <p>Add the estate map as a PDF or image, plus an optional walkthrough asset.</p>
              </div>
            </div>

            <div className="commercial-form-grid">
              <form.Field name="estateMapUrl">
                {(field) => (
                  <div
                    className="commercial-field commercial-field--full commercial-upload-field"
                    ref={(node) => {
                      fieldRefs.current.estateMapUrl = node
                    }}
                  >
                    <span>Estate map</span>
                    <label className="commercial-upload-dropzone">
                      <div className="commercial-upload-dropzone-icon">
                        <IconUpload size={18} />
                      </div>
                      <div>
                        <strong>
                          {field.state.value ? 'Replace estate map' : 'Upload estate map'}
                        </strong>
                        <small>
                          Attach the estate drawing or reference image. It will be available from
                          the estate screen.
                        </small>
                      </div>
                      <input
                        type="file"
                        accept=".pdf,application/pdf,image/*,.png,.jpg,.jpeg,.webp,.gif,.svg"
                        disabled={mapUploading || saving}
                        onChange={(event) => {
                          void uploadMap(event.target.files?.[0] ?? null)
                          event.target.value = ''
                        }}
                      />
                    </label>

                    {field.state.value ? (
                      (() => {
                        const assetKind = uploadedAssetKind(field.state.value)
                        const AssetIcon = assetKind === 'image' ? IconPhoto : IconFileTypePdf
                        return (
                      <article className="commercial-upload-item commercial-upload-item--uploaded">
                        <div className="commercial-upload-item-icon">
                          <AssetIcon size={18} />
                        </div>
                        <div className="commercial-upload-item-body">
                          <div className="commercial-upload-item-top">
                            <strong>
                              {field.state.value.split('/').at(-1) || 'Estate map file'}
                            </strong>
                            <span>{assetKind === 'image' ? 'Image' : 'PDF'}</span>
                          </div>
                          <small>Ready for this estate record</small>
                        </div>
                        <div className="commercial-upload-actions">
                          <button
                            type="button"
                            className="commercial-upload-remove"
                            onClick={() =>
                              window.open(field.state.value, '_blank', 'noopener,noreferrer')
                            }
                            aria-label="Open estate map"
                          >
                            <IconExternalLink size={14} />
                          </button>
                          <button
                            type="button"
                            className="commercial-upload-remove"
                            onClick={() => {
                              field.handleChange('')
                              setMapUploadError('')
                            }}
                            aria-label="Remove estate map"
                          >
                            <IconTrash size={14} />
                          </button>
                        </div>
                      </article>
                        )
                      })()
                    ) : null}

                    {mapUploading ? (
                      <article className="commercial-upload-item commercial-upload-item--uploading">
                        <div className="commercial-upload-item-icon">
                          <IconUpload size={18} />
                        </div>
                        <div className="commercial-upload-item-body">
                          <div className="commercial-upload-item-top">
                            <strong>Uploading estate map</strong>
                            <span>Map</span>
                          </div>
                          <div className="commercial-upload-progress">
                            <div className="commercial-upload-progress-bar" />
                          </div>
                        </div>
                      </article>
                    ) : null}

                    {mapUploadError ? (
                      <article className="commercial-upload-item commercial-upload-item--error">
                        <div className="commercial-upload-item-icon">
                          <IconUpload size={18} />
                        </div>
                        <div className="commercial-upload-item-body">
                          <div className="commercial-upload-item-top">
                            <strong>Estate map upload failed</strong>
                            <span>Map</span>
                          </div>
                          <small>{mapUploadError}</small>
                        </div>
                        <div className="commercial-upload-actions">
                          <button
                            type="button"
                            className="commercial-upload-remove"
                            onClick={() => setMapUploadError('')}
                            aria-label="Dismiss upload error"
                          >
                            <IconRefresh size={14} />
                          </button>
                        </div>
                      </article>
                    ) : null}
                  </div>
                )}
              </form.Field>

              <form.Field name="virtualTourUrl">
                {(field) => (
                  <div
                    className="commercial-field commercial-field--full commercial-upload-field"
                    ref={(node) => {
                      fieldRefs.current.virtualTourUrl = node
                    }}
                  >
                    <span>Virtual tour asset</span>
                    <label className="commercial-upload-dropzone">
                      <div className="commercial-upload-dropzone-icon">
                        <IconUpload size={18} />
                      </div>
                      <div>
                        <strong>
                          {field.state.value ? 'Replace virtual tour' : 'Upload virtual tour'}
                        </strong>
                        <small>
                          Upload your in-house walkthrough file. A video or hosted viewer file can
                          be attached here and opened from the estate screen.
                        </small>
                      </div>
                      <input
                        type="file"
                        accept="video/*,.mp4,.mov,.webm,.m4v,.jpg,.jpeg,.png,.webp,.html"
                        disabled={tourUploading || saving}
                        onChange={(event) => {
                          void uploadTour(event.target.files?.[0] ?? null)
                          event.target.value = ''
                        }}
                      />
                    </label>

                    {field.state.value ? (
                      <article className="commercial-upload-item commercial-upload-item--uploaded">
                        <div className="commercial-upload-item-icon">
                          <IconPlayerPlay size={18} />
                        </div>
                        <div className="commercial-upload-item-body">
                          <div className="commercial-upload-item-top">
                            <strong>
                              {field.state.value.split('/').at(-1) || 'Virtual tour asset'}
                            </strong>
                            <span>Tour</span>
                          </div>
                          <small>Ready for this estate record</small>
                        </div>
                        <div className="commercial-upload-actions">
                          <button
                            type="button"
                            className="commercial-upload-remove"
                            onClick={() =>
                              window.open(field.state.value, '_blank', 'noopener,noreferrer')
                            }
                            aria-label="Open virtual tour"
                          >
                            <IconExternalLink size={14} />
                          </button>
                          <button
                            type="button"
                            className="commercial-upload-remove"
                            onClick={() => {
                              field.handleChange('')
                              setTourUploadError('')
                            }}
                            aria-label="Remove virtual tour"
                          >
                            <IconTrash size={14} />
                          </button>
                        </div>
                      </article>
                    ) : null}

                    {tourUploading ? (
                      <article className="commercial-upload-item commercial-upload-item--uploading">
                        <div className="commercial-upload-item-icon">
                          <IconPlayerPlay size={18} />
                        </div>
                        <div className="commercial-upload-item-body">
                          <div className="commercial-upload-item-top">
                            <strong>Uploading virtual tour</strong>
                            <span>Tour</span>
                          </div>
                          <div className="commercial-upload-progress">
                            <div className="commercial-upload-progress-bar" />
                          </div>
                        </div>
                      </article>
                    ) : null}

                    {tourUploadError ? (
                      <article className="commercial-upload-item commercial-upload-item--error">
                        <div className="commercial-upload-item-icon">
                          <IconWorldWww size={18} />
                        </div>
                        <div className="commercial-upload-item-body">
                          <div className="commercial-upload-item-top">
                            <strong>Virtual tour upload failed</strong>
                            <span>Tour</span>
                          </div>
                          <small>{tourUploadError}</small>
                        </div>
                        <div className="commercial-upload-actions">
                          <button
                            type="button"
                            className="commercial-upload-remove"
                            onClick={() => setTourUploadError('')}
                            aria-label="Dismiss tour upload error"
                          >
                            <IconRefresh size={14} />
                          </button>
                        </div>
                      </article>
                    ) : null}
                    {fieldErrors.virtualTourUrl ? (
                      <small className="commercial-field-error">{fieldErrors.virtualTourUrl}</small>
                    ) : null}
                  </div>
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
          <button
            type="submit"
            className="commercial-btn commercial-btn-primary"
            disabled={saving || mapUploading || tourUploading}
            aria-busy={saving}
          >
            {saving
              ? mode === 'edit'
                ? 'Saving...'
                : 'Creating...'
              : mode === 'edit'
                ? 'Save Estate'
                : 'Create Estate'}
          </button>
        </footer>
      </form>
    </div>
  )
}
