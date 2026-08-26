import {
  boundaryCornerLabels,
  boundaryCorners,
} from '../real-estate/real-estate.boundary'
import type { MutableRefObject } from 'react'
import type {
  Boundary,
  BoundaryCoordinate,
  BoundaryCorner,
} from '../real-estate/real-estate.types'

function shown(value: number | null | undefined) {
  return value == null ? '' : String(value)
}

function parsed(value: string) {
  if (value.trim() === '') return null
  const nextValue = Number(value)
  return Number.isFinite(nextValue) ? nextValue : null
}

export function BoundaryFields({
  value,
  onChange,
  title = 'Boundary coordinates',
  description = 'Optional. Enter any of NW, NE, SE and SW. A supplied corner needs both latitude and longitude.',
  fieldErrors = {},
  fieldRefs,
  onClearError,
}: {
  value: Boundary | undefined
  onChange: (value: Boundary) => void
  title?: string
  description?: string
  fieldErrors?: Record<string, string>
  fieldRefs?: MutableRefObject<Record<string, HTMLElement | null>>
  onClearError?: (fieldKey: string) => void
}) {
  const update = (corner: BoundaryCorner, axis: keyof BoundaryCoordinate, raw: string) => {
    const currentPoint = value?.[corner] ?? { lat: null, lng: null }
    onChange({
      ...(value ?? {}),
      [corner]: { ...currentPoint, [axis]: parsed(raw) },
    })
    onClearError?.(`boundary.${corner}.${axis}`)
    onClearError?.('boundary')
  }

  const fieldRef = (fieldKey: string) => (node: HTMLElement | null) => {
    if (fieldRefs) {
      fieldRefs.current[fieldKey] = node
    }
  }

  return (
    <div className="commercial-form-span">
      <div className="commercial-form-section-heading">
        <div>
          <h4>{title}</h4>
          <p>{description}</p>
        </div>
      </div>
      <div className="commercial-form-grid">
        {boundaryCorners.map((corner) => {
          const point = value?.[corner]
          return (
            <div className="commercial-field" key={corner}>
              <span>{boundaryCornerLabels[corner]} corner</span>
              <div className="specialized-action-row">
                <input
                  type="number"
                  step="any"
                  inputMode="decimal"
                  aria-label={`${boundaryCornerLabels[corner]} latitude`}
                  placeholder="Latitude"
                  ref={fieldRef(`boundary.${corner}.lat`)}
                  value={shown(point?.lat)}
                  onChange={(event) => update(corner, 'lat', event.target.value)}
                />
                <input
                  type="number"
                  step="any"
                  inputMode="decimal"
                  aria-label={`${boundaryCornerLabels[corner]} longitude`}
                  placeholder="Longitude"
                  ref={fieldRef(`boundary.${corner}.lng`)}
                  value={shown(point?.lng)}
                  onChange={(event) => update(corner, 'lng', event.target.value)}
                />
              </div>
              {fieldErrors[`boundary.${corner}.lat`] || fieldErrors[`boundary.${corner}.lng`] ? (
                <small className="commercial-field-error">
                  {fieldErrors[`boundary.${corner}.lat`] ??
                    fieldErrors[`boundary.${corner}.lng`]}
                </small>
              ) : null}
            </div>
          )
        })}
      </div>
      {fieldErrors.boundary ? (
        <small className="commercial-field-error">{fieldErrors.boundary}</small>
      ) : null}
    </div>
  )
}
