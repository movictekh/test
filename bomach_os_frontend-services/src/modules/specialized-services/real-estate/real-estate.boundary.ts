import type { Boundary, BoundaryCoordinate, BoundaryCorner } from './real-estate.types'

export const boundaryCorners: BoundaryCorner[] = ['nw', 'ne', 'se', 'sw']

export const boundaryCornerLabels: Record<BoundaryCorner, string> = {
  nw: 'NW',
  ne: 'NE',
  se: 'SE',
  sw: 'SW',
}

function record(value: unknown): Record<string, unknown> | null {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null
}

function numberOrNull(value: unknown) {
  if (value == null || value === '') return null
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : null
}

function coordinate(value: unknown): BoundaryCoordinate | null {
  const normalized = record(value)
  if (!normalized) return null

  const lat = numberOrNull(normalized.lat)
  const lng = numberOrNull(normalized.lng)
  if (lat == null && lng == null) return null
  return { lat, lng }
}

export function normalizeBoundary(value: unknown): Boundary {
  const normalized: Boundary = {}

  if (Array.isArray(value)) {
    value.slice(0, 4).forEach((point, index) => {
      const corner = boundaryCorners[index]
      const nextPoint = coordinate(point)
      if (corner && nextPoint) normalized[corner] = nextPoint
    })
    return normalized
  }

  const source = record(value)
  if (!source) return normalized

  boundaryCorners.forEach((corner) => {
    const nextPoint = coordinate(source[corner])
    if (nextPoint) normalized[corner] = nextPoint
  })

  return normalized
}

export function completeBoundaryPoints(boundary: Boundary | null | undefined) {
  return boundaryCorners.flatMap((corner) => {
    const point = boundary?.[corner]
    if (point?.lat == null || point.lng == null) return []
    return [{ corner, lat: point.lat, lng: point.lng }]
  })
}

export function boundaryCenter(boundary: Boundary | null | undefined) {
  const points = completeBoundaryPoints(boundary)
  if (!points.length) return null

  return {
    lat: points.reduce((sum, point) => sum + point.lat, 0) / points.length,
    lng: points.reduce((sum, point) => sum + point.lng, 0) / points.length,
  }
}

function orientation(
  a: { lat: number; lng: number },
  b: { lat: number; lng: number },
  c: { lat: number; lng: number },
) {
  return (b.lng - a.lng) * (c.lat - a.lat) - (b.lat - a.lat) * (c.lng - a.lng)
}

function segmentsCross(
  a: { lat: number; lng: number },
  b: { lat: number; lng: number },
  c: { lat: number; lng: number },
  d: { lat: number; lng: number },
) {
  const o1 = orientation(a, b, c)
  const o2 = orientation(a, b, d)
  const o3 = orientation(c, d, a)
  const o4 = orientation(c, d, b)
  return (o1 > 0) !== (o2 > 0) && (o3 > 0) !== (o4 > 0)
}

export function validateBoundary(boundary: Boundary | null | undefined) {
  for (const corner of boundaryCorners) {
    const point = boundary?.[corner]
    if (!point) continue

    const latMissing = point.lat == null
    const lngMissing = point.lng == null
    if (latMissing && lngMissing) continue
    if (latMissing || lngMissing) {
      return `${boundaryCornerLabels[corner]} requires both latitude and longitude.`
    }
    const lat = point.lat
    const lng = point.lng
    if (lat == null || lng == null) continue
    if (!Number.isFinite(lat) || lat < -90 || lat > 90) {
      return `${boundaryCornerLabels[corner]} latitude must be between -90 and 90.`
    }
    if (!Number.isFinite(lng) || lng < -180 || lng > 180) {
      return `${boundaryCornerLabels[corner]} longitude must be between -180 and 180.`
    }
  }

  const points = completeBoundaryPoints(boundary)
  const unique = new Set(points.map((point) => `${point.lat}:${point.lng}`))
  if (unique.size !== points.length) return 'Boundary corners must not duplicate coordinates.'

  if (points.length >= 3) {
    let area2 = 0
    for (let index = 0; index < points.length; index += 1) {
      const point = points[index]!
      const nextPoint = points[(index + 1) % points.length]!
      area2 += point.lng * nextPoint.lat - nextPoint.lng * point.lat
    }
    if (Math.abs(area2) < 1e-12) {
      return 'Three or more corners must define a non-zero area.'
    }
  }

  if (
    points.length === 4 &&
    (segmentsCross(points[0]!, points[1]!, points[2]!, points[3]!) ||
      segmentsCross(points[1]!, points[2]!, points[3]!, points[0]!))
  ) {
    return 'Four corners must follow NW → NE → SE → SW without crossing.'
  }

  return ''
}

export function compactBoundary(boundary: Boundary | null | undefined): Boundary {
  const normalized: Boundary = {}
  completeBoundaryPoints(boundary).forEach((point) => {
    normalized[point.corner] = { lat: point.lat, lng: point.lng }
  })
  return normalized
}
