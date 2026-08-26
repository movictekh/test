import { describe, expect, it } from 'vitest'

import { boundaryCenter, normalizeBoundary, validateBoundary } from './real-estate.boundary'

describe('four-corner boundaries', () => {
  it('accepts zero, one and two complete corners', () => {
    expect(validateBoundary({})).toBe('')
    expect(validateBoundary({ nw: { lat: 6.5, lng: 3.3 } })).toBe('')
    expect(validateBoundary({ nw: { lat: 6.5, lng: 3.3 }, se: { lat: 6.4, lng: 3.4 } })).toBe('')
  })

  it('requires both fields for a supplied corner', () => {
    expect(validateBoundary({ nw: { lat: 6.5, lng: null } })).toContain(
      'both latitude and longitude',
    )
  })

  it('calculates the center from supplied points', () => {
    expect(boundaryCenter({ nw: { lat: 6.6, lng: 3.2 }, se: { lat: 6.4, lng: 3.4 } })).toEqual({
      lat: 6.5,
      lng: 3.3,
    })
  })

  it('normalizes legacy arrays', () => {
    expect(normalizeBoundary([{ lat: 6.6, lng: 3.2 }, { lat: 6.6, lng: 3.4 }])).toEqual({
      nw: { lat: 6.6, lng: 3.2 },
      ne: { lat: 6.6, lng: 3.4 },
    })
  })
})
