import { describe, expect, it } from 'vitest'

import {
  formatNumberFieldValue,
  formatNumericStringFieldValue,
  parseNumberFieldValue,
  parseNumericStringFieldValue,
} from './number-input'

describe('number-input helpers', () => {
  it('shows blank instead of zero', () => {
    expect(formatNumberFieldValue(0)).toBe('')
    expect(formatNumberFieldValue(125000)).toBe('125000')
  })

  it('parses blank input to zero without forcing display text', () => {
    expect(parseNumberFieldValue('')).toBe(0)
    expect(parseNumberFieldValue('10')).toBe(10)
  })

  it('formats string-backed numeric fields', () => {
    expect(formatNumericStringFieldValue('0')).toBe('')
    expect(formatNumericStringFieldValue('12')).toBe('12')
    expect(parseNumericStringFieldValue(' 15 ')).toBe('15')
  })
})
