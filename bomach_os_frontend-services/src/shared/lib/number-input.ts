/** Render numeric inputs empty instead of showing a leading 0 while editing. */
export function formatNumberFieldValue(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value) || value === 0) {
    return ''
  }

  return String(value)
}

/** Parse numeric input text; blank input becomes 0 in form state. */
export function parseNumberFieldValue(raw: string): number {
  const trimmed = raw.trim()
  if (trimmed === '') return 0

  const parsed = Number(trimmed)
  return Number.isFinite(parsed) ? parsed : 0
}

/** For string-backed dynamic numeric fields (intake forms, calculators). */
export function formatNumericStringFieldValue(value: string | number | null | undefined): string {
  if (value === null || value === undefined) return ''

  const text = String(value).trim()
  if (text === '' || text === '0') return ''

  return text
}

export function parseNumericStringFieldValue(raw: string): string {
  return raw.trim()
}
