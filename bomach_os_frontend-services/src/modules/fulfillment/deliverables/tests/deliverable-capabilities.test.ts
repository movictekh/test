import { describe, expect, it } from 'vitest'

import {
  canDeleteDeliverable,
  canEditDeliverable,
  canReviewDeliverable,
} from '../deliverable-capabilities'

describe('deliverable capabilities', () => {
  it('only shows approve/reject during under review', () => {
    expect(canReviewDeliverable('under_review')).toBe(true)
    expect(canReviewDeliverable('approved')).toBe(false)
    expect(canReviewDeliverable('rejected')).toBe(false)
  })

  it('mirrors rejected immutability for editing', () => {
    expect(canEditDeliverable('rejected')).toBe(false)
    expect(canEditDeliverable('approved')).toBe(true)
  })

  it('mirrors backend delete restrictions', () => {
    expect(canDeleteDeliverable('draft')).toBe(true)
    expect(canDeleteDeliverable('under_review')).toBe(true)
    expect(canDeleteDeliverable('superseded')).toBe(true)
    expect(canDeleteDeliverable('approved')).toBe(false)
    expect(canDeleteDeliverable('rejected')).toBe(false)
  })
})
