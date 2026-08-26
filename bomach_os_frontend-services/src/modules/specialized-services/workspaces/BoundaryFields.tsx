import {
  boundaryCornerLabels,
  boundaryCorners,
} from '../real-estate/real-estate.boundary'
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
}: {
  value: Boundary | undefined
  onChange: (value: Boundary) => void
  title?: string
  description?: string
}) {
  const update = (corner: BoundaryCorner, axis: keyof BoundaryCoordinate, raw: string) => {
    const currentPoint = value?.[corner] ?? { lat: null, lng: null }
    onChange({
      ...(value ?? {}),
      [corner]: { ...currentPoint, [axis]: parsed(raw) },
    })
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
                  value={shown(point?.lat)}
                  onChange={(event) => update(corner, 'lat', event.target.value)}
                />
                <input
                  type="number"
                  step="any"
                  inputMode="decimal"
                  aria-label={`${boundaryCornerLabels[corner]} longitude`}
                  placeholder="Longitude"
                  value={shown(point?.lng)}
                  onChange={(event) => update(corner, 'lng', event.target.value)}
                />
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
