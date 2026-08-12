import { describe, expect, it } from 'vitest'
import { validateQuickPlotUpdate } from '../real-estate.validation'

describe('quick plot update validation', () => {
  it('requires a reservation holder for reserved plots', () => {
    expect(validateQuickPlotUpdate({ status: 'reserved', price: 5_000_000, clientName: '' })).toBe(
      'A reservation holder is required when reserving a plot.',
    )
  })
  it('requires a client name for sold plots', () => {
    expect(validateQuickPlotUpdate({ status: 'sold', price: 5_000_000, clientName: '' })).toBe(
      'A client name is required when marking a plot as sold.',
    )
  })
  it('accepts a normal update', () => {
    expect(validateQuickPlotUpdate({ status: 'available', price: 5_000_000, clientName: '' })).toBe(
      '',
    )
  })
})
