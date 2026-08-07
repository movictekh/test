import { describe, expect, it } from 'vitest'

import { formatCurrency } from './formatters'

describe('formatCurrency', () => {
  it('keeps thousands and smaller amounts fully formatted', () => {
    expect(formatCurrency(0)).toBe('₦0')
    expect(formatCurrency(3_200)).toBe('₦3,200')
    expect(formatCurrency(500_000)).toBe('₦500,000')
    expect(formatCurrency(999_999)).toBe('₦999,999')
  })

  it('abbreviates million-scale values consistently', () => {
    expect(formatCurrency(1_000_000)).toBe('₦1M')
    expect(formatCurrency(3_200_000)).toBe('₦3.2M')
    expect(formatCurrency(11_300_000)).toBe('₦11.3M')
    expect(formatCurrency(165_000_000)).toBe('₦165M')
  })

  it('abbreviates billions with one decimal place', () => {
    expect(formatCurrency(1_000_000_000)).toBe('₦1.0B')
    expect(formatCurrency(1_500_000_000)).toBe('₦1.5B')
    expect(formatCurrency(12_340_000_000)).toBe('₦12.3B')
  })
})
